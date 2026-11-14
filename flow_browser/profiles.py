"""Fresh profile metadata and account order from the original Chrome directory."""
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

CHROME_DATA = Path.home() / 'Library/Application Support/Google/Chrome'


@dataclass(frozen=True)
class ChromeProfile:
    id: str
    name: str
    account: str | None
    identity: tuple


def list_profiles(data=CHROME_DATA):
    root = Path(data)
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        metadata = os.open('Local State', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        with os.fdopen(metadata) as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
                raise RuntimeError('Chrome metadata ownership is unavailable.')
            rows = json.load(stream)['profile']['info_cache']
            after = os.fstat(stream.fileno())
            current = os.stat('Local State', dir_fd=descriptor, follow_symlinks=False)
            signature = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
            if signature(before) != signature(after) or signature(after) != signature(current):
                raise RuntimeError('Chrome metadata changed during discovery. Read the inventory again.')
        result = []
        for key, row in rows.items():
            if (key in {'Guest Profile', 'System Profile', '.', '..'} or '/' in key or '\\' in key
                    or row.get('is_ephemeral') or row.get('force_signin_profile_locked')):
                continue
            try:
                info = (root / key).lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid():
                result.append(ChromeProfile(key, row.get('name', key), row.get('user_name') or None,
                                            (info.st_dev, info.st_ino, getattr(info, 'st_birthtime', None))))
        def order(profile):
            match = re.fullmatch(r'Profile (\d+)', profile.id)
            if profile.id == 'Default':
                return (0, 0)
            if match:
                return (1, int(match[1]))
            return (2, profile.id)
        return sorted(result, key=order)
    finally:
        os.close(descriptor)


def resolve_profile(identifier, data=CHROME_DATA):
    return next((profile for profile in list_profiles(data) if profile.id == identifier), None)


def next_profile(identifier, data=CHROME_DATA):
    """Refresh Chrome's inventory and advance to the next distinct account."""
    profiles = list_profiles(data)
    current = next((item for item in profiles if item.id == identifier), None)
    if current is None:
        return profiles[0] if profiles else None
    start = profiles.index(current)
    ordered = profiles[start + 1:] + profiles[:start]
    account = (current.account or '').strip().casefold()
    return next((item for item in ordered if not account or
                 (item.account or '').strip().casefold() != account), None)

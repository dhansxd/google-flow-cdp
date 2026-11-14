"""Persistent Python console for terminal agents."""
import code
import signal

from . import FlowSession, list_profiles, next_profile


def stop(*args):
    raise SystemExit(0)


def main():
    signal.signal(signal.SIGTERM, stop)
    code.interact(banner='Flow browser console. Use list_profiles() and FlowSession(profile).',
                  local={'FlowSession': FlowSession, 'list_profiles': list_profiles,
                         'next_profile': next_profile})


if __name__ == '__main__':
    main()

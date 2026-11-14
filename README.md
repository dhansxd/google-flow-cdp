# Google Flow CDP

Control Google Flow from a terminal agent through your original Google Chrome profiles and Chrome DevTools Protocol (CDP).

The agent keeps a browser session open, reads the current DOM, accessibility tree or screenshot, and operates Flow's classic or Agent interface. Login stays in the original Chrome profile. Each session owns its own window, CDP relay and Browser Harness runtime.

## Requirements

- macOS with Google Chrome installed at `/Applications/Google Chrome.app`.
- Chrome 144 or newer with **Allow remote debugging for this browser instance** enabled at `chrome://inspect/#remote-debugging`.
- Python 3.12 and an original Chrome profile signed into Google Flow.
- macOS Accessibility permission for the Python.app host running the module. Chrome's native debugging permission is handled through Accessibility.
- Node.js for the offline JavaScript fixtures and FFmpeg for checking generated media.

## Install

```sh
git clone https://github.com/dhansxd/google-flow-cdp.git
cd google-flow-cdp
python3.12 -E -m venv runtime-browser
runtime-browser/bin/python -E -m pip install -r requirements-browser.txt
runtime-browser/bin/python -E -m pip check
runtime-browser/bin/python -E -m flow_browser
```

The `-E` option isolates Python startup from environment paths supplied by a terminal host. Dependencies live in this checkout's environment. Chrome startup and session ownership are bundled with the project.

## Start a session

The interactive console preloads `FlowSession`, `list_profiles` and `next_profile`.

```python
profiles = list_profiles()
print([(profile.id, profile.name) for profile in profiles])

f = FlowSession(profiles[0].id)
print(f.navigate('https://flow.google.com/')['text'])
print(f.observe()['controls'])
print(f.accessibility())
print(f.screenshot().stdout)
```

Choose a profile directory ID from the fresh inventory. The inventory follows profile additions, removals and renames. Chrome opens the selected original profile directly when it is stopped, running without windows or already open.

Keep this console and session through configuration, generation, rendering and download. In Hermes, use its normal `terminal` tool with `background=true, pty=true`, then send Python lines with `process_manage(action=submit)`. Other terminal agents can use their interactive-process equivalent. Python scripts can also use `with FlowSession(profile_id) as session`.

## Produce images and videos

Read the current UI before choosing controls. Use `f.run(code)` to call Browser Harness helpers in the owned window.

```python
result = f.run("fill_input('div[contenteditable=true]', 'A blue cube rotates on a white table.')")
print(result.returncode, result.stderr)
print(f.observe()['controls'])
```

The selector in this example comes from an inspected classic composer. Resolve the actual editable element in the current UI. `click_element(selector)` waits for a unique, visible, enabled target and checks its hit-test result before sending native CDP pointer input.

The calling agent can operate the following native controls through the same session.

- Classic and Agent modes, image/video selection and the available models.
- Ratio, duration, resolution and output count where the chosen model and mode expose them.
- Image uploads, Ingredients, frame references, characters and saved voices.
- Native Agent approval settings, generation progress and original downloads.
- Continuation on another signed-in profile using accepted local media and references.

Read back settings and loaded references before submitting. Keep the original project and result identity while waiting. After an uncertain response, inspect that submission's outcome before deciding another action. `observe()` reads the mounted page and preserves its document.

The [usage guide](docs/USAGE.md) covers native clicks, uploads, downloads, profile continuation and cleanup. It also explains which values come from selected controls and which remain prompt requests.

## Continue with another profile

```python
profile = next_profile(f.profile.id)
if profile is not None:
    g = FlowSession(profile.id)
    print(g.navigate('https://flow.google.com/')['text'])
```

`next_profile()` refreshes inventory, advances in natural profile order, skips another profile of the same primary account and wraps after the final profile. The calling agent reads Flow's actual credit state to decide when to move and when an earlier account can be used again.

Continue by creating or opening the destination account's project, uploading the accepted local media and binding that account's character and voice references. Project IDs and native history belong to their source accounts.

## Finish

```python
print(f.close())
print(f.cleanup)
```

A successful close returns `True`. Retry cleanup when it returns `False`. Close each additional session when its work finishes. Cleanup targets the session's owned windows and daemon. Independent agent sessions and manual Chrome windows retain their own ownership. A process crash or SIGKILL can prevent Python exit cleanup.

## Verification

```sh
runtime-browser/bin/python -E -m unittest discover
runtime-browser/bin/python -E scripts/verify_browser_sessions.py Default
```

The first command runs offline regressions. The second opens local fixture pages in the selected original Chrome profile and checks four separate agent windows, concurrent commands, input, screenshots and cleanup during an active command.

See [verification results and remaining limits](docs/VERIFICATION.md) for the tested release scope. Flow's interface and available settings can vary by account and change over time.

## Local data and security

Session data defaults to `state/browser-sessions/`. Runtime environments, local state and generated media are excluded from Git. Keep project URLs, profile/account metadata, prompts, download receipts and media in local production storage. See [SECURITY.md](SECURITY.md).

## License and attribution

MIT. The bundled Chrome lifecycle derives from [Hermes Original Chrome CDP 0.4.8](https://github.com/dhansxd/hermes-original-chrome-cdp/tree/0334304dbeabea12cd8e60dee1d4f04156435ecd). See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

# Flow browser sessions

## Install

Use macOS, Python 3.12 and Google Chrome at `/Applications/Google Chrome.app`.
Sign into Flow in the original Chrome profiles you intend to use. In Chrome 144 or
newer, enable **Allow remote debugging for this browser instance** at
`chrome://inspect/#remote-debugging`. Grant macOS Accessibility permission to the
Python.app host executing the module. Chrome's native consent is handled through
Accessibility with connection and window correlation.
The automatic consent handler recognizes English and Indonesian Chrome dialog labels.

From this checkout, create `runtime-browser` and install `requirements-browser.txt`
as shown in the README. Browser Harness 0.1.13 has its own pinned transport dependency,
so use the dedicated environment shown in the README.

The source works from a clone without an HTTP service or Hermes installation.
Local session data and screenshots default to `state/browser-sessions/` and are
excluded from Git. Keep production notes, prompts, private URLs and media there.

## Keep one session for the work

Start `runtime-browser/bin/python -E -m flow_browser` from the checkout. The console
preloads `FlowSession`, `list_profiles` and `next_profile`.

The `-E` option keeps startup imports in the chosen Python environment when a
terminal host supplies `PYTHONPATH` or `PYTHONHOME`. Use it for scripts run in this
environment too. Child Browser Harness commands receive a clean Python startup
environment from the session.

```python
profiles = list_profiles()
print([(p.id, p.name) for p in profiles])
f = FlowSession(profiles[0].id)
state = f.navigate('https://flow.google.com/')
print(state['text'])
print(f.accessibility())
result = f.screenshot()
print(result.stdout)
```

Choose the profile by its directory ID from fresh inventory. Each session verifies
the original profile before browsing. A display-name change is refreshed. Removing
or replacing the profile ends its eligibility for further commands.

`observe()` reads the mounted document, including status text and controls.
`run()` executes Browser Harness Python helpers on that session. Read the current
controls before choosing selectors and verify the resulting selected values.

```python
result = f.run("fill_input('div[contenteditable=true]', 'A blue cube rotates on a white table.')")
print(result.returncode, result.stdout, result.stderr)
print(f.observe()['controls'])
```

The selector above applies to the inspected classic composer. Inspect the actual
editable element when the UI or mode changes. `run()` returns a `CompletedProcess`.
Check its return code before proceeding. `evaluate()` raises on failed observations.

For a native pointer click, use `click_element(selector)` inside `run()`. It waits
for one visible, enabled element whose center passes the DOM hit test, then sends
one CDP pointer click. A missing, obstructed or ambiguous target returns an error.

```python
selector = 'button[aria-label="Mulai pembuatan"]'
result = f.run(f"click_element({selector!r})")
print(result.returncode, result.stderr)
```

Run a Generate action within the authorized production assignment after its
checkpoint, then read the native submission state. DOM `element.click()` can
silently ignore a disabled button. The checked helper uses native CDP input.

In Hermes, start the console with `terminal` using `background=true, pty=true`.
Retain the returned process ID. Send Python lines through `process_manage` with
`action=submit` and read output with its normal process controls. Any agent with
an interactive terminal can use the same console. A script can use `with FlowSession(...)`
and the same methods.

## Operate the native Flow UI

Use DOM or accessibility labels to switch classic/Agent and choose the offered
model, image/video mode, ratio, duration, resolution and output count. Duration
controls vary by model. The inspected Omni 1.2 Flash uses a keyboard-operable slider,
while Omni 1.1 Flash offers duration buttons. Read the displayed numeric duration
after operating the control. The current UI can offer different choices later.

For Agent, its native automatic approval option can be selected, saved and read
back from settings. Credit quotes and balances are available through the UI. When
the current account has exhausted or insufficient credits, the calling agent can
continue with the next account under its production instructions.

For uploads, open the actual picker and pass an absolute local path to the native
file input with `upload_file(selector, path)`. `Page.setInterceptFileChooserDialog`
can hold the operating-system chooser while the input is located. Disable that
interception after setting the file. Wait for upload completion, select the asset
and confirm its loaded reference in the composer. Bind character and voice entities
through their native pickers using their destination account's identities.

Before Generate, save the exact prompt, selected controls, input identities, source
hashes, current project URL and result inventory in private production state. Click
Generate once. Retain that session and observe the same document while rendering.
Identify the result using its prompt, native detail URL and original checkpoint.
After a timeout or uncertain click, inspect that existing outcome before deciding
another action. `observe()` performs a read and `navigate()` navigates only when its
requested URL differs. Repeated observations preserve the mounted document.

## Download the native result

Open the completed result, inspect the native Download menu and choose its original
size. Once that menu is open, pass the single menu action to `download()`.

```python
action = """
js("Array.from(document.querySelectorAll('[role=menuitem]')).find(e=>e.innerText.includes('Ukuran asli')).id='flow-original-download'")
click_element('#flow-original-download')
"""
receipt = f.download(action, f.directory / 'results' / 'shot.mp4')
print(receipt)
```

The menu label shown above is from the inspected Indonesian UI. Resolve the current
label first. The helper associates a download with this page's frame and completed
Chrome download GUID, then collects the changed native file and verifies its hash.
It uses the profile's normal download directory, preserving the original download.
If Chrome asks for a save location, handle the actual native dialog before collection
can complete. Chrome may also ask the Flow origin for permission to download multiple
files. Handle that native permission for the authorized download. A completion can
arrive after the collector's timeout, so inspect its original GUID and downloaded
file before another click. An ambiguous result requires inspection of that same download.
Verify the resulting file's dimensions, duration, tracks and full decode with local
media tools before accepting it.

## Continue on another original profile

```python
destination = next_profile(f.profile.id)
print(destination.id if destination else None)
g = FlowSession(destination.id)
print(g.navigate('https://flow.google.com/')['text'])
```

`next_profile()` rereads Chrome metadata, advances in natural profile-directory order,
skips another profile of the same primary account and wraps after the final profile.
New and deleted profiles are reflected on the next read. Select a current eligible
profile when the inventory returns no next account.

The helper chooses an account candidate. The calling agent reads Flow's real credit
state and persists its progress.
After a full pass, read the first account again and use it when credits are available.

Preserve the accepted local media, references, prompts and settings. Create or reuse
the destination profile's project, upload the necessary files and rebind its native
entities. A previous final frame can be uploaded as the destination video's opening
frame. Native project, character and voice IDs belong to their original accounts.

## Finish and verify

Call `f.close()` and `g.close()` when their work finishes. A successful close returns
`True`. Inspect `session.cleanup` and retry cleanup if it returns `False`. Closing
interrupts an in-flight command and closes that session's owned targets. Independent
sessions and manual windows retain their ownership. Exiting the console or SIGTERM
runs Python exit cleanup. Process crashes and SIGKILL can prevent exit cleanup.

Run the offline tests with `runtime-browser/bin/python -E -m unittest discover`.
Their JavaScript fixtures use Node.js. With authorized Chrome access,
`runtime-browser/bin/python -E scripts/verify_browser_sessions.py` tests four concurrent
agent windows, an independent manual fixture, native input, screenshots and cleanup
during an active command. Pass a profile directory ID as its optional argument.

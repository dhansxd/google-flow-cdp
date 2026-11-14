# Verification

## Validated source

The standalone controller was validated on macOS with original Chrome profiles on 15 November 2026. The publication source preserves the controller that passed the terminal acceptance through Hermes.

Completed checks on that controller include the following.

- Chrome startup from stopped, windowless and open states, with direct profile selection, zero profile picker observations and one Chrome Dock icon.
- Four agents on one profile using four distinct windows, concurrent commands and cleanup with another command active.
- Dynamic profile inventory, profile removal/replacement checks, ordering and account rotation.
- Classic and native Agent video generation through Hermes, original MP4 downloads, hash checks, FFprobe inspection and full decode.
- Image generation, uploaded references, saved characters, custom voice preview and a video with character/voice bindings.
- Model, ratio, duration, resolution and output count controls on the inspected native composers.
- Video continuation on another original Chrome profile using uploaded accepted media.
- Isolated Python imports in the console and Browser Harness child process, persistent document identity while waiting and verified session cleanup.

The inspected Agent composer exposed model, ratio, count and approval controls. Its duration and resolution were prompt requests and measured output properties. The inspected classic composer exposed hard duration and resolution controls.

## Publication package

The standalone controller files match the validated source byte for byte. The package includes 19 standalone regressions and 99 reused Chrome lifecycle regressions. All 118 offline tests pass in a fresh Python 3.12 environment, and `pip check` reports consistent dependencies.

An independent clone of this repository at `89c6404` installed its dependencies in a new environment, passed `pip check` and all 118 offline tests, and completed the four-agent native window test.

Hermes then used that clone's persistent terminal console to produce and download two original videos through the current Flow UI.

| Mode | Submissions | Measured dimensions | Container duration | Audio | Full decode |
| --- | --- | --- | --- | --- | --- |
| Classic | 1 | 720 × 1280 | 4.032 seconds | AAC | Passed |
| Agent | 1 | 720 × 1280 | 4.032 seconds | AAC | Passed |

Both files passed byte and SHA-256 comparison against their original native downloads. Independent FFprobe and FFmpeg checks also passed. A sampled frame from each file showed the requested technical subject.

Forty-one observations retained the same document marker, time origin, session, owned page window and daemon across both modes. Console and child imports resolved to the clone's environment. Native observations recorded zero profile picker windows. Session cleanup returned `True`, removed its owned targets and runtime, and stopped its daemon. The console and Hermes CLI exited with status zero. The Dock contained one Google Chrome icon.

The four-agent fixture exercise verified survival of independent peer and manual-fixture pages. The subsequent generation run had zero independent peer pages available for that separate check.

A settings-selector error during setup was resolved through a fresh DOM read before the first submission. The composer settings were then read back successfully. The native Agent composer exposed model, ratio, count and automatic approval. Its requested duration and resolution were checked against the resulting file.

## Remaining field coverage

Credit exhaustion followed by real account refill has yet to be exercised end to end. Inventory rotation and continuation between signed-in profiles have passed.

Installation on a second physical Mac has yet to be exercised. Fresh clone and environment installation on the tested Mac have passed for the validated source.

Technical generation checks establish that real media can be produced and downloaded. Acting, identity consistency, dialogue, accent and edit acceptance follow the individual production brief and its review ownership.

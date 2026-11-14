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

Clean-clone installation and native generation results will be recorded after the publication-package acceptance run.

## Remaining field coverage

Credit exhaustion followed by real account refill has yet to be exercised end to end. Inventory rotation and continuation between signed-in profiles have passed.

Installation on a second physical Mac has yet to be exercised. Fresh clone and environment installation on the tested Mac have passed for the validated source.

Technical generation checks establish that real media can be produced and downloaded. Acting, identity consistency, dialogue, accent and edit acceptance follow the individual production brief and its review ownership.

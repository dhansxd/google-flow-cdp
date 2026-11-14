# Third-party notices

## Original Chrome lifecycle

The modules in `flow_browser/_chrome/` and the corresponding regressions in `tests/` derive from Hermes Original Chrome CDP 0.4.8, commit `0334304dbeabea12cd8e60dee1d4f04156435ecd`, with Flow-local imports. Copyright 2026 dhansxd. The MIT notice is preserved in `flow_browser/_chrome/LICENSE` and the project license.

Source is available at [hermes-original-chrome-cdp](https://github.com/dhansxd/hermes-original-chrome-cdp/tree/0334304dbeabea12cd8e60dee1d4f04156435ecd).

## Installed dependencies

Browser Harness 0.1.13 is installed from its Python distribution under the MIT license. psutil and websockets use the BSD-3-Clause license. Their distributions contain their own notices. `requirements-browser.txt` selects Browser Harness and psutil, while Browser Harness supplies its pinned transport dependencies.

# Local credentials and publication

Chrome keeps login in the original profile. The controller reads profile metadata and operates the signed-in browser through CDP. This grants the calling agent access to the selected profile's signed-in websites.

Local session state, screenshots, project URLs, account metadata, receipts and generated media belong in ignored production storage. The repository contains source, synthetic fixtures, tests and documentation. Runtime environments and Chrome profile contents stay on the local machine.

When reporting an issue, redact account identifiers, private URLs, tokens and production data from screenshots and logs. A full Git history scan and a tracked-tree scan can be run with Gitleaks before publication.

```sh
gitleaks git --log-opts=--all --redact=100
```

Automated scanning detects supported patterns. Review the tracked files and Git history as part of publication.

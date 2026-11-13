# Security

## Report a problem

Please report security problems privately, not in a public issue:
[open a private report](https://github.com/malewis5/big-apple-connect-box/security/advisories/new).
Only the maintainer sees it.

Say what you found and how to reproduce it. This is a personal project with
one maintainer, so there is no promised response time, but reports are read
and answered as soon as possible.

## What counts

- The measuring program in `apps/box`: anything that lets someone else run
  commands on the machine, read the database, or send the results somewhere
  they shouldn't go.
- The website at <https://www.bigappleconnect.com>.
- The release files: anything that would let a download differ from what the
  release workflow built. [Verify a download](apps/box/README.md#verify-a-download)
  explains how to check one.

## Supported versions

Only the [latest release](https://github.com/malewis5/big-apple-connect-box/releases/latest)
gets fixes.

## Email

The project does not send email. `bigappleconnect.com` publishes records
that tell mail servers to reject anything claiming to come from it.

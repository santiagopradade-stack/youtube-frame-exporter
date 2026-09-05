# Code signing policy

Free code signing is provided by [SignPath.io](https://signpath.io/);
the certificate is provided by the
[SignPath Foundation](https://signpath.org/).

## Team roles

- Committer and reviewer:
  [repository owner @santiagopradade-stack](https://github.com/santiagopradade-stack)
- Signing approver:
  [repository owner @santiagopradade-stack](https://github.com/santiagopradade-stack)

Changes proposed by anyone other than the repository owner must be reviewed
before they are merged. Every release signing request requires manual approval
by the signing approver.

## Privacy

This program will not transfer any information to other networked systems
unless specifically requested by the user or the person installing or
operating it. See the full [privacy policy](PRIVACY.md).

## Build origin

Windows releases are built from this public repository on GitHub-hosted
runners. Once the project is accepted by the SignPath Foundation, the workflow
will submit the resulting artifact for origin-verified signing.

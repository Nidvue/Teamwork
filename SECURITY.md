# Security Policy

Owner: Technical Writer.

Related: [Contributing](CONTRIBUTING.md) · [Code of conduct](CODE_OF_CONDUCT.md)

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |
| < 1.0 | No |

Security fixes are released for the latest minor line.

## Reporting a vulnerability

Use [GitHub Security Advisories](https://github.com/Nidvue/Teamwork/security/advisories/new)
to report a vulnerability privately. This is the **only** supported channel: no
personal email address is published, and reports sent by other means cannot be
guaranteed to reach the maintainers.

Please include:

- the affected version and platform;
- a description of the issue and its impact;
- reproduction steps or a proof of concept;
- any suggested fix or mitigation.

Do not open a public issue, and do not disclose the issue publicly before a fix
is released.

## Our process

1. We acknowledge the report through the advisory thread as soon as possible.
2. We confirm the issue and assess severity.
3. We prepare and test a fix on a private branch.
4. We release the fix and publish the advisory, crediting the reporter unless
   they ask to remain anonymous.

## Scope

In scope: the `teamwork` package, the `teamwork` CLI, the bundled skill bundle,
and the documented workspace format.

Out of scope: vulnerabilities in third-party tools or services you run alongside
Teamwork; social engineering; and reports that require access to a private
machine.

## Privacy allowlist

`scripts/privacy_scan.py` runs with `--allow .github/privacy-allow.txt` in
`make privacy` and in CI. The file holds one regular expression per line plus a
reason; it exists so a false positive cannot force a history rewrite. It carries
exactly one entry today (`^\.pi/agent/npm$`, a package path quoted by T-0001; the tree still carries the scanner's own
fixture for it, and three history blobs match, so the gate needs the entry). A second entry needs a recorded decision and, if it
masks a credential rule, the Security Auditor's review - growing the list is
weakening the gate.

## Safe harbour

Good-faith security research is welcome. We will not pursue action against
researchers who follow this policy, avoid privacy violations and data
destruction, and do not exploit an issue beyond what is needed to demonstrate it.

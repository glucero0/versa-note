# Security Policy

## Supported Versions

Security updates are applied to the latest release on the default branch (`main`).

| Version | Supported |
| ------- | --------- |
| `main` (latest) | Yes |
| Older commits / forks | No |

## Reporting a Vulnerability

If you discover a security issue in Versa Note, please report it privately so it can be fixed before public disclosure.

**Preferred:** use [GitHub Security Advisories](https://github.com/glucero0/versa-note/security/advisories/new) for this repository.

Please include:

- A description of the issue and its impact
- Steps to reproduce (or a proof of concept if available)
- Affected version / commit if known

You should receive an acknowledgment within a few days. After the issue is confirmed and a fix is ready, we may publish a security advisory and credit reporters who wish to be named.

Please do **not** open a public issue for security vulnerabilities.

## Scope

Versa Note is a local desktop note-taking app (Python / tkinter). Typical concerns include:

- Path handling when opening or saving files
- Session restore (`.versa-note-session.json`)
- Clipboard handling
- Parsing of user-controlled note content (e.g. CSV, JSON, Markdown)

Reports outside this scope (e.g. issues in third-party tools used only for development) may be declined.

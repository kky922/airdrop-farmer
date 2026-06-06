# Security Policy

## Reporting a vulnerability

Do not open a public issue for credentials, private data, or an exploitable
security problem.

Use GitHub's private vulnerability reporting feature for this repository. If
that feature is unavailable, contact the repository owner through the GitHub
profile and provide:

- the affected file or component
- steps to reproduce
- the expected impact
- a suggested remediation, if available

Never include live API keys, wallet secrets, account numbers, or personal data
in a report.

## Secrets

All credentials must be supplied through environment variables or local files
excluded by `.gitignore`. Rotate a credential immediately if it is committed,
even if the commit is later removed.

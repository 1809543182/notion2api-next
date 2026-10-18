# Security

## Never commit credentials

This project authenticates with your own Notion session. The following files
contain secrets and are ignored by `.gitignore`:

| File | Contents |
|---|---|
| `accounts.json` | `token_v2`, space/user ids, cookies |
| `.env` | the same credentials, `NOTION_ACCOUNTS`, optional API keys |
| `data/` | conversation database, pending tokens, sync output |

Before pushing to GitHub run:

```bash
git status --short          # make sure .env / accounts.json are not listed
git grep -n "token_v2"      # inspect values; code references and placeholders are normal
```

## If a token leaks

1. Revoke the affected session through Notion's account/session controls; a local logout alone must not be assumed to revoke every copied cookie.
2. Re-run `python login.py` after signing in again to capture a fresh session.
3. Remove the file from git history (`git filter-repo`) before publishing.

## Reporting

Open a GitHub issue for vulnerabilities; do not include tokens in reports.

See [authentication and credential storage](docs/AUTHENTICATION.md) for the full
data flow. Runtime logs, browser localStorage, pending login data and Heavy-mode
conversation databases are private too. The default launchers bind only to
localhost; before exposing the service, configure API_KEY, HTTPS and CORS.

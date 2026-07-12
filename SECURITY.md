# Security Policy & Credential Rotation Runbook

## Reporting a Vulnerability
If you discover a security vulnerability or exposed credential, please do not open a public issue. Instead, report it privately.

## Credential Rotation Runbook

To prevent secret exposure, never commit keys, cookies, or secrets to source control. Always follow these rules:

### 1. Storage of Secrets
- Store all active configuration values and keys in a local, untracked `.env` file in the project root.
- Add `.env`, `config.toml`, and all session or cookie JSON files (`*_cookies.json`, `*storage_state.json`) to `.gitignore`.

### 2. Standard Secret Rotation Checklist
If credentials are leaked or compromised:
1. **Revoke the exposed key/token immediately** in the provider's developer dashboard (GitHub, Google, Meta, Pexels).
2. **Move the compromised files** out of the repository working tree to a secure local folder.
3. **Rewrite Git History** to purge all occurrences of the exposed files:
   ```bash
   git-filter-repo --path <compromised_filename> --invert-paths --force
   ```
4. **Restore remote** configurations and force-push the cleaned branches:
   ```bash
   git remote add origin <safe_repo_url>
   git push origin main --force
   ```

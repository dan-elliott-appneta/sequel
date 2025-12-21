# Security Policy

## Reporting Security Issues

If you discover a security vulnerability in Sequel, please report it responsibly:

- **Preferred Method:** GitHub Security Advisories
  https://github.com/dan-elliott-appneta/sequel/security/advisories/new

- **Email:** daniel.elliot@broadcom.com (for urgent issues)

- **Response Time:** We aim to respond within 48 hours

**Please do NOT open public issues for security vulnerabilities.**

---

## Security Practices

### Credential Protection

Sequel implements automatic credential scrubbing in all logs via `CredentialScrubbingFilter`:

- **Patterns Detected:**
  - API tokens and keys
  - Bearer authorization headers
  - Private keys (PEM format)
  - Passwords and credentials
  - Base64-encoded keys

- **Coverage:**
  - JSON request/response bodies
  - Python function parameters
  - HTTP Authorization headers
  - Configuration values

- **Testing:** 38+ test cases ensure scrubbing works correctly across all scenarios

**Implementation:** `src/sequel/utils/logging.py`

### Secret Management

- **Metadata Only:** Secret Manager integration retrieves **METADATA ONLY**
- Secret values are **never accessed or displayed**
- Explicitly enforced in `src/sequel/services/secrets.py`
- List operations show secret names, versions, and creation dates only

### Authentication

- **Application Default Credentials (ADC):** Uses Google Cloud's standard authentication
- **Read-Only Scope:** `cloud-platform.read-only` - no write permissions
- **No Credential Storage:** Relies on gcloud CLI or service account files
- **Automatic Refresh:** Credentials refreshed automatically when expired

### Local Data

- **Configuration File:** `~/.config/sequel/config.json`
- **Contains:** UI preferences (theme), project filters (regex patterns)
- **Does NOT Contain:** Credentials, secrets, tokens, or sensitive data
- **Permissions:** Uses standard user file permissions

---

## Supported Versions

| Version | Security Updates |
|---------|------------------|
| 0.1.x (Alpha) | ✅ Latest release only |

**Note:** This is alpha software. Use at your own risk in production environments.

---

## Known Limitations

We believe in transparent security. The following limitations are known:

1. **Config File Permissions:** Uses default user permissions (not hardened to 600)
2. **Input Validation:** Relies on Google Cloud API validation for inputs
3. **Audit Logging:** No built-in audit logging (use GCP audit logs instead)
4. **Rate Limiting:** No client-side rate limiting (relies on GCP quota enforcement)

---

## Security Audit

- **Last Audit:** Initial release (2024)
- **Test Coverage of Security Features:** 100%
- **Automated Security Scanning:** GitHub Dependabot enabled
- **Credential Scrubbing Tests:** 38 test cases

---

## Dependencies

- All dependencies managed via `requirements.txt`
- GitHub Dependabot alerts enabled
- Regular updates applied for security patches
- Minimal dependency footprint to reduce attack surface

---

## Recommended Security Practices

When using Sequel:

1. **Use Service Accounts:** Create dedicated service accounts with minimal permissions
2. **Enable Audit Logging:** Enable Cloud Audit Logs in your GCP projects
3. **Review IAM Permissions:** Regularly audit IAM role bindings
4. **Separate Environments:** Use different projects for dev/staging/production
5. **Monitor Quota Usage:** Set up quota alerts to detect unusual activity
6. **Keep Updated:** Regularly update to the latest version for security patches

---

## Security Features by Design

- **Read-Only Operations:** All API operations are read-only (list, get, describe)
- **No Data Modification:** Cannot create, update, or delete cloud resources
- **Local Processing:** All data processing happens locally (no telemetry)
- **Open Source:** Source code is publicly auditable

---

## Contact

For security concerns or questions:
- GitHub Security Advisories: https://github.com/dan-elliott-appneta/sequel/security/advisories/new
- Email: daniel.elliot@broadcom.com

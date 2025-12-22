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

### Input Validation & ReDoS Prevention

**Regex Pattern Validation** (Added in v1.0.4):
- **All user-provided regex patterns are validated** at startup
- **ReDoS Detection:** Patterns with nested quantifiers or catastrophic backtracking are rejected
- **Syntax Validation:** Invalid regex syntax is caught gracefully
- **Graceful Degradation:** Invalid patterns log a warning and filtering is disabled
- **Implementation:** `src/sequel/utils/regex_validator.py`
- **Test Coverage:** 31 tests covering validation, ReDoS detection, and real-world scenarios

**Protected Patterns:**
- Nested quantifiers: `(a+)+`, `(a*)*`, `(a{2,5})*`
- Overlapping alternations: `(a|ab)*`
- Excessive complexity: >500 chars, >20 capturing groups

**Why This Matters:**
Regular Expression Denial of Service (ReDoS) attacks can cause catastrophic backtracking, freezing the application with maliciously-crafted input. Sequel validates all patterns before use to prevent this attack vector.

---

## Supported Versions

| Version | Security Updates |
|---------|------------------|
| 1.0.x | ✅ Latest release only |
| 0.1.x (Legacy) | ❌ No longer supported |

**Note:** Version 1.0.0+ is production-ready. Security patches are applied to the latest 1.0.x release only.

---

## Known Limitations

We believe in transparent security. The following limitations are known:

1. **Config File Permissions:** Uses default user permissions (not hardened to 600)
2. **Audit Logging:** No built-in audit logging (use GCP audit logs instead)
3. **Rate Limiting:** No client-side rate limiting (relies on GCP quota enforcement)

---

## Security Audit

- **Last Audit:** v1.0.4 release (December 2025)
- **Test Coverage of Security Features:** 100%
- **Automated Security Scanning:** GitHub Dependabot enabled
- **Credential Scrubbing Tests:** 17 test cases
- **Regex Validation Tests:** 31 test cases

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

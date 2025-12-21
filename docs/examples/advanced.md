# Advanced Usage Examples

This guide covers advanced configuration, customization, and troubleshooting for Sequel.

## Example 1: Project Filtering with Regex

### Use Case: Show Only Production Projects

**Config File:** `~/.config/sequel/config.json`

```json
{
  "filters": {
    "project_regex": "^prod-.*"
  }
}
```

**Effect:**
- Only projects starting with "prod-" are shown
- Matches against both project ID and display name
- Examples that match: `prod-web`, `prod-api`, `prod-data`
- Examples that don't match: `dev-web`, `staging-api`

**Launch Sequel:**
```bash
sequel

# Status bar will show:
# Filtered 50 projects to 5 using regex: ^prod-.*
```

### Use Case: Show Multiple Project Patterns

**Match projects starting with "prod-", "staging-", or containing "test":**

```json
{
  "filters": {
    "project_regex": "^(prod-|staging-).*|.*test.*"
  }
}
```

**Matches:**
- `prod-web` ✓
- `staging-api` ✓
- `dev-test-env` ✓
- `my-test-project` ✓
- `dev-web` ✗

### Use Case: Show Projects by Team

**Match projects for NetOps and DevOps teams:**

```json
{
  "filters": {
    "project_regex": ".*(netops|devops).*"
  }
}
```

**Note:** Use `.*` for case-insensitive matching via environment variable:

```bash
# Case-insensitive filter via environment
export SEQUEL_PROJECT_FILTER_REGEX="(?i).*(netops|devops).*"
sequel
```

### Use Case: Disable Filtering (Show All)

```json
{
  "filters": {
    "project_regex": ""
  }
}
```

**Or via environment variable:**
```bash
export SEQUEL_PROJECT_FILTER_REGEX=""
sequel
```

---

## Example 2: Custom Configuration File

### Full Configuration Example

**File:** `~/.config/sequel/config.json`

```json
{
  "ui": {
    "theme": "dracula"
  },
  "filters": {
    "project_regex": "^s[dvp]ap[n|nc]gl.*$"
  }
}
```

**What This Does:**
- Sets Dracula theme
- Filters projects matching pattern: starts with `sd`, `sv`, or `sp`, followed by `apn` or `apnc`, then `gl`, then anything

### Configuration Precedence

**Priority (highest to lowest):**
1. Environment variables (e.g., `SEQUEL_THEME`)
2. Config file (`~/.config/sequel/config.json`)
3. Default values

**Example:**
```bash
# Config file says theme="dracula"
# But environment variable overrides:
export SEQUEL_THEME="monokai"
sequel

# Result: Monokai theme is used
```

---

## Example 3: Environment Variable Configuration

### All Available Environment Variables

```bash
# API Configuration
export SEQUEL_API_TIMEOUT=45                # API timeout in seconds (default: 30)
export SEQUEL_API_MAX_RETRIES=5             # Max retry attempts (default: 3)
export SEQUEL_API_RETRY_DELAY=2.0           # Initial retry delay (default: 1.0)
export SEQUEL_API_RETRY_BACKOFF=3.0         # Backoff multiplier (default: 2.0)

# Cache Configuration
export SEQUEL_CACHE_ENABLED=true            # Enable caching (default: true)
export SEQUEL_CACHE_TTL_PROJECTS=300        # Project cache TTL in seconds (default: 600)
export SEQUEL_CACHE_TTL_RESOURCES=180       # Resource cache TTL in seconds (default: 300)

# Logging
export SEQUEL_LOG_LEVEL=DEBUG               # Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
export SEQUEL_LOG_FILE=/tmp/sequel.log      # Log file path (default: None)
export SEQUEL_ENABLE_CREDENTIAL_SCRUBBING=true  # Enable credential scrubbing (default: true)

# Google Cloud
export SEQUEL_GCLOUD_PROJECT_ID=my-project  # Default project ID (default: auto-detect)
export SEQUEL_GCLOUD_QUOTA_WAIT_TIME=120    # Quota retry wait time in seconds (default: 60)

# UI
export SEQUEL_THEME=nord                    # Textual theme name (default: textual-dark)

# Filters
export SEQUEL_PROJECT_FILTER_REGEX="^prod-.*"  # Project filter regex (default: specific pattern)

# Launch Sequel
sequel
```

### Example: High-Performance Configuration

```bash
# Reduce cache TTLs for fresher data
export SEQUEL_CACHE_TTL_PROJECTS=120   # 2 minutes
export SEQUEL_CACHE_TTL_RESOURCES=60   # 1 minute

# Increase timeout for slow networks
export SEQUEL_API_TIMEOUT=60           # 60 seconds

# More aggressive retries
export SEQUEL_API_MAX_RETRIES=5        # 5 attempts
export SEQUEL_API_RETRY_DELAY=0.5      # Start with 0.5s delay

sequel
```

### Example: Debug Configuration

```bash
# Enable debug logging with file output
export SEQUEL_LOG_LEVEL=DEBUG
export SEQUEL_LOG_FILE=/tmp/sequel-debug.log

# Disable caching to see all API calls
export SEQUEL_CACHE_ENABLED=false

# Launch Sequel
sequel

# In another terminal, watch logs
tail -f /tmp/sequel-debug.log
```

---

## Example 4: Using Service Account Authentication

### Step 1: Create Service Account

```bash
# Via gcloud CLI
gcloud iam service-accounts create sequel-viewer \
    --display-name="Sequel Viewer" \
    --project=my-project

# Grant Viewer role
gcloud projects add-iam-policy-binding my-project \
    --member="serviceAccount:sequel-viewer@my-project.iam.gserviceaccount.com" \
    --role="roles/viewer"

# Create and download key
gcloud iam service-accounts keys create ~/sequel-sa-key.json \
    --iam-account=sequel-viewer@my-project.iam.gserviceaccount.com
```

### Step 2: Configure Sequel to Use Service Account

```bash
# Set environment variable pointing to key file
export GOOGLE_APPLICATION_CREDENTIALS=~/sequel-sa-key.json

# Launch Sequel
sequel

# Sequel will use service account credentials
# No browser authentication needed
```

### Step 3: Verify Authentication

```bash
# Check which credentials are being used
gcloud auth application-default print-access-token

# This should work without errors if credentials are valid
```

**Security Note:** Never commit service account keys to version control!

---

## Example 5: Debugging Authentication Issues

### Check Current Credentials

```bash
# Print access token to verify credentials work
gcloud auth application-default print-access-token

# If this fails, credentials need to be refreshed:
gcloud auth application-default login
```

### Check Credential Location

```bash
# ADC file location
ls -la ~/.config/gcloud/application_default_credentials.json

# Service account key (if using)
ls -la ~/sequel-sa-key.json

# Check GOOGLE_APPLICATION_CREDENTIALS
echo $GOOGLE_APPLICATION_CREDENTIALS
```

### Debug Credential Loading

```bash
# Enable debug logging
export SEQUEL_LOG_LEVEL=DEBUG
export SEQUEL_LOG_FILE=/tmp/sequel-auth-debug.log

# Launch Sequel
sequel

# Check logs for authentication details
grep -i "credential\|auth" /tmp/sequel-auth-debug.log
```

**Sample Debug Output:**
```
DEBUG:sequel.services.auth:Loading Google Cloud Application Default Credentials...
INFO:sequel.services.auth:Successfully loaded credentials for project: my-project
DEBUG:sequel.services.base:Executing list_projects (attempt 1/4)
```

---

## Example 6: Performance Tuning

### Measure Current Performance

```bash
# Enable debug logging to see API call timings
export SEQUEL_LOG_LEVEL=DEBUG
export SEQUEL_LOG_FILE=/tmp/sequel-perf.log

sequel

# Analyze log file
grep "Executing\|succeeded" /tmp/sequel-perf.log

# Sample output:
# DEBUG: Executing list_projects (attempt 1/4)
# INFO: list_projects succeeded after 1 attempts
# DEBUG: Executing list_clusters(project=my-project) (attempt 1/4)
```

### Optimize Cache Settings

**Problem:** API calls are slow, want to reduce repeated calls

**Solution:** Increase cache TTLs

```bash
# Increase cache durations
export SEQUEL_CACHE_TTL_PROJECTS=1800   # 30 minutes
export SEQUEL_CACHE_TTL_RESOURCES=900   # 15 minutes

sequel
```

**Trade-off:** Data may be stale, but fewer API calls

### Optimize for Many Projects

**Problem:** 100+ projects, slow initial load

**Solution:** Filter to relevant projects only

```bash
# Show only projects matching pattern
export SEQUEL_PROJECT_FILTER_REGEX="^(prod|staging)-.*"

sequel

# This reduces:
# - Initial project listing
# - Memory usage
# - Tree rendering time
```

### Optimize Network Timeout

**Problem:** Slow network, frequent timeouts

**Solution:** Increase timeout and adjust retries

```bash
# Longer timeout for slow networks
export SEQUEL_API_TIMEOUT=60

# More retries with longer delays
export SEQUEL_API_MAX_RETRIES=5
export SEQUEL_API_RETRY_DELAY=2.0
export SEQUEL_API_RETRY_BACKOFF=2.5

sequel
```

**Calculation:** Retry delays will be: 2s, 5s, 12.5s, 31.25s

---

## Example 7: Working with API Quotas

### Understanding Quota Errors

When you hit API quota limits:

```
QuotaExceededError: API quota exceeded for list_clusters.
Waiting 60s before retry. Error: Quota exceeded for quota metric
'Read requests' and limit 'Read requests per minute' ...
```

**Sequel's automatic handling:**
1. Detects quota exceeded error
2. Extracts retry-after time from error (or uses `SEQUEL_GCLOUD_QUOTA_WAIT_TIME`)
3. Waits specified time
4. Automatically retries operation

### Customize Quota Wait Time

```bash
# Wait 2 minutes instead of default 60 seconds
export SEQUEL_GCLOUD_QUOTA_WAIT_TIME=120

sequel
```

### Reduce API Calls with Caching

```bash
# Aggressive caching to minimize API calls
export SEQUEL_CACHE_TTL_PROJECTS=3600    # 1 hour
export SEQUEL_CACHE_TTL_RESOURCES=1800   # 30 minutes

sequel

# Result: Fewer API calls, less likely to hit quotas
```

### Check Current API Usage

```bash
# In Google Cloud Console:
# Navigation Menu → APIs & Services → Dashboard
# View API usage graphs

# For specific API (e.g., Compute Engine):
# Navigation Menu → APIs & Services → Compute Engine API → Quotas
```

---

## Example 8: Credential Scrubbing Verification

### Verify Credentials Are Scrubbed from Logs

```bash
# Enable logging
export SEQUEL_LOG_LEVEL=DEBUG
export SEQUEL_LOG_FILE=/tmp/sequel-security-test.log

sequel

# Check log file for credentials (should not find any)
grep -i "token\|bearer\|key\|password\|secret" /tmp/sequel-security-test.log

# Credentials should appear as:
# "Authorization": "Bearer [REDACTED]"
# "api_key": "[REDACTED]"
# "password": "[REDACTED]"
```

**Scrubbing Patterns:**
- `Bearer <token>` → `Bearer [REDACTED]`
- `"token": "abc123"` → `"token": "[REDACTED]"`
- `api_key=xyz789` → `api_key=[REDACTED]`
- Private keys and certificates
- Base64-encoded credentials

### Disable Scrubbing (Not Recommended)

```bash
# Only for local debugging, NEVER in production
export SEQUEL_ENABLE_CREDENTIAL_SCRUBBING=false

sequel
```

**Warning:** This will expose credentials in logs! Use only in secure, isolated environments.

---

## Example 9: Custom Configuration Directory

### Use Non-Standard Config Location

```bash
# Set custom config directory
export SEQUEL_CONFIG_DIR=~/my-custom-config

# Or use XDG standard
export XDG_CONFIG_HOME=~/my-configs

# Create config file
mkdir -p ~/my-custom-config/sequel
cat > ~/my-custom-config/sequel/config.json <<EOF
{
  "ui": {
    "theme": "tokyo-night"
  },
  "filters": {
    "project_regex": "^dev-.*"
  }
}
EOF

# Launch Sequel
sequel

# Sequel will load config from:
# ~/my-custom-config/sequel/config.json
```

---

## Example 10: Debugging Specific API Errors

### Permission Denied Errors

**Error:**
```
PermissionError: Permission denied for list_clusters: Missing permission:
container.clusters.list. Grant this permission in IAM or contact your administrator.
```

**Debug Steps:**

```bash
# 1. Check current IAM permissions
gcloud projects get-iam-policy my-project \
    --flatten="bindings[].members" \
    --filter="bindings.members:user:your-email@example.com" \
    --format="table(bindings.role)"

# 2. Check which APIs are enabled
gcloud services list --enabled --project=my-project | grep container

# 3. Enable required API if not enabled
gcloud services enable container.googleapis.com --project=my-project

# 4. Grant required permission
gcloud projects add-iam-policy-binding my-project \
    --member="user:your-email@example.com" \
    --role="roles/container.viewer"

# 5. Retry in Sequel (press 'r' to refresh)
```

### API Not Enabled Errors

**Error:**
```
ServiceNotEnabledError: Google Cloud API not enabled: container.googleapis.com.
Enable it at: https://console.cloud.google.com/apis/library/container.googleapis.com
```

**Solution:**

```bash
# Enable API via gcloud
gcloud services enable container.googleapis.com --project=my-project

# Or click the link in error message to enable via Console

# Refresh Sequel (press 'r')
```

### Network Timeout Errors

**Error:**
```
NetworkError: list_clusters(project=my-project) timed out after 30s
```

**Solution:**

```bash
# Increase timeout
export SEQUEL_API_TIMEOUT=60

# Check network connectivity to Google Cloud
ping -c 4 www.googleapis.com

# Check firewall rules if on corporate network

# Relaunch Sequel
sequel
```

---

## Example 11: Testing and Development Setup

### Development Mode with Hot Reload

```bash
# Install in editable mode
pip install -e .

# Make code changes to src/sequel/...

# Changes take effect immediately on next Sequel launch
# No need to reinstall

# Launch for testing
sequel --debug --log-file /tmp/sequel-dev.log
```

### Running Tests Before Changes

```bash
# Activate virtual environment
source venv/bin/activate

# Run full test suite
pytest --cov

# Run specific test file
pytest tests/unit/services/test_projects.py

# Run with verbose output
pytest -v

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

### Code Quality Checks

```bash
# Run linter
ruff check src tests

# Auto-fix linting issues
ruff check --fix src tests

# Run type checker
mypy src

# Run all quality checks
ruff check src tests && mypy src && pytest --cov --cov-fail-under=60
```

---

## Example 12: Comparing Configurations

### Scenario: Development vs Production Config

**Development Config:** `~/.config/sequel/config.dev.json`
```json
{
  "ui": {
    "theme": "textual-dark"
  },
  "filters": {
    "project_regex": "^dev-.*"
  }
}
```

**Production Config:** `~/.config/sequel/config.prod.json`
```json
{
  "ui": {
    "theme": "textual-dark"
  },
  "filters": {
    "project_regex": "^prod-.*"
  }
}
```

**Switching Configs:**

```bash
# Use dev config
cp ~/.config/sequel/config.dev.json ~/.config/sequel/config.json
sequel

# Use prod config
cp ~/.config/sequel/config.prod.json ~/.config/sequel/config.json
sequel

# Or use environment variable instead of config file
export SEQUEL_PROJECT_FILTER_REGEX="^dev-.*"
sequel

export SEQUEL_PROJECT_FILTER_REGEX="^prod-.*"
sequel
```

---

## Example 13: Monitoring Cache Performance

### Enable Cache Statistics

```bash
# Debug mode shows cache stats
export SEQUEL_LOG_LEVEL=DEBUG
export SEQUEL_LOG_FILE=/tmp/sequel-cache.log

sequel

# Use the app for a while, navigate projects/resources

# Check cache statistics in logs
grep -i "cache" /tmp/sequel-cache.log

# Sample output:
# DEBUG:sequel.cache.memory:Cache miss: projects:all
# DEBUG:sequel.cache.memory:Cache set: projects:all (TTL: 600s, size: 12345 bytes)
# DEBUG:sequel.cache.memory:Cache hit: projects:all
# DEBUG:sequel.cache.memory:Cache hit: cloudsql:instances:my-project
```

**Watch status bar for cache hit rate:**
```
Cache: 73% hit rate
```

**High hit rate (>70%)**: Good caching, fewer API calls
**Low hit rate (<30%)**: Increase cache TTLs or check access patterns

---

## Example 14: Scripting and Automation

### Automated Project Auditing

```bash
#!/bin/bash
# audit-projects.sh

# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=~/sequel-sa-key.json

# Set project filter
export SEQUEL_PROJECT_FILTER_REGEX="^prod-.*"

# Enable debug logging
export SEQUEL_LOG_LEVEL=DEBUG
export SEQUEL_LOG_FILE=/tmp/sequel-audit-$(date +%Y%m%d).log

# Launch Sequel in background (if running headless)
# Note: Sequel is interactive TUI, so this is just for logging
# For actual automation, use gcloud CLI or Python scripts instead

echo "Launching Sequel with audit configuration..."
echo "Log file: $SEQUEL_LOG_FILE"
echo "Filter: $SEQUEL_PROJECT_FILTER_REGEX"

sequel
```

**Note:** Sequel is designed for interactive use. For automation, consider using Google Cloud Client Libraries directly in Python scripts.

---

## Example 15: Multi-Organization Setup

### Working with Multiple Organizations

```bash
# Organization 1 (using user credentials)
unset GOOGLE_APPLICATION_CREDENTIALS
gcloud auth application-default login --project=org1-project
sequel

# Organization 2 (using service account)
export GOOGLE_APPLICATION_CREDENTIALS=~/org2-sa-key.json
sequel

# Organization 3 (different user)
unset GOOGLE_APPLICATION_CREDENTIALS
gcloud auth application-default login --account=user@org3.com
sequel
```

### Switching Between Accounts

```bash
# List available gcloud accounts
gcloud auth list

# Switch active account
gcloud config set account user@different-org.com

# Update ADC for new account
gcloud auth application-default login

# Launch Sequel with new credentials
sequel
```

---

## Troubleshooting Tips

### Problem: Config changes not taking effect

**Solution:**
1. Check file location: `cat ~/.config/sequel/config.json`
2. Verify JSON syntax: `python -m json.tool ~/.config/sequel/config.json`
3. Remember: Environment variables override config file
4. Restart Sequel after config changes

### Problem: Slow performance with many projects

**Solution:**
1. Filter projects: Set `project_regex` in config
2. Increase cache TTLs
3. Don't expand all nodes at once (lazy loading)
4. Use faster network connection

### Problem: Can't see certain resources

**Solution:**
1. Check IAM permissions
2. Verify API is enabled
3. Check project filter isn't excluding it
4. Try refreshing (press 'r')

---

## Next Steps

- See [Configuration Guide](../user-guide/configuration.md) for all config options
- See [Troubleshooting Guide](../user-guide/troubleshooting.md) for error solutions
- See [Development Guide](../contributing/development.md) for contributing

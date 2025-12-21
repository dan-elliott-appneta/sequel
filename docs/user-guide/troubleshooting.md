# Troubleshooting Guide

## Common Errors and Solutions

### Authentication Errors

#### "Google Cloud credentials not found"

**Cause**: No valid Google Cloud credentials found.

**Solution**:
```bash
# Recommended: Use gcloud CLI
gcloud auth application-default login

# Or: Set service account key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

#### "Failed to refresh expired credentials"

**Cause**: Credentials have expired and cannot be refreshed.

**Solution**:
```bash
gcloud auth application-default login
```

#### "Permission denied" when viewing resources

**Cause**: Insufficient IAM permissions.

**Solution**:
1. Ensure your account has **Viewer** role or specific read permissions
2. Check required permissions for each resource type
3. Verify APIs are enabled in your project

### API Errors

#### "API has not been enabled"

**Cause**: Required Google Cloud API is not enabled in the project.

**Solution**:
Enable the required API in Google Cloud Console:
- Cloud Resource Manager API
- Compute Engine API
- Kubernetes Engine API
- Secret Manager API
- Cloud DNS API

Or via gcloud:
```bash
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable dns.googleapis.com
```

#### "API quota exceeded"

**Cause**: You've hit API rate limits.

**Behavior**: Sequel automatically waits (default: 60 seconds) and retries.

**Solutions**:
1. Wait for the automatic retry
2. Increase quota in Google Cloud Console
3. Reduce API call frequency by using caching
4. Adjust wait time via `SEQUEL_GCLOUD_QUOTA_WAIT_TIME`

#### "Deadline exceeded" or timeout errors

**Cause**: API request took too long.

**Solutions**:
1. Check network connectivity
2. Increase timeout: `export SEQUEL_API_TIMEOUT=60`
3. Retry the operation with `r` key

### Performance Issues

#### Slow loading

**Possible causes and solutions**:

1. **Many projects**: Filter projects using regex
   ```json
   {
     "filters": {
       "project_regex": "^prod-.*"
     }
   }
   ```

2. **Network latency**: Check network connection to Google Cloud APIs

3. **Large datasets**: This is normal. Resources load lazily as you expand nodes.

4. **Cache disabled**: Enable caching (default behavior)
   ```bash
   # Don't use --no-cache unless debugging
   sequel
   ```

#### High memory usage

**Cause**: Large number of resources cached.

**Solutions**:
1. Reduce cache TTL:
   ```bash
   export SEQUEL_CACHE_TTL_PROJECTS=300  # 5 minutes instead of 10
   export SEQUEL_CACHE_TTL_RESOURCES=120  # 2 minutes instead of 5
   ```

2. Restart Sequel to clear cache

3. Filter projects to reduce total resource count

### UI Issues

#### Text rendering problems

**Cause**: Terminal doesn't support required features.

**Solutions**:
1. Use a modern terminal emulator (iTerm2, Windows Terminal, GNOME Terminal)
2. Ensure terminal supports Unicode and colors
3. Try different themes: Press `Ctrl+P` and select a theme

#### Syntax highlighting not working

**Cause**: Missing tree-sitter dependencies.

**Solution**:
```bash
pip install tree-sitter tree-sitter-languages tree-sitter-json
```

#### Keyboard shortcuts not working

**Possible causes**:
1. Terminal is capturing the key combination
2. Focus is on wrong pane (click in the pane first)
3. Modal dialog is open (press `Esc` to dismiss)

### Installation Issues

#### "Command not found: sequel"

**Solutions**:
1. Ensure Python scripts directory is in PATH
2. Use: `python -m sequel.cli`
3. Reinstall: `pip install --force-reinstall -e .`

#### Import errors

**Solutions**:
1. Verify Python version: `python --version` (must be 3.11+)
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Create fresh virtual environment

### Configuration Issues

#### Config file changes not taking effect

**Solutions**:
1. Verify file location: `~/.config/sequel/config.json`
2. Check JSON syntax is valid
3. Remember: Environment variables override config file
4. Restart Sequel after changes

#### Project filter not working

**Solutions**:
1. Verify regex syntax is correct
2. Test regex separately
3. Use empty string to disable: `"project_regex": ""`
4. Use double backslashes in JSON: `"\\d+"`

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
sequel --debug --log-file /tmp/sequel-debug.log
```

Then check the log file:
```bash
tail -f /tmp/sequel-debug.log
```

## Error Recovery Features

Sequel includes automatic error recovery:

### Automatic Credential Refresh

If credentials expire during runtime, Sequel attempts to refresh them automatically.

### Quota Wait and Retry

When hitting API quotas, Sequel:
1. Detects quota exceeded error
2. Extracts retry-after time from error message
3. Waits the specified time (default: 60 seconds)
4. Automatically retries the operation

### Exponential Backoff

For transient errors, Sequel retries with exponential backoff:
- Attempt 1: Wait 1 second
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- Maximum: 3 retries (configurable via `SEQUEL_API_MAX_RETRIES`)

## Getting Help

If you encounter issues not covered here:

1. Check logs with `--debug --log-file` flags
2. Search GitHub issues: https://github.com/dan-elliott-appneta/sequel/issues
3. Create a new issue with:
   - Sequel version (`sequel --version`)
   - Python version (`python --version`)
   - Operating system
   - Full error message
   - Debug log (with credentials scrubbed)

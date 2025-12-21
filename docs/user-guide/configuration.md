# Configuration Guide

Sequel supports configuration through environment variables and a JSON configuration file.

**Configuration Precedence** (highest to lowest):
1. Environment variables
2. Config file (`~/.config/sequel/config.json`)
3. Default values

## Config File Location

Default: `~/.config/sequel/config.json`

Override with environment variable:
- `SEQUEL_CONFIG_DIR`: Set custom config directory
- `XDG_CONFIG_HOME`: Follows XDG Base Directory specification

## Config File Format

The config file uses JSON format with the following structure:

```json
{
  "ui": {
    "theme": "textual-dark"
  },
  "filters": {
    "project_regex": "^s[d|v|p]ap[n|nc]gl.*$"
  }
}
```

## Configuration Options

### API Configuration

| Environment Variable | Config File | Default | Description |
|---------------------|-------------|---------|-------------|
| `SEQUEL_API_TIMEOUT` | N/A | `30` | API request timeout (seconds) |
| `SEQUEL_API_MAX_RETRIES` | N/A | `3` | Maximum retry attempts |
| `SEQUEL_API_RETRY_DELAY` | N/A | `1.0` | Initial retry delay (seconds) |
| `SEQUEL_API_RETRY_BACKOFF` | N/A | `2.0` | Exponential backoff multiplier |

### Cache Configuration

| Environment Variable | Config File | Default | Description |
|---------------------|-------------|---------|-------------|
| `SEQUEL_CACHE_ENABLED` | N/A | `true` | Enable/disable caching |
| `SEQUEL_CACHE_TTL_PROJECTS` | N/A | `600` | Project cache TTL (seconds) |
| `SEQUEL_CACHE_TTL_RESOURCES` | N/A | `300` | Resource cache TTL (seconds) |

### Logging Configuration

| Environment Variable | Config File | Default | Description |
|---------------------|-------------|---------|-------------|
| `SEQUEL_LOG_LEVEL` | N/A | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `SEQUEL_LOG_FILE` | N/A | None | Log file path (optional) |
| `SEQUEL_ENABLE_CREDENTIAL_SCRUBBING` | N/A | `true` | Enable credential scrubbing in logs |

### Google Cloud Configuration

| Environment Variable | Config File | Default | Description |
|---------------------|-------------|---------|-------------|
| `SEQUEL_GCLOUD_PROJECT_ID` | N/A | None | Default GCloud project ID |
| `SEQUEL_GCLOUD_QUOTA_WAIT_TIME` | N/A | `60` | Seconds to wait on quota errors |

### Project Filtering

| Environment Variable | Config File | Default | Description |
|---------------------|-------------|---------|-------------|
| `SEQUEL_PROJECT_FILTER_REGEX` | `filters.project_regex` | `^s[d\|v\|p]ap[n\|nc]gl.*$` | Regex to filter projects (empty = show all) |

### UI Configuration

| Environment Variable | Config File | Default | Description |
|---------------------|-------------|---------|-------------|
| `SEQUEL_THEME` | `ui.theme` | `textual-dark` | Textual theme name |

## Example Configurations

### Disable Caching

**Via Environment Variable:**
```bash
export SEQUEL_CACHE_ENABLED=false
sequel
```

**Via CLI:**
```bash
sequel --no-cache
```

### Enable Debug Logging

**Via Environment Variable:**
```bash
export SEQUEL_LOG_LEVEL=DEBUG
export SEQUEL_LOG_FILE=/tmp/sequel.log
sequel
```

**Via CLI:**
```bash
sequel --debug --log-file /tmp/sequel.log
```

### Show All Projects (No Filter)

**Via Environment Variable:**
```bash
export SEQUEL_PROJECT_FILTER_REGEX=""
sequel
```

**Via Config File:**
```json
{
  "filters": {
    "project_regex": ""
  }
}
```

### Change Theme

Themes are persisted automatically when changed via the command palette (Ctrl+P).

**Available themes:**
- textual-dark
- textual-light
- catppuccin
- dracula
- gruvbox
- monokai
- nord
- solarized-dark
- solarized-light
- tokyo-night
- (and others supported by Textual)

**Via Config File:**
```json
{
  "ui": {
    "theme": "monokai"
  }
}
```

**Via Environment Variable:**
```bash
export SEQUEL_THEME=monokai
sequel
```

## Troubleshooting

### Config file not being read

1. Check file location: `cat ~/.config/sequel/config.json`
2. Verify JSON syntax is valid
3. Check file permissions (must be readable)

### Environment variables not working

1. Ensure exact variable names (case-sensitive)
2. Verify with: `echo $SEQUEL_LOG_LEVEL`
3. Remember: environment variables override config file

### Project filter not working

1. Test regex pattern separately
2. Empty string (`""`) disables filtering
3. Check syntax: use double backslashes in JSON (`\\`)

# Basic Usage Examples

This guide provides step-by-step examples for common Sequel workflows.

## Prerequisites

Before using Sequel, ensure you have:
- Python 3.11 or higher installed
- Google Cloud SDK installed
- Valid Google Cloud credentials configured

## Example 1: First Time Setup and Launch

### Step 1: Install Sequel

```bash
# Clone the repository
git clone https://github.com/dan-elliott-appneta/sequel.git
cd sequel

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Step 2: Configure Authentication

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Follow the browser prompts to authenticate
# This creates credentials at:
# ~/.config/gcloud/application_default_credentials.json
```

### Step 3: Launch Sequel

```bash
# Start Sequel with default settings
sequel

# The application will:
# 1. Load credentials from gcloud
# 2. Display all accessible projects in the tree
# 3. Show detail pane on the right
# 4. Display status bar at bottom
```

**Expected Output:**
```
┌─────────────────────────────────────────────────────────┐
│  Sequel - GCP Resource Browser                  v0.1.0  │
├───────────────────┬─────────────────────────────────────┤
│ GCP Resources     │                                     │
│  ├─ 📁 Project 1  │   (Select a resource to view)       │
│  ├─ 📁 Project 2  │                                     │
│  └─ 📁 Project 3  │                                     │
├───────────────────┴─────────────────────────────────────┤
│  q: Quit | r: Refresh | ?: Help | j/k/↑↓: Navigate     │
└─────────────────────────────────────────────────────────┘
```

---

## Example 2: Browsing Projects and Resources

### Navigating the Tree

```
1. Press 'j' or '↓' to move down to the first project
2. Press 'l' or '→' to expand the project
3. You'll see resource categories:
   📁 My Project
     ├─ 🌐 Cloud DNS
     ├─ ☁️  Cloud SQL
     ├─ 💻 Instance Groups
     ├─ ⎈  GKE Clusters
     ├─ 🔐 Secrets
     └─ 👤 Service Accounts

4. Press 'j' to move to "Cloud SQL"
5. Press 'l' to expand Cloud SQL
6. You'll see Cloud SQL instances:
   ☁️  Cloud SQL
     └─ my-database-1

7. Press 'Enter' on the instance to view details
8. The detail pane shows JSON with syntax highlighting
```

### Viewing Resource Details

When you select a resource (press Enter or click):

```json
{
  "name": "my-database-1",
  "project": "my-project",
  "region": "us-central1",
  "databaseVersion": "POSTGRES_14",
  "state": "RUNNABLE",
  "ipAddresses": [
    {
      "type": "PRIMARY",
      "ipAddress": "10.1.2.3"
    }
  ],
  ...
}
```

The detail pane provides:
- Syntax-highlighted JSON
- Scrollable view
- VIM navigation (j/k/h/l/g/G/0/$)
- Text selection and copying

---

## Example 3: Copying Data from Detail Pane

### Method 1: VIM Yanking

```
1. Navigate to a resource (e.g., GKE cluster)
2. The detail pane shows the resource JSON
3. Click in the detail pane to focus it
4. Use VIM commands:
   - Press 'V' to enter visual mode (if supported)
   - Or use mouse to select text
   - Press 'y' to yank (copy) selected text
   OR
   - Press 'Y' to yank the current line

5. Paste into another application (Ctrl+V / Cmd+V)
```

**Example:**
```
Selected text:
  "clusterIpv4Cidr": "10.52.0.0/14"

Press 'y' → Text copied to clipboard
```

### Method 2: Mouse Selection

```
1. Select a resource to view details
2. Click and drag to select text in detail pane
3. Copy with Ctrl+C (Linux/Windows) or Cmd+C (Mac)
4. Paste wherever needed
```

---

## Example 4: Exploring GKE Clusters

### Viewing Cluster Hierarchy

```
1. Expand a project
2. Navigate to "⎈ GKE Clusters"
3. Press 'l' to expand
4. You see clusters:
   ⎈  GKE Clusters
     └─ production-cluster

5. Expand the cluster (press 'l')
6. You see node pools:
   production-cluster
     ├─ default-pool
     └─ compute-pool

7. Expand a node pool to see nodes:
   default-pool
     ├─ Node: gke-prod-default-pool-abc123
     ├─ Node: gke-prod-default-pool-def456
     └─ Node: gke-prod-default-pool-ghi789

8. Select a node to view details
```

### Viewing Node Details

```json
{
  "name": "gke-prod-default-pool-abc123",
  "status": {
    "state": "RUNNING"
  },
  "config": {
    "machineType": "e2-standard-4",
    "diskSizeGb": 100,
    "imageType": "COS_CONTAINERD"
  },
  "version": "1.27.3-gke.100"
}
```

---

## Example 5: Refreshing Data

### Manual Refresh

```bash
# While Sequel is running:
# Press 'r' to refresh the current view

# Status bar will show:
#   ⏳ Refreshing resources...

# After refresh completes:
#   Updated 0s ago
```

**What Gets Refreshed:**
- All projects in the tree
- Currently expanded resources
- Cache is invalidated and reloaded from API

**When to Refresh:**
- After making changes in Google Cloud Console
- To see latest resource states
- When data appears stale

### Automatic Cache Behavior

```
Default TTLs:
- Projects: 10 minutes (600 seconds)
- Resources: 5 minutes (300 seconds)

Example timeline:
0:00 - Load projects (API call)
0:30 - Load Cloud SQL (API call)
2:00 - View same project (cache hit - no API call)
5:30 - View Cloud SQL again (cache expired - API call)
10:01 - View projects again (cache expired - API call)
```

---

## Example 6: Using Keyboard Shortcuts

### Navigation Shortcuts

| Action | Keys | Example |
|--------|------|---------|
| Move down | `j` or `↓` | Navigate to next project |
| Move up | `k` or `↑` | Go back to previous project |
| Expand node | `l` or `→` | Expand "Cloud SQL" category |
| Collapse node | `h` or `←` | Collapse "GKE Clusters" |
| Go to top | `g` | Jump to first project |
| Go to bottom | `G` | Jump to last visible item |
| Toggle expand | `Enter` | Expand/collapse selected node |

### Application Shortcuts

| Action | Key | Description |
|--------|-----|-------------|
| Quit | `q` | Exit Sequel |
| Refresh | `r` | Reload resources from API |
| Help | `?` | Show help modal |
| Command Palette | `Ctrl+P` | Open command palette (themes) |
| Dismiss Modal | `Esc` | Close error/help dialogs |

### Detail Pane Shortcuts (VIM Mode)

| Action | Key | Description |
|--------|-----|-------------|
| Scroll down | `j` | Move cursor down |
| Scroll up | `k` | Move cursor up |
| Scroll left | `h` | Move cursor left |
| Scroll right | `l` | Move cursor right |
| Page up | `g` | Scroll up one page |
| Page down | `G` | Scroll down one page |
| Line start | `0` | Jump to line start |
| Line end | `$` | Jump to line end |
| Copy selection | `y` | Yank selected text |
| Copy line | `Y` | Yank current line |

---

## Example 7: Changing Themes

### Using Command Palette

```
1. Press 'Ctrl+P' to open command palette
2. Type or scroll to select a theme:
   - textual-dark (default)
   - textual-light
   - dracula
   - monokai
   - nord
   - gruvbox
   - solarized-dark
   - solarized-light
   - tokyo-night
   - catppuccin

3. Press 'Enter' to apply theme
4. Theme is automatically saved to:
   ~/.config/sequel/config.json
5. Next launch will use the selected theme
```

**Theme is persisted:**
```json
{
  "ui": {
    "theme": "dracula"
  }
}
```

---

## Example 8: Viewing Secret Manager

### Viewing Secret Metadata

```
1. Expand a project
2. Navigate to "🔐 Secrets"
3. Press 'l' to expand
4. You see secrets:
   🔐 Secrets
     ├─ database-password
     ├─ api-key
     └─ tls-cert

5. Select a secret to view metadata
```

**Important:** Sequel shows **metadata only**, never secret values:

```json
{
  "name": "projects/my-project/secrets/database-password",
  "replication": {
    "automatic": {}
  },
  "createTime": "2024-01-15T10:30:00Z",
  "labels": {
    "env": "production"
  }
}
```

---

## Example 9: Viewing DNS Records

### Navigating DNS Hierarchy

```
1. Expand a project
2. Navigate to "🌐 Cloud DNS"
3. Press 'l' to expand managed zones:
   🌐 Cloud DNS
     ├─ example.com.
     └─ internal.local.

4. Expand a zone (e.g., example.com.)
5. View DNS records:
   example.com.
     ├─ A: example.com. → 192.0.2.1
     ├─ CNAME: www.example.com. → example.com.
     ├─ MX: example.com. → mail.example.com.
     └─ TXT: example.com. → "v=spf1 ..."

6. Select a record to view full details
```

**DNS Record Details:**
```json
{
  "name": "www.example.com.",
  "type": "CNAME",
  "ttl": 300,
  "rrdatas": [
    "example.com."
  ]
}
```

---

## Example 10: Viewing Instance Groups and VMs

### Exploring Compute Resources

```
1. Expand a project
2. Navigate to "💻 Instance Groups"
3. Press 'l' to expand:
   💻 Instance Groups
     ├─ us-central1-a: web-servers
     ├─ us-central1-a: api-servers
     └─ us-east1-b: batch-workers

4. Expand an instance group (e.g., web-servers)
5. View VM instances:
   web-servers
     ├─ web-server-01
     ├─ web-server-02
     └─ web-server-03

6. Select a VM to view details
```

**VM Instance Details:**
```json
{
  "name": "web-server-01",
  "zone": "us-central1-a",
  "machineType": "n1-standard-2",
  "status": "RUNNING",
  "networkInterfaces": [
    {
      "networkIP": "10.128.0.2",
      "accessConfigs": [
        {
          "natIP": "35.1.2.3"
        }
      ]
    }
  ]
}
```

---

## Example 11: Getting Help

### Viewing Keyboard Shortcuts

```
1. Press '?' to show help modal
2. View all keyboard shortcuts:
   - Tree navigation (j/k/h/l/g/G)
   - Detail pane VIM mode
   - Application actions (q/r/Ctrl+P)

3. Press 'Esc' to close help
```

---

## Example 12: Quitting Sequel

### Clean Exit

```
Press 'q' to quit

# Sequel will:
# 1. Close all connections
# 2. Save any configuration changes
# 3. Exit cleanly to terminal
```

---

## Common Workflows

### Workflow 1: Check Database Status

```
1. Launch Sequel
2. Navigate to project → Cloud SQL
3. View instance status in detail pane
4. Check "state" field (should be "RUNNABLE")
5. Verify IP addresses and configuration
```

### Workflow 2: Audit Service Accounts

```
1. Launch Sequel
2. Navigate to project → Service Accounts
3. Browse list of service accounts
4. Select each to view:
   - Email address
   - Created date
   - Display name
5. Copy email addresses for IAM review
```

### Workflow 3: Verify GKE Cluster Configuration

```
1. Navigate to project → GKE Clusters → cluster
2. View cluster details:
   - Kubernetes version
   - Node pool configurations
   - Network settings
3. Expand node pools
4. Check node counts and machine types
5. Verify cluster is properly configured
```

---

## Tips for Efficient Usage

1. **Use VIM bindings** for faster navigation
   - `j/k` is faster than arrow keys
   - `g/G` jumps to top/bottom instantly
   - `h/l` for smart expand/collapse

2. **Leverage caching**
   - Data is cached for 5-10 minutes
   - No need to refresh constantly
   - Press 'r' only when needed

3. **Filter projects** (see Advanced Examples)
   - Use regex to show only relevant projects
   - Reduces clutter and improves performance

4. **Copy JSON efficiently**
   - Use 'Y' to copy entire lines
   - Use 'y' with visual selection for specific fields
   - Mouse selection works too

5. **Watch the status bar**
   - Shows current operation
   - Displays cache hit rate
   - Indicates last refresh time

---

## Next Steps

- See [Advanced Usage Examples](advanced.md) for:
  - Project filtering with regex
  - Custom configuration
  - Debug logging
  - Performance tuning

- See [Troubleshooting Guide](../user-guide/troubleshooting.md) for:
  - Common errors and solutions
  - Permission issues
  - API quota management

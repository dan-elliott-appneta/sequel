# Authentication Guide

Sequel uses Google Cloud Application Default Credentials (ADC) for authentication.

## Authentication Methods

ADC checks for credentials in the following order:

1. **GOOGLE_APPLICATION_CREDENTIALS** environment variable (service account key file)
2. **gcloud CLI** configuration (`gcloud auth application-default login`)
3. **GCE/GKE metadata server** (when running on Google Cloud)

## Required Scopes

Sequel uses the read-only cloud platform scope:
- `https://www.googleapis.com/auth/cloud-platform.read-only`

This scope allows Sequel to view (but not modify) Google Cloud resources.

## Setup Methods

### Method 1: gcloud CLI (Recommended)

This is the recommended method for local development:

```bash
# Install Google Cloud SDK if not already installed
# Visit: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login

# Verify authentication
gcloud auth application-default print-access-token
```

### Method 2: Service Account Key

For automated environments or CI/CD:

1. Create a service account in Google Cloud Console
2. Grant it the **Viewer** role (or specific read-only permissions)
3. Create and download a JSON key file
4. Set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Method 3: GCE/GKE Metadata (Automatic)

When running on Google Compute Engine or Google Kubernetes Engine, Sequel automatically uses the instance's service account. No additional configuration needed.

## Troubleshooting

### Error: "Google Cloud credentials not found"

**Solution:**
1. Run: `gcloud auth application-default login`
2. Or set: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`

### Error: "Failed to refresh expired credentials"

Credentials have expired. Re-authenticate:

```bash
gcloud auth application-default login
```

### Warning: "No project ID detected from credentials"

If Sequel cannot detect a default project ID:

1. Set explicitly via environment variable:
   ```bash
   export SEQUEL_GCLOUD_PROJECT_ID=your-project-id
   ```

2. Or configure gcloud default project:
   ```bash
   gcloud config set project your-project-id
   ```

Note: Project ID is optional. Sequel lists all projects you have access to.

### Permission Errors

If you see permission denied errors when viewing resources:

1. **Check IAM permissions**: Ensure your user/service account has the **Viewer** role or specific read permissions for the resource types you want to view.

2. **Required permissions** (at minimum):
   - `resourcemanager.projects.get`
   - `resourcemanager.projects.list`
   - Plus permissions for specific resources (e.g., `compute.instances.list`)

3. **Enable APIs**: Some APIs must be enabled in your project:
   - Cloud Resource Manager API
   - Compute Engine API (for Compute resources)
   - Kubernetes Engine API (for GKE)
   - Secret Manager API (for Secrets)
   - Cloud DNS API (for DNS zones)

## Service Account Best Practices

When using service accounts:

1. **Use minimal permissions**: Grant only the **Viewer** role or specific read-only permissions
2. **Rotate keys regularly**: Service account keys should be rotated periodically
3. **Protect key files**: Never commit key files to version control
4. **Use GCE/GKE metadata** when possible: Avoids managing key files

## Verifying Authentication

After setup, verify authentication works:

```bash
# This will fail with auth error if credentials are not valid
sequel --version  # Should output: sequel 0.1.0

# Then run the app
sequel
```

If authentication is successful, Sequel will display your accessible projects in the tree view.

# GitHub Actions Workflows

This directory contains GitHub Actions workflows for building and deploying the MCP BigQuery server.

## Docker Hub Publishing

The `docker-publish.yml` workflow automatically builds and publishes Docker images to Docker Hub.

### Setup Instructions

1. **Create a Docker Hub account** (if you don't have one):
   - Go to https://hub.docker.com/signup

2. **Create an access token**:
   - Log in to Docker Hub
   - Go to Account Settings → Security → New Access Token
   - Name: `github-actions`
   - Permissions: Read, Write, Delete
   - Copy the token (you won't see it again!)

3. **Configure GitHub Secrets**:

   Go to your GitHub repository → Settings → Secrets and variables → Actions, and add:

   | Secret Name          | Description                    | Example Value      |
   | -------------------- | ------------------------------ | ------------------ |
   | `DOCKERHUB_USERNAME` | Your Docker Hub username       | `yourusername`     |
   | `DOCKERHUB_TOKEN`    | Docker Hub access token        | `dckr_pat_xxx...`  |

4. **Push to trigger build**:
   ```bash
   git push origin main
   ```

### Workflow Features

- ✅ **Multi-architecture builds** (linux/amd64, linux/arm64)
- ✅ **Automatic tagging** based on git tags and branches
- ✅ **Pull request builds** (without pushing)
- ✅ **Build caching** for faster builds
- ✅ **README sync** to Docker Hub
- ✅ **Manual trigger** via workflow_dispatch

### Image Tags

The workflow creates the following tags:

- `latest` - Latest build from main branch
- `main` - Latest build from main branch
- `v1.2.3` - Semantic version tags (when you push a git tag)
- `v1.2` - Major.minor version
- `v1` - Major version
- `main-abc1234` - Branch name with commit SHA
- `pr-123` - Pull request number

### Using the Published Image

```bash
# Pull the latest image
docker pull yourusername/mcp-server-bigquery:latest

# Pull a specific version
docker pull yourusername/mcp-server-bigquery:v0.3.0

# Run the container
docker run -p 8080:8080 \
  -e BIGQUERY_PROJECT=your-project-id \
  -e BIGQUERY_LOCATION=us-central1 \
  -e MCP_TRANSPORT=http \
  yourusername/mcp-server-bigquery:latest
```

### Creating a Release

To publish a versioned release:

```bash
# Tag the release
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0

# The workflow will automatically build and push:
# - yourusername/mcp-server-bigquery:v0.3.0
# - yourusername/mcp-server-bigquery:v0.3
# - yourusername/mcp-server-bigquery:v0
# - yourusername/mcp-server-bigquery:latest
```

## Cloud Run Deployment

The `deploy-cloud-run.yml.example` file provides an example workflow for deploying to Google Cloud Run.

### Setup Instructions

1. **Copy the example file:**
   ```bash
   cp .github/workflows/deploy-cloud-run.yml.example .github/workflows/deploy-cloud-run.yml
   ```

2. **Create an Artifact Registry repository:**
   ```bash
   gcloud artifacts repositories create mcp-server-bigquery \
     --repository-format=docker \
     --location=us-central1 \
     --description="MCP BigQuery Server Docker images"
   ```

3. **Set up Workload Identity Federation (Recommended):**

   This is the secure, keyless authentication method for GitHub Actions.

   ```bash
   # Set variables
   export PROJECT_ID="your-gcp-project-id"
   export POOL_NAME="github-actions-pool"
   export PROVIDER_NAME="github-provider"
   export SERVICE_ACCOUNT_NAME="github-actions-sa"
   export REPO="your-github-username/mcp-server-bigquery"

   # Create Workload Identity Pool
   gcloud iam workload-identity-pools create $POOL_NAME \
     --location="global" \
     --display-name="GitHub Actions Pool"

   # Create Workload Identity Provider
   gcloud iam workload-identity-pools providers create-oidc $PROVIDER_NAME \
     --location="global" \
     --workload-identity-pool=$POOL_NAME \
     --display-name="GitHub Provider" \
     --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
     --issuer-uri="https://token.actions.githubusercontent.com"

   # Create Service Account
   gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
     --display-name="GitHub Actions Service Account"

   # Grant permissions to the service account
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"

   # Allow GitHub Actions to impersonate the service account
   gcloud iam service-accounts add-iam-policy-binding \
     $SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME/attribute.repository/$REPO"
   ```

   Note: Replace `PROJECT_NUMBER` with your actual GCP project number (find it with `gcloud projects describe $PROJECT_ID --format="value(projectNumber)"`).

4. **Configure GitHub Secrets:**

   Go to your GitHub repository → Settings → Secrets and variables → Actions, and add:

   | Secret Name              | Description                                                           | Example Value                                                                                          |
   | ------------------------ | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
   | `GCP_PROJECT_ID`         | Your GCP project ID                                                   | `my-project-123`                                                                                       |
   | `WIF_PROVIDER`           | Workload Identity Federation provider resource name                   | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider` |
   | `WIF_SERVICE_ACCOUNT`    | Service account email for Workload Identity Federation               | `github-actions-sa@my-project-123.iam.gserviceaccount.com`                                             |
   | `BIGQUERY_PROJECT`       | BigQuery project ID (can be same as GCP_PROJECT_ID or different)     | `my-data-project`                                                                                      |
   | `BIGQUERY_LOCATION`      | BigQuery location/region                                              | `us-central1` or `europe-west4`                                                                        |

5. **Optional: Service Account Key (Alternative to Workload Identity Federation):**

   If you prefer using a service account key instead of Workload Identity Federation:

   ```bash
   # Create service account
   gcloud iam service-accounts create github-actions \
     --display-name="GitHub Actions"

   # Grant permissions
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer"

   # Create and download key
   gcloud iam service-accounts keys create key.json \
     --iam-account=github-actions@$PROJECT_ID.iam.gserviceaccount.com
   ```

   Then update the workflow to use `google-github-actions/auth@v2` with `credentials_json` instead of Workload Identity Federation.

6. **Customize the workflow:**

   Edit `.github/workflows/deploy-cloud-run.yml` and adjust:
   - `REGION`: Your preferred Cloud Run region
   - `SERVICE_NAME`: Your service name
   - Resource limits (memory, CPU, instances)
   - Environment variables

7. **Push to trigger deployment:**
   ```bash
   git add .github/workflows/deploy-cloud-run.yml
   git commit -m "Add Cloud Run deployment workflow"
   git push origin main
   ```

### Workflow Features

- ✅ **Keyless authentication** using Workload Identity Federation
- ✅ **Multi-architecture support** (builds for linux/amd64)
- ✅ **Image tagging** with both commit SHA and `latest`
- ✅ **Automatic deployment** on push to main branch
- ✅ **Manual trigger** via workflow_dispatch
- ✅ **Secure secrets management** via GitHub Secrets
- ✅ **Auto-scaling** with configurable min/max instances

### Testing the Deployment

After deployment, test your Cloud Run service:

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe mcp-server-bigquery \
  --region us-central1 \
  --format 'value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health

# Expected response:
# {"status":"healthy","service":"bigquery-mcp-server"}
```

### Troubleshooting

**Build fails:**
- Check that Artifact Registry repository exists
- Verify service account has `artifactregistry.writer` role

**Deployment fails:**
- Verify service account has `run.admin` role
- Check that all required secrets are set in GitHub
- Review Cloud Run logs: `gcloud run services logs read mcp-server-bigquery --region us-central1`

**Service fails to start:**
- Check environment variables are set correctly
- Verify BigQuery permissions for the Cloud Run service account
- Review logs for authentication errors

### Cost Optimization

The example workflow configures:
- `--min-instances 0`: Scales to zero when not in use (no cost when idle)
- `--max-instances 10`: Limits maximum concurrent instances
- `--memory 512Mi`: Minimal memory allocation
- `--cpu 1`: Single CPU core

Adjust these based on your usage patterns and budget.

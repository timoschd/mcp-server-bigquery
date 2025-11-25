# GitHub Secrets Configuration

This document lists all the secrets needed for the GitHub Actions workflows.

## Required Secrets

Configure these in your GitHub repository: **Settings → Secrets and variables → Actions**

### For Docker Hub Publishing

Required for the `docker-publish.yml` workflow:

| Secret Name          | Description                              | How to Get                                                                                      |
| -------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `DOCKERHUB_USERNAME` | Your Docker Hub username                 | Your Docker Hub account username                                                                |
| `DOCKERHUB_TOKEN`    | Docker Hub access token (for image push) | Docker Hub → Account Settings → Security → New Access Token (with Read & Write permissions)    |
| `DOCKERHUB_PASSWORD` | Your Docker Hub password (for README sync) | Your actual Docker Hub account password (required for README updates via API)                 |

**Note**: The README sync feature requires your actual password due to Docker Hub API limitations. If you prefer not to store your password, you can remove the "Update Docker Hub description" step from the workflow and manually update the README on Docker Hub's website.

### For Cloud Run Deployment (Workload Identity Federation - Recommended)

| Name                  | Type | Description                                              | How to Get                                                                                                                           |
| --------------------- | ---- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `GCP_PROJECT_ID`      | Variable | Your GCP project ID                                      | `gcloud config get-value project`                                                                                                    |
| `WIF_PROVIDER`        | Secret | Workload Identity Federation provider resource name     | Format: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_NAME/providers/PROVIDER_NAME`                           |
| `WIF_SERVICE_ACCOUNT` | Secret | Service account email for Workload Identity Federation  | Format: `SERVICE_ACCOUNT_NAME@PROJECT_ID.iam.gserviceaccount.com`                                                                    |
| `BIGQUERY_PROJECT`    | Variable | BigQuery project ID (can be same or different from GCP) | Your BigQuery project ID                                                                                                             |
| `BIGQUERY_LOCATION`   | Variable | BigQuery location/region                                 | e.g., `us-central1`, `europe-west4`, `asia-northeast1`                                                                               |

**Note**: Project IDs and locations are not sensitive and can be stored as **Variables** instead of **Secrets** for better visibility. Go to **Settings → Secrets and variables → Actions → Variables tab** to add them.

### For Service Account Key (Alternative)

If not using Workload Identity Federation, use these instead:

| Name                | Type | Description                          | How to Get                                                                                      |
| ------------------- | ---- | ------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `GCP_PROJECT_ID`    | Variable | Your GCP project ID                  | `gcloud config get-value project`                                                               |
| `GCP_SA_KEY`        | Secret | Service account JSON key (base64)   | Create key, then: `cat key.json \| base64`                                                      |
| `BIGQUERY_PROJECT`  | Variable | BigQuery project ID                  | Your BigQuery project ID                                                                        |
| `BIGQUERY_LOCATION` | Variable | BigQuery location/region             | e.g., `us-central1`, `europe-west4`                                                             |

## Optional Secrets

| Secret Name           | Description                                    | Example                                  |
| --------------------- | ---------------------------------------------- | ---------------------------------------- |
| `BIGQUERY_DATASETS`   | Comma-separated list of datasets to filter    | `analytics,marketing,sales`              |
| `SLACK_WEBHOOK_URL`   | Slack webhook for deployment notifications     | `https://hooks.slack.com/services/...`   |

## Getting Your Project Number

You'll need your GCP project number (not project ID) for Workload Identity Federation:

```bash
gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"
```

## Example Values

Here's what your secrets might look like (with fake values):

```
GCP_PROJECT_ID=my-bigquery-project
WIF_PROVIDER=projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github
WIF_SERVICE_ACCOUNT=github-actions@my-bigquery-project.iam.gserviceaccount.com
BIGQUERY_PROJECT=my-bigquery-project
BIGQUERY_LOCATION=us-central1
```

## Security Best Practices

1. ✅ **Use Workload Identity Federation** instead of service account keys when possible
2. ✅ **Limit service account permissions** to only what's needed (run.admin, artifactregistry.writer)
3. ✅ **Rotate service account keys** regularly if using key-based auth
4. ✅ **Use separate service accounts** for different environments (dev, staging, prod)
5. ✅ **Enable audit logging** for service account usage
6. ✅ **Use GitHub environment protection rules** for production deployments

## Verifying Secrets

After adding secrets, you can verify they're set correctly:

1. Go to your repository on GitHub
2. Navigate to **Settings → Secrets and variables → Actions**
3. You should see all required secrets listed (values are hidden)
4. Trigger the workflow manually to test: **Actions → Deploy to Google Cloud Run → Run workflow**

## Troubleshooting

**"Secret not found" error:**
- Ensure secret names match exactly (case-sensitive)
- Verify secrets are added to the correct repository
- Check if using organization-level secrets vs repository-level secrets

**Authentication fails:**
- Verify WIF_PROVIDER format is correct
- Ensure service account has necessary IAM roles
- Check that Workload Identity binding is configured correctly

**Deployment succeeds but service fails:**
- Check Cloud Run logs for runtime errors
- Verify BIGQUERY_PROJECT and BIGQUERY_LOCATION are correct
- Ensure Cloud Run service account has BigQuery permissions

# BigQuery MCP server

[![Build and Push to Docker Hub](https://github.com/timoschd/mcp-server-bigquery/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/timoschd/mcp-server-bigquery/actions/workflows/docker-publish.yml)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-timoschd%2Fmcp--server--bigquery-blue?logo=docker)](https://hub.docker.com/r/timoschd/mcp-server-bigquery)

A Model Context Protocol server that provides access to BigQuery. This server enables LLMs to inspect database schemas and execute queries.

**Features:**
- 🔍 Execute SELECT queries on BigQuery datasets
- 📋 List all accessible tables across datasets
- 📊 Retrieve detailed table schemas
- 🔐 Service account authentication support
- 🎯 Dataset filtering for security and performance
- 🚀 Dual transport support (stdio for local, HTTP/SSE for cloud deployment)

## Deployment Options

This server can be deployed in multiple ways to suit different use cases:

- **📦 PyPI Package** - Install via `uvx` or `uv` for local use with Claude Desktop or other MCP clients
- **🐳 Docker Hub** - Pre-built multi-architecture images available at [`timoschd/mcp-server-bigquery`](https://hub.docker.com/r/timoschd/mcp-server-bigquery)
- **☁️ Google Cloud Run** - Deploy as a serverless HTTP/SSE endpoint with automatic scaling
- **🔧 Local Development** - Use Podman Compose for containerized local development

All deployment methods support both **stdio** (for local MCP clients) and **HTTP/SSE** (for cloud/remote access) transports.

## Table of Contents

- [Deployment Options](#deployment-options)
- [Components](#components)
- [Configuration](#configuration)
- [Quickstart](#quickstart)
  - [Installing via Smithery](#installing-via-smithery)
  - [Claude Desktop](#claude-desktop)
  - [Docker Deployment](#docker-deployment)
- [Development](#development)
- [Transport Modes](#transport-modes)
- [Authentication](#authentication)

## Components

### Tools

The server implements three tools:

- **`execute-query`**: Executes a SQL query using BigQuery dialect
  - Input: `query` (string) - SELECT SQL query to execute
  - Returns: Query results as a list of dictionaries

- **`list-tables`**: Lists all tables in the BigQuery database
  - Input: None
  - Returns: List of fully-qualified table names (format: `dataset.table`)

- **`describe-table`**: Describes the schema of a specific table
  - Input: `table_name` (string) - Fully-qualified table name (e.g., `my_dataset.my_table`)
  - Returns: Table DDL (Data Definition Language) with complete schema information

### Example Usage

Once connected to an MCP client (like Claude Desktop), you can ask questions like:

- "What tables are available in my BigQuery project?"
- "Show me the schema for the `analytics.user_events` table"
- "Query the top 10 users by activity from the `analytics.user_events` table"

The LLM will automatically use the appropriate tools to answer your questions.

## Configuration

The server can be configured either with command line arguments or environment variables.

| Argument       | Environment Variable | Required | Description                                                                                                                                                                                                                                                                                                                                                    |
| -------------- | -------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--project`    | `BIGQUERY_PROJECT`   | Yes      | The GCP project ID.                                                                                                                                                                                                                                                                                                                                            |
| `--location`   | `BIGQUERY_LOCATION`  | Yes      | The GCP location (e.g. `europe-west4`, `us-central1`).                                                                                                                                                                                                                                                                                                        |
| `--dataset`    | `BIGQUERY_DATASETS`  | No       | Only take specific BigQuery datasets into consideration. Several datasets can be specified by repeating the argument (e.g. `--dataset my_dataset_1 --dataset my_dataset_2`) or by joining them with a comma in the environment variable (e.g. `BIGQUERY_DATASETS=my_dataset_1,my_dataset_2`). If not provided, all datasets in the project will be considered. |
| `--key-file`   | `BIGQUERY_KEY_FILE`  | No       | Path to a service account key file for BigQuery. If not provided, the server will use Application Default Credentials (ADC).                                                                                                                                                                                                                                  |
| `--transport`  | `MCP_TRANSPORT`      | No       | Transport type: `stdio` (default), `http`, or `sse`. Use `stdio` for local MCP clients, `http`/`sse` for cloud deployments.                                                                                                                                                                                                                                   |
| `--port`       | `PORT` or `MCP_PORT` | No       | Port number for HTTP/SSE transport (default: 8080). Ignored when using stdio transport.                                                                                                                                                                                                                                                                       |

## Quickstart

### Install

#### Installing via Smithery

To install BigQuery Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-server-bigquery):

```bash
npx -y @smithery/cli install mcp-server-bigquery --client claude
```

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

##### Development/Unpublished Servers Configuration</summary>

```json
"mcpServers": {
  "bigquery": {
    "command": "uv",
    "args": [
      "--directory",
      "{{PATH_TO_REPO}}",
      "run",
      "mcp-server-bigquery",
      "--project",
      "{{GCP_PROJECT_ID}}",
      "--location",
      "{{GCP_LOCATION}}"
    ]
  }
}
```

##### Published Servers Configuration

```json
"mcpServers": {
  "bigquery": {
    "command": "uvx",
    "args": [
      "mcp-server-bigquery",
      "--project",
      "{{GCP_PROJECT_ID}}",
      "--location",
      "{{GCP_LOCATION}}"
    ]
  }
}
```

##### Remote Server Configuration (SSE)

To connect to a remotely deployed server (e.g., on Cloud Run):

```json
"mcpServers": {
  "bigquery": {
    "transport": "sse",
    "url": "https://your-server-url.run.app/messages"
  }
}
```

Replace `{{PATH_TO_REPO}}`, `{{GCP_PROJECT_ID}}`, `{{GCP_LOCATION}}`, and `https://your-server-url.run.app` with the appropriate values.

### Docker Deployment

The server can be deployed as a Docker container for cloud environments (e.g., Google Cloud Run, Kubernetes).

Docker images are automatically built and published to Docker Hub via GitHub Actions. You can use the pre-built images or build your own.

#### Using Pre-built Images

```bash
# Pull the latest image from Docker Hub
docker pull timoschd/mcp-server-bigquery:latest

# Or pull a specific version
docker pull timoschd/mcp-server-bigquery:v0.3.0
```

#### Building Your Own Image

```bash
docker build -t mcp-server-bigquery .
# or with Podman
podman build -t mcp-server-bigquery .
```

The repository includes a GitHub Actions workflow that automatically builds and publishes multi-architecture images (amd64/arm64) to Docker Hub. See [`.github/workflows/README.md`](.github/workflows/README.md) for setup instructions.

#### Running with Docker

**Local stdio mode:**
```bash
docker run -it \
  -e BIGQUERY_PROJECT=your-project-id \
  -e BIGQUERY_LOCATION=us-central1 \
  timoschd/mcp-server-bigquery:latest
```

**HTTP/SSE mode (for cloud deployment):**
```bash
docker run -p 8080:8080 \
  -e BIGQUERY_PROJECT=your-project-id \
  -e BIGQUERY_LOCATION=us-central1 \
  -e MCP_TRANSPORT=http \
  -e PORT=8080 \
  timoschd/mcp-server-bigquery:latest
```

**With service account authentication:**
```bash
docker run -p 8080:8080 \
  -v /path/to/key.json:/app/secrets/key.json \
  -e BIGQUERY_PROJECT=your-project-id \
  -e BIGQUERY_LOCATION=us-central1 \
  -e BIGQUERY_KEY_FILE=/app/secrets/key.json \
  -e MCP_TRANSPORT=http \
  timoschd/mcp-server-bigquery:latest
```

#### Using Podman Compose/ Docker Compose

A `podman-compose.yml` file is provided for easy local development:

```bash
# Copy and customize the environment file
cp .env.example .env

# Start the service
podman-compose up
```
OR
```bash
docker-compose up
```

The compose file supports configurable environment variables:
- `PORT`: External port mapping (default: 8085)
- `BIGQUERY_PROJECT`: Your GCP project ID
- `BIGQUERY_LOCATION`: BigQuery location/region
- `BIGQUERY_KEY_FILE`: Optional path to service account key

#### Deploying to Google Cloud Run

**Manual deployment:**

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/mcp-server-bigquery

# Deploy to Cloud Run
gcloud run deploy mcp-server-bigquery \
  --image gcr.io/YOUR_PROJECT_ID/mcp-server-bigquery \
  --platform managed \
  --region us-central1 \
  --set-env-vars BIGQUERY_PROJECT=your-project-id,BIGQUERY_LOCATION=us-central1,MCP_TRANSPORT=http \
  --allow-unauthenticated \
  --port 8080
```

**Automated deployment with GitHub Actions:**

An example GitHub Actions workflow is provided for automated deployments. See [`.github/workflows/README.md`](.github/workflows/README.md) for detailed setup instructions.

```bash
# Copy the example workflow
cp .github/workflows/deploy-cloud-run.yml.example .github/workflows/deploy-cloud-run.yml

# Configure GitHub Secrets (see workflow README for details)
# Then push to trigger deployment
git push origin main
```

---

## Development

### Building and Publishing

To prepare the package for distribution:

1. Increase the version number in `pyproject.toml`

2. Sync dependencies and update lockfile:

```bash
uv sync
```

3. Build package distributions:

```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

4. Publish to PyPI:

```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:

- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

#### Using MCP Inspector (stdio mode)

You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory {{PATH_TO_REPO}} run mcp-server-bigquery --project {{GCP_PROJECT_ID}} --location {{GCP_LOCATION}}
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

#### Testing HTTP/SSE mode

For testing the HTTP/SSE transport locally:

```bash
# Start the server in HTTP mode
uv run mcp-server-bigquery --project {{GCP_PROJECT_ID}} --location {{GCP_LOCATION}} --transport http --port 8080

# In another terminal, test the health endpoint
curl http://localhost:8080/health
```

#### Viewing Logs

The server logs to both stdout and `/tmp/mcp_bigquery_server.log`. When running in Docker:

```bash
# View container logs
docker logs <container-id>

# Or access the log file
docker exec <container-id> cat /tmp/mcp_bigquery_server.log
```

## Transport Modes

The server supports two transport modes:

### stdio (Default)
- **Use case**: Local MCP clients (Claude Desktop, CLI tools)
- **Communication**: Standard input/output streams
- **Configuration**: Default mode, no additional setup required

### HTTP/SSE
- **Use case**: Cloud deployments (Google Cloud Run, Kubernetes, remote servers)
- **Communication**: Server-Sent Events over HTTP
- **Endpoints**:
  - `GET /`: Health check endpoint
  - `GET /health`: Health check endpoint
  - `GET /messages`: SSE connection for receiving events
  - `POST /messages`: Send tool invocation requests
- **Configuration**: Set `--transport http` or `MCP_TRANSPORT=http`

#### Connecting MCP Clients to Remote SSE Server

To connect an MCP client (like Claude Desktop or Windsurf) to a remotely deployed server using SSE transport:

**Configuration example** (e.g., in `mcp_config.json` or Claude Desktop config):

```json
{
  "mcpServers": {
    "bigquery": {
      "disabled": false,
      "transport": "sse",
      "url": "https://your-server-url.run.app/messages"
    }
  }
}
```

Replace `https://your-server-url.run.app` with your actual deployment URL:
- **Cloud Run**: `https://mcp-server-bigquery-xxxxx-uc.a.run.app`
- **Custom domain**: `https://bigquery-mcp.yourdomain.com`
- **Local testing**: `http://localhost:8080`

The `/messages` path is required for SSE communication.

## Authentication

The server supports multiple authentication methods:

1. **Service Account Key File** (Recommended for production):
   ```bash
   --key-file /path/to/service-account-key.json
   # or
   export BIGQUERY_KEY_FILE=/path/to/service-account-key.json
   ```

2. **Application Default Credentials (ADC)**:
   - Used automatically when no key file is provided
   - Works with `gcloud auth application-default login`
   - Automatically available in Google Cloud environments (Cloud Run, GCE, etc.)

## Support

For questions, issues, or feedback:
- 📧 Email: [contact@timschendzielorz.com](mailto:contact@timschendzielorz.com)
- 🐛 Issues: [GitHub Issues](https://github.com/timoschd/mcp-server-bigquery/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/timoschd/mcp-server-bigquery/discussions)

## License

MIT

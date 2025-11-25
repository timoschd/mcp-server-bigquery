"""
BigQuery MCP Server

This module implements a Model Context Protocol (MCP) server that provides
LLMs with access to Google BigQuery databases. It supports both stdio and
HTTP/SSE transports for flexible deployment scenarios.

Key features:
- Execute SELECT queries on BigQuery datasets
- List available tables across datasets
- Retrieve table schema information
- Support for service account authentication
- Dataset filtering for security and performance
- Dual transport support (stdio for local, HTTP/SSE for cloud deployment)
"""

from google.cloud import bigquery
from google.oauth2 import service_account
import logging
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from typing import Any, Optional

# ============================================================================
# Logging Configuration
# ============================================================================
# Configure dual logging to both stdout (for container logs) and a file
# (for debugging). This ensures logs are visible in both local development
# and containerized deployments.

logger = logging.getLogger("mcp_bigquery_server")

# Handler for console output (captured by Docker/Podman)
handler_stdout = logging.StreamHandler()

# Handler for persistent file logging
handler_file = logging.FileHandler("/tmp/mcp_bigquery_server.log")

# Consistent timestamp format for both handlers
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler_stdout.setFormatter(formatter)
handler_file.setFormatter(formatter)

# Attach both handlers to the logger
logger.addHandler(handler_stdout)
logger.addHandler(handler_file)

# Set to DEBUG to capture detailed execution information
logger.setLevel(logging.DEBUG)

logger.info("Starting MCP BigQuery Server")


class BigQueryDatabase:
    """
    BigQuery Database Client Wrapper

    Provides a simplified interface for interacting with Google BigQuery,
    handling authentication, query execution, and metadata retrieval.

    This class manages the BigQuery client lifecycle and provides methods
    for common operations needed by the MCP server.
    """

    def __init__(
        self,
        project: str,
        location: str,
        key_file: Optional[str],
        datasets_filter: list[str],
    ):
        """
        Initialize a BigQuery database client.

        Args:
            project: GCP project ID containing the BigQuery datasets
            location: BigQuery location/region (e.g., 'europe-west4', 'us-central1')
            key_file: Optional path to service account JSON key file.
                     If None, uses Application Default Credentials (ADC)
            datasets_filter: List of dataset names to restrict access to.
                           If empty, all datasets in the project are accessible.

        Raises:
            ValueError: If project or location is not provided, or if key_file is invalid
        """
        logger.info(
            f"Initializing BigQuery client for project: {project}, location: {location}, key_file: {key_file}"
        )
        if not project:
            raise ValueError("Project is required")
        if not location:
            raise ValueError("Location is required")

        # Initialize credentials - either from service account key file or ADC
        credentials: service_account.Credentials | None = None
        if key_file:
            try:
                # Load service account credentials from JSON key file
                credentials_path = key_file
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
            except Exception as e:
                logger.error(f"Error loading service account credentials: {e}")
                raise ValueError(f"Invalid key file: {e}")

        # Create BigQuery client with provided or default credentials
        # If credentials is None, the client will use Application Default Credentials
        self.client = bigquery.Client(
            credentials=credentials, project=project, location=location
        )

        # Store dataset filter for restricting table access
        self.datasets_filter = datasets_filter

    def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute a SQL query and return results as a list of dictionaries.

        Args:
            query: SQL query string to execute (BigQuery SQL dialect)
            params: Optional dictionary of query parameters for parameterized queries

        Returns:
            List of dictionaries, where each dictionary represents a row with
            column names as keys and cell values as values

        Raises:
            Exception: If query execution fails (e.g., syntax error, permission denied)
        """
        logger.debug(f"Executing query: {query}")
        try:
            if params:
                # Execute parameterized query for security (prevents SQL injection)
                job = self.client.query(
                    query, job_config=bigquery.QueryJobConfig(query_parameters=params)
                )
            else:
                # Execute simple query without parameters
                job = self.client.query(query)

            # Wait for query to complete and fetch results
            results = job.result()

            # Convert BigQuery Row objects to standard Python dictionaries
            rows = [dict(row.items()) for row in results]
            logger.debug(f"Query returned {len(rows)} rows")
            return rows
        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            raise

    def list_tables(self) -> list[str]:
        """
        List all tables accessible in the BigQuery project.

        If datasets_filter is configured, only tables from those datasets are returned.
        Otherwise, all tables from all datasets in the project are listed.

        Returns:
            List of fully-qualified table names in format 'dataset_id.table_id'

        Note:
            This method may be slow for projects with many datasets/tables.
            Consider using datasets_filter to improve performance.
        """
        logger.debug("Listing all tables")

        # Determine which datasets to scan based on filter configuration
        if self.datasets_filter:
            # Use only the specified datasets
            datasets = [
                self.client.dataset(dataset) for dataset in self.datasets_filter
            ]
        else:
            # Scan all datasets in the project
            datasets = list(self.client.list_datasets())

        logger.debug(f"Found {len(datasets)} datasets")

        # Collect all tables from the selected datasets
        tables = []
        for dataset in datasets:
            dataset_tables = self.client.list_tables(dataset.dataset_id)
            # Format as fully-qualified table names
            tables.extend(
                [f"{dataset.dataset_id}.{table.table_id}" for table in dataset_tables]
            )

        logger.debug(f"Found {len(tables)} tables")
        return tables

    def describe_table(self, table_name: str) -> list[dict[str, Any]]:
        """
        Retrieve the schema and DDL for a specific table.

        Args:
            table_name: Fully-qualified table name in format 'dataset.table' or
                       'project.dataset.table'

        Returns:
            List containing a single dictionary with the table's DDL (Data Definition Language)
            statement, which includes the complete schema definition

        Raises:
            ValueError: If table_name format is invalid

        Note:
            Uses INFORMATION_SCHEMA.TABLES to retrieve metadata, which requires
            appropriate BigQuery permissions.
        """
        logger.debug(f"Describing table: {table_name}")

        # Parse the table name to extract dataset and table components
        parts = table_name.split(".")
        if len(parts) != 2 and len(parts) != 3:
            raise ValueError(f"Invalid table name: {table_name}")

        # Handle both 'dataset.table' and 'project.dataset.table' formats
        dataset_id = ".".join(parts[:-1])
        table_id = parts[-1]

        # Query INFORMATION_SCHEMA for table DDL
        # Using parameterized query for security
        query = f"""
            SELECT ddl
            FROM {dataset_id}.INFORMATION_SCHEMA.TABLES
            WHERE table_name = @table_name;
        """
        return self.execute_query(
            query,
            params=[
                bigquery.ScalarQueryParameter("table_name", "STRING", table_id),
            ],
        )


async def main(
    project: str,
    location: str,
    key_file: Optional[str],
    datasets_filter: list[str],
    transport: str = "stdio",
    port: int = 8080,
):
    """
    Main entry point for the BigQuery MCP Server.

    Initializes the BigQuery client, registers MCP tools, and starts the server
    with the specified transport mechanism.

    Args:
        project: GCP project ID
        location: BigQuery location/region
        key_file: Optional path to service account key file
        datasets_filter: List of datasets to restrict access to
        transport: Transport type - 'stdio' for local/CLI use, 'http'/'sse' for cloud deployment
        port: Port number for HTTP/SSE transport (ignored for stdio)

    Transport modes:
        - stdio: Standard input/output, used for local MCP client connections
        - http/sse: Server-Sent Events over HTTP, used for cloud deployments (e.g., Cloud Run)
    """
    logger.info(
        f"Starting BigQuery MCP Server with project: {project} and location: {location}"
    )
    logger.info(f"Using transport: {transport}")

    # Initialize BigQuery database client
    db = BigQueryDatabase(project, location, key_file, datasets_filter)

    # Create MCP server instance
    server = Server("bigquery-manager")

    # ========================================================================
    # Register MCP Tool Handlers
    # ========================================================================
    logger.debug("Registering handlers")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Handler for listing available MCP tools.

        Returns the catalog of tools that LLMs can invoke to interact with BigQuery.
        Each tool includes its name, description, and input schema for validation.
        """
        return [
            types.Tool(
                name="execute-query",
                description="Execute a SELECT query on the BigQuery database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SELECT SQL query to execute using BigQuery dialect",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="list-tables",
                description="List all tables in the BigQuery database",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="describe-table",
                description="Get the schema information for a specific table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to describe (e.g. my_dataset.my_table)",
                        },
                    },
                    "required": ["table_name"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Handler for executing MCP tool calls.

        Routes tool invocations to the appropriate BigQuery operations and
        returns results in MCP-compatible format.

        Args:
            name: Name of the tool to execute
            arguments: Dictionary of arguments for the tool

        Returns:
            List of MCP content objects (typically TextContent with results)

        Note:
            All exceptions are caught and returned as error messages to prevent
            server crashes from malformed queries or permission issues.
        """
        logger.debug(f"Handling tool execution request: {name}")

        try:
            # Route to appropriate handler based on tool name
            if name == "list-tables":
                results = db.list_tables()
                return [types.TextContent(type="text", text=str(results))]

            elif name == "describe-table":
                if not arguments or "table_name" not in arguments:
                    raise ValueError("Missing table_name argument")
                results = db.describe_table(arguments["table_name"])
                return [types.TextContent(type="text", text=str(results))]

            elif name == "execute-query":
                if not arguments or "query" not in arguments:
                    raise ValueError("Missing query argument")
                results = db.execute_query(arguments["query"])
                return [types.TextContent(type="text", text=str(results))]

            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            # Return errors as text content rather than raising exceptions
            # This prevents the MCP server from crashing on invalid requests
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # ========================================================================
    # Transport Layer Setup
    # ========================================================================

    if transport == "http" or transport == "sse":
        # HTTP/SSE transport for cloud deployments (e.g., Google Cloud Run, Kubernetes)
        # This mode exposes the MCP server over HTTP using Server-Sent Events
        logger.info(f"Starting HTTP server on port {port}")

        from starlette.routing import Route

        # Initialize SSE transport for bidirectional MCP communication over HTTP
        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            """
            Handle SSE connections for MCP communication.

            Establishes a persistent connection for the MCP client to receive
            server-sent events (tool results, notifications, etc.).
            """
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await server.run(
                    streams[0],
                    streams[1],
                    InitializationOptions(
                        server_name="bigquery",
                        server_version="0.3.0",
                        capabilities=server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )

        async def handle_post(request):
            """
            Handle POST requests from MCP clients.

            Receives tool invocation requests and other client messages.
            Returns 202 Accepted to indicate the message was queued for processing.
            """
            from starlette.responses import Response

            await sse.handle_post_message(request.scope, request.receive, request._send)
            return Response(status_code=202)

        async def handle_health(request):
            """
            Health check endpoint for container orchestration.

            Used by Cloud Run, Kubernetes, and load balancers to verify
            the service is running and ready to accept requests.
            """
            from starlette.responses import JSONResponse

            return JSONResponse({"status": "healthy", "service": "bigquery-mcp-server"})

        # Create Starlette ASGI application with route definitions
        app = Starlette(
            routes=[
                Route("/", endpoint=handle_health),  # Root health check
                Route("/health", endpoint=handle_health),  # Standard health endpoint
                Route("/messages", endpoint=handle_sse),  # SSE connection endpoint
                Route(
                    "/messages", endpoint=handle_post, methods=["POST"]
                ),  # Message POST endpoint
            ]
        )

        import uvicorn

        # Start the HTTP server using uvicorn ASGI server
        logger.info(f"Server ready on http://0.0.0.0:{port}")
        await uvicorn.Server(
            uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        ).serve()
    else:
        # ====================================================================
        # stdio Transport (Local/CLI Mode)
        # ====================================================================
        # Standard input/output transport for local MCP client connections
        # This is the default mode for desktop applications and CLI tools
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("Server running with stdio transport")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="bigquery",
                    server_version="0.3.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

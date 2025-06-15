# Use official Python image
FROM python:3.12-slim as base

# Set working directory
WORKDIR /app

# Install Poetry
RUN pip install --upgrade pip \
    && pip install poetry

# Copy pyproject.toml and poetry.lock for dependency installation
COPY pyproject.toml poetry.lock ./



# Add the rest of the project source code
ADD src /app/src
RUN touch ./README.md

# If you need to install the project as a package, uncomment the following:
RUN poetry install --no-interaction --no-ansi --only main


WORKDIR /app/src

# Define the entry point
ENTRYPOINT ["poetry", "run", "mcp-server-bigquery"]

# Example command
# CMD ["--project", "your-gcp-project-id", "--location", "your-gcp-location"]

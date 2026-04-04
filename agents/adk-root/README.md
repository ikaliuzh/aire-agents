# ADK Root Agent

A Google ADK-based agent with Agent-to-Agent (A2A) capabilities for database schema management and intelligent delegation to the DBA agent.

## Overview

The ADK Root Agent serves as a high-level orchestrator for database operations, demonstrating **pure A2A (Agent-to-Agent) architecture**:

1. **Database Schema Management**: Creates new databases with predefined schemas by delegating to the DBA agent
2. **A2A Delegation**: ALL database operations are delegated to the specialized DBA agent via A2A protocol
3. **No Direct Database Access**: The agent has no direct PostgreSQL access - it's a pure orchestrator

This architecture demonstrates clean separation of concerns:
- **ADK Root Agent**: Orchestration, schema templates, high-level workflows
- **DBA Agent**: Database execution, expertise, direct MCP access

## Architecture

```
┌─────────────────────┐
│   ADK Root Agent    │
│   (Google ADK)      │
│                     │
│   - FastAPI/Uvicorn │
│   - A2A Protocol    │
│   - Port 8080       │
│   - NO DB Access    │ ← Pure orchestrator
└──────────┬──────────┘
           │
           │ ALL operations via A2A
           │
           ▼
┌─────────────────────┐
│  DBA Agent          │
│  (Kagent)           │
│                     │
│  A2A Skills:        │
│  - Queries          │
│  - Schema Creation  │
│  - Analysis         │
│  - Optimization     │
│  - Maintenance      │
│         │           │
│         ▼           │
│  PostgreSQL MCP     │
└─────────────────────┘
```

## Features

- **Pure A2A Architecture**: ALL database operations via Agent-to-Agent protocol
- **Schema Templates**: Predefined SQL schemas for common use cases
- **No Direct Database Access**: Delegates everything to DBA agent for clean separation
- **Production Ready**: Includes health checks, logging, and error handling
- **Kubernetes Native**: Designed for deployment in Kubernetes clusters
- **Simplified Dependencies**: No MCP or database drivers needed

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DBA_AGENT_URL` | URL of the Kagent DBA agent | `http://dba-agent.kagent.svc.cluster.local:8080` |
| `GOOGLE_API_KEY` | Google API key for Gemini | Required |
| `SCHEMA_FILE` | Path to SQL schema file | `/app/schema.sql` |
| `PORT` | HTTP server port | `8080` |

**Note**: No `DATABASE_URI` needed - all database access is via DBA agent delegation.

### DBA Agent Skills

The agent can delegate to these DBA agent A2A skills:

- `database-queries`: Execute SQL queries and retrieve data
- `schema-inspection`: Inspect database schemas and structures  
- `performance-optimization`: Analyze and optimize query performance
- `database-maintenance`: Perform VACUUM and ANALYZE operations
- `data-analysis`: Analyze data patterns and generate insights

## Usage

### Running Locally

**Prerequisites**: [Poetry](https://python-poetry.org/docs/#installation) 2.0+

```bash
# Install dependencies with Poetry
task agent:install
# Or: poetry install

# Set environment variables
export GOOGLE_API_KEY="your-api-key"
export DBA_AGENT_URL="http://localhost:8081"  # Or your DBA agent URL

# Run the agent
task agent:run
# Or: poetry run python agent.py

# Or activate the virtual environment
poetry shell
python agent.py
```

### Building Docker Image

```bash
# Generate lock file (if not present)
task agent:lock

# Build the image (uses Poetry)
task agent:build

# Push to Docker Hub
task agent:push VERSION=v1.0.0

# Legacy aliases also work
task build-adk-agent
task push-adk-agent VERSION=v1.0.0
```

### Deploying to Kubernetes

The agent is deployed via Helm chart (see `chart/templates/agent-adk-root.yaml`).

Enable in `values.yaml`:

```yaml
agents:
  adkRoot:
    enabled: true
    name: adk-root-agent
    namespace: kagent
```

Then deploy with:

```bash
task up
```

## Testing

```bash
# Install all dependencies (including dev/test)
task agent:install

# Run tests
task agent:test

# Run with coverage (configured in pyproject.toml)
task agent:test-cov

# Run all checks (lint + type-check + test)
task agent:check-all

# Individual checks
task agent:lint        # Linting only
task agent:type-check  # Type checking only
task agent:format      # Auto-format code

# Legacy aliases
task test-adk-agent    # → agent:test
task lint-adk-agent    # → agent:lint + agent:type-check
```

## Development

### Project Structure

```
agents/adk-root/
├── agent.py              # Main agent implementation
├── pyproject.toml        # Poetry configuration & dependencies
├── poetry.lock           # Locked dependency versions
├── schema.sql            # Predefined database schema
├── Dockerfile            # Multi-stage container build with Poetry
├── tests/
│   └── test_agent.py     # Unit tests
├── ARCHITECTURE.md       # Architecture documentation
└── README.md
```

### Adding New Schemas

1. Create a new `.sql` file in the agent directory
2. Set `SCHEMA_FILE` environment variable to point to your schema
3. The agent will use the specified schema for database creation

### Extending A2A Capabilities

To add new skills or modify A2A behavior, edit `agent.py`:

```python
# Add new tool function
def my_new_tool(param: str) -> dict:
    """Tool description"""
    return {"result": "success"}

# Add to agent tools
root_agent = Agent(
    name='adk-root-agent',
    tools=[
        create_database_schema,
        query_dba_agent,
        my_new_tool,  # Add here
    ]
)
```

### Available Taskfile Commands

All commands are available via `task agent:<command>`:

| Command | Description |
|---------|-------------|
| `task agent:install` | Install dependencies with Poetry |
| `task agent:test` | Run unit tests |
| `task agent:test-cov` | Run tests with coverage report |
| `task agent:lint` | Run code linting (ruff) |
| `task agent:format` | Auto-format code (ruff) |
| `task agent:type-check` | Run type checking (mypy) |
| `task agent:check-all` | Run all checks (lint + type + test) |
| `task agent:build` | Build Docker image |
| `task agent:push` | Push Docker image to registry |
| `task agent:run` | Run agent locally |
| `task agent:clean` | Remove generated files |
| `task agent:update` | Update dependencies |
| `task agent:lock` | Regenerate poetry.lock |

## API Endpoints

The agent exposes A2A-compliant REST API endpoints:

- `POST /invoke` - Invoke the agent with a prompt
- `GET /health` - Health check endpoint
- `GET /capabilities` - List agent capabilities (A2A)

## Monitoring

The agent includes:

- **Structured Logging**: JSON-formatted logs for observability
- **Health Checks**: HTTP endpoint for liveness/readiness probes
- **OpenTelemetry**: Ready for distributed tracing integration

## Troubleshooting

### Connection Issues with DBA Agent

Check that the DBA agent is accessible:

```bash
kubectl get svc -n kagent dba-agent
```

### Database Connection Errors

Verify DATABASE_URI is correct:

```bash
kubectl logs -n kagent deployment/adk-root-agent
```

### A2A Protocol Issues

Enable debug logging:

```python
logging.basicConfig(level=logging.DEBUG)
```

## References

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [A2A Protocol Specification](https://github.com/google-a2a/A2A/)
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [Kagent Framework](https://github.com/kagent-dev/kagent)

## License

See project root LICENSE file.

# Context Forge Integration

IBM's Model Context Protocol (MCP) Gateway & Registry - Context Forge provides centralized governance, discovery, and observability for MCP servers, A2A agents, and REST/gRPC APIs.

## Overview

Context Forge acts as a federation layer for your AI infrastructure:

- **MCP Server Registry**: Centralize management of multiple MCP servers
- **A2A Protocol Support**: Native Agent-to-Agent communication
- **API Gateway**: Rate limiting, authentication, retries, reverse proxy
- **Admin UI**: Real-time management, monitoring, and configuration
- **Observability**: OpenTelemetry tracing with Phoenix, Jaeger, Zipkin support
- **Multi-tenancy**: User/team management with RBAC

## Deployment

Context Forge is deployed via ArgoCD as Wave 6, after all other components are running.

### Resources Deployed

1. **Context Forge Gateway** (2 replicas with HPA)
   - Service: `contextforge-mcp-context-forge.contextforge.svc.cluster.local:80`
   - Port: 80 (internal), 4444 (container)
   - Namespace: `contextforge`

2. **PostgreSQL** (via subchart)
   - Database: `contextforge`
   - Storage: 2Gi persistent volume

3. **Redis** (via subchart)
   - Storage: 1Gi persistent volume
   - Auth: Disabled for local development

## Access

### Admin UI

```bash
# Port-forward to access the Admin UI
kubectl port-forward -n contextforge svc/contextforge-mcp-context-forge 4444:80 --context kind-aire-lab

# Open http://localhost:4444/admin
# Login with:
#   Email: admin@aire-lab.local
#   Password: changeme123
```

### API Access

Generate a JWT token for API access:

```bash
# Get a shell in the Context Forge pod
kubectl exec -it -n contextforge deployment/contextforge-mcp-context-forge -- sh

# Generate token (10080 minutes = 1 week)
python3 -m mcpgateway.utils.create_jwt_token \
  --username admin@aire-lab.local \
  --exp 10080 \
  --secret my-test-key-but-now-longer-than-32-bytes-for-aire-lab

# Export token
export CONTEXTFORGE_TOKEN="<your-token>"
```

### Test API

```bash
# Health check
curl -H "Authorization: Bearer $CONTEXTFORGE_TOKEN" \
  http://localhost:4444/health | jq

# Version
curl -H "Authorization: Bearer $CONTEXTFORGE_TOKEN" \
  http://localhost:4444/version | jq

# List tools
curl -H "Authorization: Bearer $CONTEXTFORGE_TOKEN" \
  http://localhost:4444/tools | jq

# List servers
curl -H "Authorization: Bearer $CONTEXTFORGE_TOKEN" \
  http://localhost:4444/servers | jq
```

## Integration with Existing Components

### Register PostgreSQL MCP Server

```bash
# Register the existing postgres-mcp-server from kagent namespace
curl -X POST http://localhost:4444/gateways \
  -H "Authorization: Bearer $CONTEXTFORGE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "postgres_mcp",
    "url": "http://postgres-mcp-server.kagent.svc.cluster.local:80/mcp",
    "description": "PostgreSQL MCP server for AIRE database"
  }'
```

### Register ADK Root Agent

```bash
# Register the ADK Root Agent for A2A communication
curl -X POST http://localhost:4444/agents \
  -H "Authorization: Bearer $CONTEXTFORGE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "adk_root_agent",
    "url": "http://adk-root-agent.aire-lab.svc.cluster.local:8080",
    "description": "Google ADK Root Agent with A2A capabilities"
  }'
```

### Create Virtual Server

Bundle tools from registered MCP servers into a virtual server:

```bash
# First, get tool IDs
curl -H "Authorization: Bearer $CONTEXTFORGE_TOKEN" \
  http://localhost:4444/tools | jq '.[] | {id, name}'

# Create virtual server with selected tools
curl -X POST http://localhost:4444/servers \
  -H "Authorization: Bearer $CONTEXTFORGE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server": {
      "name": "aire_tools",
      "description": "AIRE Lab combined tools",
      "associated_tools": ["<tool-id-1>", "<tool-id-2>"]
    }
  }'
```

## Configuration

### Security Settings

**IMPORTANT**: Change these values before production use:

- `JWT_SECRET_KEY`: Used for signing JWT tokens (32+ chars)
- `AUTH_ENCRYPTION_SECRET`: Used for encrypting stored credentials
- `PLATFORM_ADMIN_PASSWORD`: Admin user password
- PostgreSQL password
- Redis auth (if enabled)

### SSRF Protection

Context Forge includes SSRF protection to prevent Server-Side Request Forgery attacks. For the AIRE Lab (local Kind cluster), we've configured:

- `SSRF_PROTECTION_ENABLED: "true"` - Protection is active
- `SSRF_ALLOW_PRIVATE_NETWORKS: "true"` - Allow in-cluster communication
- `SSRF_ALLOWED_NETWORKS: '["10.96.0.0/12"]'` - Kind's default service CIDR

This allows Context Forge to communicate with in-cluster MCP servers while still protecting against external SSRF attacks.

### Resource Limits

Default resource allocation per replica:

```yaml
requests:
  cpu: 200m
  memory: 512Mi
limits:
  cpu: 1
  memory: 1Gi
```

HPA scales between 2-5 replicas based on CPU/memory utilization (80% threshold).

## Use Cases

### 1. Unified MCP Server Management

Instead of each agent connecting directly to MCP servers, they connect to Context Forge, which:
- Routes requests to appropriate MCP servers
- Provides authentication and authorization
- Caches responses for better performance
- Tracks usage and provides observability

### 2. Multi-Agent Coordination

Context Forge can coordinate between multiple agents (DBA Agent, ADK Root Agent, etc.) through:
- A2A protocol support
- Shared tool registry
- Centralized state management

### 3. Tool Composition

Create virtual servers that combine tools from multiple MCP servers:
- Database tools + Kubernetes tools
- Monitoring tools + deployment tools
- Custom tool bundles per use case

### 4. API Gateway for AI Services

Use Context Forge as a gateway for external AI services:
- Rate limiting per user/team
- Request/response transformation
- Retry logic and circuit breakers
- Audit logging

## Troubleshooting

### Pod not starting

```bash
# Check pod status
kubectl get pods -n contextforge

# Check logs
kubectl logs -n contextforge -l app.kubernetes.io/name=mcp-context-forge

# Check events
kubectl get events -n contextforge --sort-by='.lastTimestamp'
```

### Database connection issues

```bash
# Check PostgreSQL pod
kubectl get pods -n contextforge -l app.kubernetes.io/name=postgresql

# Check PostgreSQL logs
kubectl logs -n contextforge -l app.kubernetes.io/name=postgresql

# Test connection from Context Forge pod
kubectl exec -it -n contextforge deployment/contextforge-mcp-context-forge -- \
  psql postgresql://contextforge:contextforge-pass-change-me@contextforge-postgresql:5432/contextforge
```

### Redis connection issues

```bash
# Check Redis pod
kubectl get pods -n contextforge -l app.kubernetes.io/name=redis

# Check Redis logs
kubectl logs -n contextforge -l app.kubernetes.io/name=redis-master

# Test connection from Context Forge pod
kubectl exec -it -n contextforge deployment/contextforge-mcp-context-forge -- \
  redis-cli -h contextforge-redis-master ping
```

## Documentation

- **Official Docs**: https://ibm.github.io/mcp-context-forge/
- **GitHub**: https://github.com/IBM/mcp-context-forge
- **API Reference**: http://localhost:4444/docs (when port-forwarded)
- **ReDoc**: http://localhost:4444/redoc (when port-forwarded)

## Next Steps

1. **Access the Admin UI** and explore the interface
2. **Register existing MCP servers** (postgres-mcp-server)
3. **Create virtual servers** with custom tool combinations
4. **Configure agents** to use Context Forge as their MCP gateway
5. **Set up observability** with OpenTelemetry backend
6. **Explore A2A integration** with ADK Root Agent

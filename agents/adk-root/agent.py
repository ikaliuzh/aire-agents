"""
ADK Root Agent - Database Schema Manager with A2A Integration

This agent is responsible for:
1. Spinning up databases with predefined schemas by delegating to DBA agent
2. Querying the DBA agent for insights via A2A protocol

All database operations are delegated to the DBA agent via A2A communication.
All AI requests route through AgentGateway proxy (not direct to Gemini).
"""

import os
import logging
from typing import Any

from google.adk import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
DBA_AGENT_URL = os.getenv('DBA_AGENT_URL', 'http://dba-agent.kagent.svc.cluster.local:8080')
AGENTGATEWAY_URL = os.getenv('AGENTGATEWAY_URL', 'http://agentgateway-proxy.agentgateway-system.svc.cluster.local:80/gemini')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
SCHEMA_FILE = os.getenv('SCHEMA_FILE', '/app/schema.sql')

# Configure OpenAI client to use AgentGateway
# AgentGateway provides an OpenAI-compatible API for Gemini
# No API key needed - AgentGateway handles authentication
openai_client = OpenAI(
    base_url=AGENTGATEWAY_URL,
    api_key='not-needed'  # AgentGateway handles real auth
)

logger.info(f"Using AgentGateway at: {AGENTGATEWAY_URL}")
logger.info(f"Model: {GEMINI_MODEL}")

# Create remote DBA agent using proper A2A protocol
# RemoteA2aAgent automatically handles agent card discovery, streaming, and A2A protocol
dba_agent = RemoteA2aAgent(
    name="dba_agent",
    description="""AI Database Administrator specializing in PostgreSQL operations.

    This agent can:
    - Create databases and execute schema definitions
    - Execute SQL queries and retrieve data
    - Analyze query performance and optimize queries
    - Inspect table structures and indexes
    - Perform database maintenance (VACUUM, ANALYZE)
    - Analyze data patterns and generate insights
    """,
    agent_card=f"{DBA_AGENT_URL}/{AGENT_CARD_WELL_KNOWN_PATH}",
)

logger.info(f"DBA agent configured with card at: {DBA_AGENT_URL}/{AGENT_CARD_WELL_KNOWN_PATH}")


async def create_database_schema(database_name: str = "testdb", schema_file: str = SCHEMA_FILE) -> dict[str, Any]:
    """
    Create a new database with a predefined schema by delegating to the DBA agent.

    Args:
        database_name: Name of the database to create
        schema_file: Path to SQL file with schema definition

    Returns:
        Dictionary with status and details
    """
    try:
        logger.info(f"Creating database: {database_name}")

        # Read schema from file
        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        # Create combined prompt for DBA agent via A2A
        # The DBA agent will handle both database creation and schema execution
        combined_prompt = f"""
        Please perform the following database operations:

        1. Create a new database called '{database_name}'
        2. Execute the following SQL schema in that database:

        {schema_sql}

        Confirm when complete and report any issues.
        """

        logger.info(f"Delegating database creation to DBA agent via A2A...")

        # Note: The actual invocation of dba_agent is handled by the LLM
        # when it's added as a sub_agent to the root agent.
        # This function provides the schema context.

        return {
            "status": "success",
            "database": database_name,
            "message": f"Database {database_name} schema prepared. Use dba_agent to execute.",
            "schema_size": len(schema_sql),
            "schema_sql": schema_sql,
            "instruction": "Delegate to dba_agent to create the database and execute this schema."
        }

    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return {
            "status": "error",
            "database": database_name,
            "error": str(e)
        }


# Define the root agent with DBA agent as sub_agent
root_agent = Agent(
    name='adk-root-agent',
    model=GEMINI_MODEL,
    client=openai_client,  # Use AgentGateway instead of direct Gemini
    instruction="""
    You are the ADK Root Agent, a database schema manager that orchestrates database
    operations by delegating ALL database tasks to a specialized DBA agent via A2A
    (Agent-to-Agent) communication.

    Your primary responsibilities are:

    1. **Database Schema Management**: Create new databases with predefined schemas by
       delegating to the DBA agent. You have access to predefined schema templates via
       the `create_database_schema` function.

    2. **DBA Agent Delegation**: For ALL database operations, analysis, or optimization
       tasks, transfer the conversation to the `dba_agent` sub-agent.

    ## Architecture

    You do NOT have direct database access. ALL database operations are performed by
    delegating to the `dba_agent` sub-agent via proper A2A protocol. The DBA agent has
    PostgreSQL MCP tools and database expertise.

    ## Available Sub-Agent

    - `dba_agent`: AI Database Administrator specializing in PostgreSQL
      - Can create databases and execute schemas
      - Can run SQL queries and analyze data
      - Can optimize performance and inspect structures
      - Can perform maintenance and generate insights

    ## Workflow

    When a user requests database operations:

    1. **For predefined schemas**:
       - Use `create_database_schema` to prepare the schema
       - Then transfer to `dba_agent` to execute it

    2. **For ad-hoc database operations**:
       - Transfer directly to `dba_agent`

    3. **For analysis after creation**:
       - Create database via `dba_agent`
       - Then ask `dba_agent` to analyze it

    ## Best Practices

    - Always confirm database names before creation
    - Transfer to dba_agent for all database execution
    - Provide clear context when transferring
    - Summarize DBA agent responses for the user
    - Handle errors gracefully and suggest alternatives

    Remember: You orchestrate, the dba_agent executes via A2A protocol.
    """,
    tools=[
        create_database_schema,
    ],
    sub_agents=[
        dba_agent,  # Remote A2A agent (proper ADK pattern)
    ]
)

# Convert to A2A-compliant FastAPI application
a2a_app = to_a2a(root_agent)

logger.info("ADK Root Agent initialized and ready to serve on port 8080")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host="0.0.0.0", port=8080)

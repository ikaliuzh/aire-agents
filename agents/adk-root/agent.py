"""
ADK Root Agent - Database Schema Manager with A2A Integration

This agent is responsible for:
1. Spinning up databases with predefined schemas by delegating to DBA agent
2. Querying the DBA agent for insights via A2A protocol

All database operations are delegated to the DBA agent via A2A communication.
"""

import os
import logging
from typing import Any

import httpx
from google.adk import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
DBA_AGENT_URL = os.getenv('DBA_AGENT_URL', 'http://dba-agent.kagent.svc.cluster.local:8080')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
SCHEMA_FILE = os.getenv('SCHEMA_FILE', '/app/schema.sql')


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

        # Step 1: Create the database via DBA agent
        create_db_prompt = f"Create a new database called '{database_name}'"
        create_result = await query_dba_agent("database-queries", create_db_prompt)

        if create_result["status"] != "success":
            logger.error(f"Failed to create database: {create_result.get('error')}")
            return {
                "status": "error",
                "database": database_name,
                "error": f"Database creation failed: {create_result.get('error')}"
            }

        # Step 2: Execute schema SQL via DBA agent
        schema_prompt = f"""
        Connect to database '{database_name}' and execute the following SQL schema:

        {schema_sql}
        """
        schema_result = await query_dba_agent("database-queries", schema_prompt)

        if schema_result["status"] != "success":
            logger.error(f"Failed to create schema: {schema_result.get('error')}")
            return {
                "status": "error",
                "database": database_name,
                "error": f"Schema creation failed: {schema_result.get('error')}"
            }

        result = {
            "status": "success",
            "database": database_name,
            "message": f"Database {database_name} created with predefined schema via DBA agent",
            "schema_size": len(schema_sql),
            "dba_response": schema_result["response"]
        }

        logger.info(f"Database created successfully: {database_name}")
        return result

    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return {
            "status": "error",
            "database": database_name,
            "error": str(e)
        }


async def query_dba_agent(skill_id: str, prompt: str) -> dict[str, Any]:
    """
    Query the DBA agent via A2A protocol for database insights.

    Args:
        skill_id: The DBA agent skill to invoke (e.g., 'database-queries', 'data-analysis')
        prompt: The query or request to send to the DBA agent

    Returns:
        Dictionary with the DBA agent's response
    """
    try:
        logger.info(f"Querying DBA agent with skill: {skill_id}")

        # Construct A2A request to Kagent DBA agent
        # Note: This is a simplified A2A call. Actual implementation may vary based on Kagent's API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{DBA_AGENT_URL}/invoke",
                json={
                    "skill": skill_id,
                    "prompt": prompt,
                    "context": {}
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"DBA agent responded successfully")
                return {
                    "status": "success",
                    "skill": skill_id,
                    "response": result
                }
            else:
                logger.error(f"DBA agent returned error: {response.status_code}")
                return {
                    "status": "error",
                    "skill": skill_id,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

    except Exception as e:
        logger.error(f"Failed to query DBA agent: {e}")
        return {
            "status": "error",
            "skill": skill_id,
            "error": str(e)
        }


# Define the root agent
root_agent = Agent(
    name='adk-root-agent',
    model='gemini-2.5-flash',
    instruction="""
    You are the ADK Root Agent, a database schema manager that orchestrates database
    operations by delegating ALL database tasks to a specialized DBA agent via A2A
    (Agent-to-Agent) communication.

    Your primary responsibilities are:

    1. **Database Schema Management**: Create new databases with predefined schemas by
       delegating to the DBA agent. You have access to predefined schema templates.

    2. **DBA Agent Delegation**: For ALL database operations, analysis, or optimization
       tasks, delegate to the DBA agent using A2A communication.

    ## Architecture

    You do NOT have direct database access. ALL database operations are performed by
    delegating to the DBA agent, which has PostgreSQL MCP tools and expertise.

    ## Available DBA Agent Skills

    You can query the DBA agent using these skills:
    - `database-queries`: Execute SQL queries, create databases, create schemas, retrieve data
    - `schema-inspection`: Inspect database schemas and structures
    - `performance-optimization`: Analyze and optimize query performance
    - `database-maintenance`: Perform VACUUM and ANALYZE operations
    - `data-analysis`: Analyze data patterns and generate insights

    ## Workflow

    When a user requests database operations:
    1. To create a database with predefined schema: use create_database_schema
       - This reads the schema file and delegates creation to DBA agent
    2. For querying, analysis, or optimization: use query_dba_agent directly
    3. Combine both capabilities when needed (e.g., create DB then analyze it)

    ## Best Practices

    - Always confirm database names before creation
    - Provide clear, detailed prompts when delegating to the DBA agent
    - Summarize DBA agent responses for the user
    - Handle errors gracefully and suggest alternatives
    - Remember: You orchestrate, the DBA agent executes

    Be helpful, efficient, and collaborative with the DBA agent.
    """,
    tools=[
        create_database_schema,
        query_dba_agent,
    ]
)

# Convert to A2A-compliant FastAPI application
a2a_app = to_a2a(root_agent, port=8080)

logger.info("ADK Root Agent initialized and ready to serve on port 8080")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host="0.0.0.0", port=8080)

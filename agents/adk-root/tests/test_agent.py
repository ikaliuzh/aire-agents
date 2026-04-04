"""
Unit tests for ADK Root Agent
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent import create_database_schema, query_dba_agent


class TestDatabaseSchema:
    """Tests for database schema creation via DBA agent delegation"""

    @pytest.mark.asyncio
    async def test_create_database_schema_success(self, tmp_path):
        """Test successful database schema creation via DBA agent"""
        # Create a temporary schema file
        schema_file = tmp_path / "test_schema.sql"
        schema_file.write_text("CREATE TABLE test (id INT);")

        # Mock successful DBA agent responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": "Success",
            "message": "Database created"
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await create_database_schema(
                database_name="testdb",
                schema_file=str(schema_file)
            )

            assert result["status"] == "success"
            assert result["database"] == "testdb"
            assert "created" in result["message"].lower()
            assert result["schema_size"] > 0
            assert "dba_response" in result

    @pytest.mark.asyncio
    async def test_create_database_schema_file_not_found(self):
        """Test schema creation with non-existent file"""
        result = await create_database_schema(
            database_name="testdb",
            schema_file="/nonexistent/schema.sql"
        )

        assert result["status"] == "error"
        assert "error" in result
        assert "testdb" == result["database"]

    @pytest.mark.asyncio
    async def test_create_database_schema_dba_agent_error(self, tmp_path):
        """Test schema creation when DBA agent fails"""
        schema_file = tmp_path / "test_schema.sql"
        schema_file.write_text("CREATE TABLE test (id INT);")

        # Mock DBA agent error on database creation
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Database error"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await create_database_schema(
                database_name="testdb",
                schema_file=str(schema_file)
            )

            assert result["status"] == "error"
            assert "Database creation failed" in result["error"]


class TestDBAAgentQuery:
    """Tests for DBA agent A2A communication"""

    @pytest.mark.asyncio
    async def test_query_dba_agent_success(self):
        """Test successful A2A query to DBA agent"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": "Query executed successfully",
            "data": [{"count": 10}]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await query_dba_agent(
                skill_id="database-queries",
                prompt="Count all events"
            )

            assert result["status"] == "success"
            assert result["skill"] == "database-queries"
            assert "response" in result
            assert result["response"]["result"] == "Query executed successfully"

    @pytest.mark.asyncio
    async def test_query_dba_agent_http_error(self):
        """Test A2A query with HTTP error response"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await query_dba_agent(
                skill_id="database-queries",
                prompt="Invalid query"
            )

            assert result["status"] == "error"
            assert "HTTP 500" in result["error"]

    @pytest.mark.asyncio
    async def test_query_dba_agent_connection_error(self):
        """Test A2A query with connection failure"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            result = await query_dba_agent(
                skill_id="database-queries",
                prompt="Test query"
            )

            assert result["status"] == "error"
            assert "Connection refused" in result["error"]

    @pytest.mark.asyncio
    async def test_query_dba_agent_all_skills(self):
        """Test querying different DBA agent skills"""
        skills = [
            "database-queries",
            "schema-inspection",
            "performance-optimization",
            "database-maintenance",
            "data-analysis"
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "Success"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            for skill in skills:
                result = await query_dba_agent(skill_id=skill, prompt="Test")
                assert result["status"] == "success"
                assert result["skill"] == skill


class TestAgentIntegration:
    """Integration tests for the agent"""

    def test_agent_configuration(self):
        """Test that agent is properly configured"""
        from agent import root_agent

        assert root_agent.name == 'adk-root-agent'
        assert root_agent.model == 'gemini-2.5-flash'
        assert len(root_agent.tools) == 2  # Only 2 tools now (no MCP)

        # Verify both tools are present
        tool_functions = [tool for tool in root_agent.tools if callable(tool)]
        assert len(tool_functions) == 2

    def test_a2a_app_creation(self):
        """Test that A2A app is properly created"""
        from agent import a2a_app

        assert a2a_app is not None
        # FastAPI app should have routes
        assert hasattr(a2a_app, 'routes') or hasattr(a2a_app, 'router')

    def test_agent_instruction_mentions_delegation(self):
        """Test that agent instruction emphasizes delegation"""
        from agent import root_agent

        instruction = root_agent.instruction.lower()
        assert "dba agent" in instruction
        assert "delegate" in instruction or "delegating" in instruction
        assert "a2a" in instruction


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for newly spawned agents: VeronicaAgent (Research) and ForgeAgent (Code Architect).
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))

from friday.base_agent import AgentDef, AgentTask
from friday.research_agent import VeronicaAgent
from friday.code_agent import ForgeAgent


class TestVeronicaAgent(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.defn = AgentDef(
            id="research_agent",
            name="Veronica",
            task_types=["research"],
            nim_model="meta/llama-3.1-405b-instruct",
            enabled=True
        )
        self.agent = VeronicaAgent(self.defn)

    @patch("friday.research_agent.InferenceClient")
    @patch("friday.research_agent.requests.get")
    async def test_execute_research_flow(self, mock_get, mock_client_cls):
        # Mock InferenceClient
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        self.agent._client = mock_client

        # Mock query generation
        resp_queries = MagicMock()
        resp_queries.content = "quantum computing history\nrecent quantum developments\nquantum algorithms guide"
        
        # Mock page summary
        resp_summary = MagicMock()
        resp_summary.content = "Quantum computing uses qubits instead of classical bits."

        # Mock synthesis
        resp_synthesis = MagicMock()
        resp_synthesis.content = "# Research Synthesis on Quantum Computing\n\nExecutive summary details..."

        mock_client.chat = AsyncMock()
        mock_client.chat.side_effect = [resp_queries, resp_summary, resp_summary, resp_summary, resp_synthesis]

        # Mock requests.get for crawler
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><main><p>Quantum computing uses qubits instead of classical bits. This is a very long paragraph to pass the length check.</p></main></body></html>"
        mock_get.return_value = mock_response

        # Mock search engine returning results
        self.agent._execute_search = AsyncMock(return_value=[
            {"title": "Intro to Quantum Computing", "url": "https://example.com/intro", "snippet": "A basic intro", "engine": "duckduckgo"},
            {"title": "Advanced Qubits", "url": "https://example.com/qubits", "snippet": "Detailed look at qubits", "engine": "bing"}
        ])

        task = AgentTask(
            task_id="test-task-123",
            task_type="research",
            payload="quantum computing history"
        )

        result = await self.agent.execute(task)
        self.assertEqual(result.status, "completed")
        self.assertIn("Research Synthesis on Quantum", result.output)
        self.assertEqual(result.agent_id, "research_agent")


class TestForgeAgent(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.defn = AgentDef(
            id="code_agent",
            name="Forge",
            task_types=["code_gen", "ast_analysis"],
            nim_model="nvidia/llama-3.1-nemotron-70b-instruct",
            enabled=True
        )
        self.agent = ForgeAgent(self.defn)

    @patch("friday.code_agent.InferenceClient")
    async def test_execute_ast_analysis(self, mock_client_cls):
        # Create a temp file to parse
        temp_file = "temp_test_file.py"
        code_content = (
            "import os\n"
            "from math import sqrt\n\n"
            "class MathHelper:\n"
            "    def add_numbers(self, a, b):\n"
            "        '''Adds two numbers.'''\n"
            "        return a + b\n\n"
            "def calculate_root(x):\n"
            "    if x < 0:\n"
            "        return None\n"
            "    return sqrt(x)\n"
        )
        with open(temp_file, "w") as f:
            f.write(code_content)

        try:
            task = AgentTask(
                task_id="test-task-456",
                task_type="ast_analysis",
                payload=f"Analyze code in {temp_file}"
            )
            task.context_snapshot["file_path"] = temp_file

            result = await self.agent.execute(task)
            self.assertEqual(result.status, "completed")
            self.assertIn("AST Structural Analysis", result.output)
            self.assertIn("class MathHelper", result.output)
            self.assertIn("add_numbers", result.output)
            self.assertIn("calculate_root", result.output)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    @patch("friday.code_agent.InferenceClient")
    async def test_execute_syntax_check(self, mock_client_cls):
        temp_file = "temp_syntax_test.py"
        code_content = "def invalid_syntax_here(:\n    pass\n"
        with open(temp_file, "w") as f:
            f.write(code_content)

        try:
            task = AgentTask(
                task_id="test-task-789",
                task_type="syntax_check",
                payload=f"Check syntax of {temp_file}"
            )
            task.context_snapshot["file_path"] = temp_file

            result = await self.agent.execute(task)
            self.assertEqual(result.status, "completed")
            self.assertIn("Syntax Error Detected", result.output)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


if __name__ == "__main__":
    unittest.main()

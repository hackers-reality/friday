"""
Tests for Custom FRIDAY Agents — VeronicaAgent (research_agent) and ForgeAgent (code_agent).
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from friday.base_agent import AgentDef, AgentTask, AgentResult
from friday.research_agent import VeronicaAgent
from friday.code_agent import ForgeAgent
from friday.pr_agent import AutonomousPRReviewer


class TestVeronicaAgent(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.defn = AgentDef(
            id="research_agent",
            name="Veronica",
            task_types=["research", "summarization"],
            nim_model="meta/llama-3.1-405b-instruct",
            tools=["web_search", "deep_research"],
            enabled=True
        )
        self.scraper_patcher = patch("friday.research_agent.WebScraper")
        self.client_patcher = patch("friday.research_agent.InferenceClient")
        self.mock_scraper_cls = self.scraper_patcher.start()
        self.mock_client_cls = self.client_patcher.start()

        self.mock_scraper = MagicMock()
        self.mock_scraper_cls.return_value = self.mock_scraper
        self.mock_client = MagicMock()
        self.mock_client.chat = AsyncMock()
        self.mock_client_cls.return_value = self.mock_client

        self.agent = VeronicaAgent(self.defn)

    def tearDown(self):
        self.scraper_patcher.stop()
        self.client_patcher.stop()

    def test_initialization(self):
        self.assertEqual(self.agent.id, "research_agent")
        self.assertEqual(self.agent.name, "Veronica")
        self.assertEqual(self.agent.nim_model, "meta/llama-3.1-405b-instruct")

    def test_rank_sources(self):
        results = [
            {"title": "Unrelated title", "url": "https://spam.com/ads", "snippet": "buy now", "engine": "duckduckgo"},
            {"title": "History of Machine Learning", "url": "https://wikipedia.org/wiki/ML", "snippet": "Machine learning is...", "engine": "duckduckgo"},
            {"title": "Machine Learning history and details", "url": "https://mit.edu/ml", "snippet": "Foundational history of machine learning", "engine": "bing"}
        ]
        topic = "history of machine learning"
        ranked = self.agent._rank_sources(results, topic)
        
        # The wikipedia and edu links should be ranked highest
        self.assertGreater(len(ranked), 0)
        self.assertTrue("wikipedia.org" in ranked[0]["url"] or "mit.edu" in ranked[0]["url"])
        self.assertEqual(ranked[-1]["url"], "https://spam.com/ads")

    async def test_execute_success(self):
        self.mock_client.chat.return_value = MagicMock(content="Query 1\nQuery 2\nQuery 3")
        self.mock_scraper.search_engine.return_value = {
            "success": True,
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
                {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"}
            ]
        }

        task = AgentTask(
            task_type="research",
            payload="artificial intelligence trends"
        )

        # Run execute
        with patch("friday.research_agent.get_bus"), \
             patch("friday.orchestrator.get_orchestrator"), \
             patch.object(self.agent, "_crawl_page", AsyncMock(return_value={"url": "https://example.com/1", "title": "Result 1", "text": "Content here"})), \
             patch.object(self.agent, "_summarize_page_content", AsyncMock(return_value="Summary here")), \
             patch.object(self.agent, "_synthesize_report", AsyncMock(return_value="# Synthesized Report")):
            result = await self.agent.execute(task)
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.output, "# Synthesized Report")


class TestForgeAgent(unittest.TestCase):
    def setUp(self):
        self.defn = AgentDef(
            id="code_agent",
            name="Forge",
            task_types=["code_gen", "reasoning"],
            nim_model="nvidia/llama-3.1-nemotron-70b-instruct",
            tools=["read_file", "write_file", "git_ops"],
            enabled=True
        )
        self.agent = ForgeAgent(self.defn)

    def test_initialization(self):
        self.assertEqual(self.agent.id, "code_agent")
        self.assertEqual(self.agent.name, "Forge")

    def test_classify_code_task(self):
        self.assertEqual(self.agent._classify_code_task("review the code in app.py"), "code_review")
        self.assertEqual(self.agent._classify_code_task("show me the AST structure"), "ast_analysis")
        self.assertEqual(self.agent._classify_code_task("refactor this code block"), "code_refactor")
        self.assertEqual(self.agent._classify_code_task("generate a flask server"), "code_gen")
        self.assertEqual(self.agent._classify_code_task("check syntax errors"), "syntax_check")

    def test_extract_filepath_from_payload(self):
        self.assertEqual(self.agent._extract_filepath_from_payload("analyze e:\\workspace\\main.py"), "e:\\workspace\\main.py")
        self.assertEqual(self.agent._extract_filepath_from_payload("check syntax in friday/core.py please"), "friday/core.py")
        self.assertEqual(self.agent._extract_filepath_from_payload("no file path here"), "")

    def test_ast_analysis_non_existent(self):
        res = self.agent._do_ast_analysis("non_existent_file_xyz.py")
        self.assertIn("does not exist", res)

    def test_ast_analysis_valid(self):
        # We can analyze a small temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
            f.write(
                "import os\n"
                "class TestClass:\n"
                "    def test_method(self, x):\n"
                "        return x + 1\n"
                "def global_func():\n"
                "    pass\n"
            )
            temp_path = f.name

        try:
            res = self.agent._do_ast_analysis(temp_path)
            self.assertIn("AST Structural Analysis", res)
            self.assertIn("TestClass", res)
            self.assertIn("test_method", res)
            self.assertIn("global_func", res)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_syntax_check_valid(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
            f.write("def func():\n    return 42\n")
            temp_path = f.name
        try:
            res = self.agent._do_syntax_check(temp_path)
            self.assertIn("Syntax check passed", res)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_syntax_check_invalid(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
            f.write("def func()\n    return 42\n")  # Missing colon
            temp_path = f.name
        try:
            res = self.agent._do_syntax_check(temp_path)
            self.assertIn("Syntax Error Detected", res)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestAutonomousPRReviewer(unittest.TestCase):
    def setUp(self):
        self.defn = AgentDef(
            id="pr_reviewer_agent",
            name="PRReviewer",
            task_types=["pr_review", "code_repair"],
            nim_model="nvidia/llama-3.1-nemotron-70b-instruct",
            tools=["read_file", "write_file", "git_ops"],
            enabled=True
        )
        self.agent = AutonomousPRReviewer(self.defn)

    def test_initialization(self):
        self.assertEqual(self.agent.id, "pr_reviewer_agent")
        self.assertEqual(self.agent.name, "PRReviewer")
        self.assertIsNotNone(self.agent.repo_path)

    def test_extract_json(self):
        # Test markdown wrapper cleanup
        raw_list = "```json\n[\n  {\"file\": \"test.py\", \"line\": 10}\n]\n```"
        extracted = self.agent._extract_json(raw_list)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["file"], "test.py")

        # Test object cleanup
        raw_obj = "```json\n{\n  \"file_to_edit\": \"src/main.py\"\n}\n```"
        extracted_obj = self.agent._extract_json_object(raw_obj)
        self.assertEqual(extracted_obj["file_to_edit"], "src/main.py")

    def test_parse_unified_diff(self):
        sample_diff = (
            "diff --git a/src/math_utils.py b/src/math_utils.py\n"
            "index 123456..789101 100644\n"
            "--- a/src/math_utils.py\n"
            "+++ b/src/math_utils.py\n"
            "@@ -5,4 +5,5 @@\n"
            " def add(a, b):\n"
            "-    return a - b\n"
            "+    # corrected addition logic\n"
            "+    return a + b\n"
            " \n"
        )
        parsed = self.agent._parse_unified_diff(sample_diff)
        self.assertIn("src/math_utils.py", parsed)
        hunks = parsed["src/math_utils.py"]
        self.assertEqual(len(hunks), 1)
        
        hunk = hunks[0]
        self.assertEqual(hunk["new_start"], 5)
        # Check that we parsed the + lines correctly
        added_lines = [l for l in hunk["lines"] if l[0] == '+']
        self.assertEqual(len(added_lines), 2)
        self.assertEqual(added_lines[0][1], "    # corrected addition logic")
        self.assertEqual(added_lines[0][2], 6)
        self.assertEqual(added_lines[1][2], 7)

    def test_parse_test_failures_pytest(self):
        pytest_output = (
            "=================================== FAILURES ===================================\n"
            "________________________________ test_addition _________________________________\n"
            "\n"
            "def test_addition():\n"
            ">       assert add(2, 3) == 6\n"
            "E       AssertionError: assert 5 == 6\n"
            "E         -5\n"
            "E         +6\n"
            "\n"
            "tests/test_math.py:12: AssertionError\n"
            "============================== 1 failed in 0.05s ===============================\n"
        )
        failures = self.agent._parse_test_failures(pytest_output, "")
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["test_name"], "test_addition")
        self.assertEqual(failures[0]["file"], "tests/test_math.py")
        self.assertEqual(failures[0]["line"], 12)
        self.assertIn("AssertionError", failures[0]["error"])

    def test_find_test_files_for_modified(self):
        # Create a mock environment checks or verify the heuristic logic
        modified = ["friday/pr_agent.py"]
        tests = self.agent._find_test_files_for_modified(modified)
        # It shouldn't crash and should return a list
        self.assertIsInstance(tests, list)


class TestSandboxRunner(unittest.TestCase):
    def test_resolve_pip_package(self):
        from friday.sandbox_runner import resolve_pip_package
        self.assertEqual(resolve_pip_package("yaml"), "pyyaml")
        self.assertEqual(resolve_pip_package("bs4"), "beautifulsoup4")
        self.assertEqual(resolve_pip_package("numpy"), "numpy")
        self.assertEqual(resolve_pip_package("my_custom_module"), "my-custom-module")

    def test_extract_imports(self):
        from friday.sandbox_runner import extract_imports
        # Write temporary file to extract imports
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
            f.write("import math\nfrom os import path\nimport requests.exceptions\n")
            temp_path = f.name
        try:
            imports = extract_imports(temp_path)
            self.assertIn("math", imports)
            self.assertIn("os", imports)
            self.assertIn("requests.exceptions", imports)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


import asyncio
import json
import unittest
from types import SimpleNamespace

import app.services.agent_loop as agent_loop
import app.services.junior_dev as junior_dev
import app.services.orchestrator as orchestrator


class SequenceCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        if not self.responses:
            raise AssertionError("No mock responses left for chat completion calls")
        content = self.responses.pop(0)
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class SequenceChat:
    def __init__(self, responses):
        self.completions = SequenceCompletions(responses)


class SequenceClient:
    def __init__(self, responses):
        self.chat = SequenceChat(responses)


class FeedbackLoopTests(unittest.TestCase):
    def setUp(self):
        self.original_orchestrator_client = orchestrator.client
        self.original_junior_client = junior_dev.client
        orchestrator.chat_sessions.clear()
        junior_dev.junior_sessions.clear()

    def tearDown(self):
        orchestrator.client = self.original_orchestrator_client
        junior_dev.client = self.original_junior_client
        orchestrator.chat_sessions.clear()
        junior_dev.junior_sessions.clear()

    def _single_file_plan(self, filename="Foo.tsx"):
        return {
            "global_style": {
                "color_scheme": "Test neutrals",
                "style_description": "Test description"
            },
            "files": [
                {
                    "path": "src/pages",
                    "filename": filename,
                    "functions": [{"name": filename.replace('.tsx', ''), "description": "Test component"}],
                    "dependencies": [],
                    "props": "",
                    "routes": [],
                }
            ],
        }

    def test_junior_feedback_response_is_parsed(self):
        junior_dev.client = SequenceClient(
            ['{"type":"feedback","blocking":true,"message":"Need API shape","filename":"Foo.tsx"}']
        )
        from app.schemas.plan import FilePlan, FunctionInfo
        fp = FilePlan(
            path="src",
            filename="Foo.tsx",
            functions=[FunctionInfo(name="Foo", description="Test")],
            dependencies=[],
            props="",
            routes=[],
        )

        result = asyncio.run(junior_dev.implement_component(fp, global_style=None, session_id="feedback-test"))
        self.assertEqual(result["type"], "feedback")
        self.assertTrue(result["blocking"])
        self.assertIn("Need API shape", result["message"])

    def test_feedback_loop_runs_multiple_rounds(self):
        plan1 = self._single_file_plan("RoundOne.tsx")
        plan2 = self._single_file_plan("RoundTwo.tsx")

        orchestrator.client = SequenceClient(
            [
                f"```json\n{json.dumps(plan1)}\n```",
                f"```json\n{json.dumps(plan2)}\n```",
            ]
        )

        junior_dev.client = SequenceClient(
            [
                '{"type":"feedback","blocking":true,"message":"Need design tokens","filename":"RoundOne.tsx"}',
                "```tsx\nconst RoundTwo = () => null;\nexport default RoundTwo;\n```",
            ]
        )

        loop_result = asyncio.run(agent_loop.run_orchestration_with_feedback("Build UI", max_rounds=2))
        self.assertEqual(loop_result["type"], "feedback_loop")
        self.assertGreaterEqual(len(loop_result["iterations"]), 2)
        first_feedback = loop_result["iterations"][0]["feedback"][0]
        self.assertTrue(first_feedback["blocking"])
        self.assertIn("design tokens", first_feedback["message"])
        second_impls = loop_result["iterations"][1]["implementations"]["implementations"]
        self.assertEqual(second_impls[0]["type"], "implementation")
        # If build is available, we should finish completed; otherwise a blocking build feedback may extend rounds.
        self.assertIn(loop_result["status"], ["completed", "soft_limit_reached", "max_rounds_reached"])


if __name__ == "__main__":
    unittest.main()

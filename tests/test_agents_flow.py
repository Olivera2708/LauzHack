import asyncio
import json
import unittest
from types import SimpleNamespace

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


class AgentFlowTests(unittest.TestCase):
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

    def _plan_payload(self):
        return {
            "global_style": {
                "color_scheme": "Muted neutrals with primary highlights",
                "style_description": "Dashboard look using shadcn/ui cards, buttons, and tabs",
            },
            "files": [
                {
                    "path": "src/components",
                    "filename": "Navbar.tsx",
                    "functions": [
                        {
                            "name": "Navbar",
                            "description": "Navigation bar with active states",
                        }
                    ],
                    "dependencies": [
                        {
                            "from_path": "react-router-dom",
                            "imports": [
                                {
                                    "name": "Link",
                                    "description": "Navigation link for client routing",
                                },
                                {
                                    "name": "NavLink",
                                    "description": "Active-aware navigation link",
                                },
                            ],
                        },
                        {
                            "from_path": "@/components/ui/button",
                            "imports": [
                                {
                                    "name": "Button",
                                    "description": "Styled button used as a link wrapper",
                                }
                            ],
                        },
                    ],
                    "props": "interface NavbarProps {}",
                    "routes": [
                        {"name": "/", "component": "Home"},
                        {"name": "/projects", "component": "Projects"},
                    ],
                },
                {
                    "path": "src",
                    "filename": "App.tsx",
                    "functions": [
                        {
                            "name": "App",
                            "description": "Entry point wiring BrowserRouter and page routes",
                        }
                    ],
                    "dependencies": [
                        {
                            "from_path": "react-router-dom",
                            "imports": [
                                {
                                    "name": "BrowserRouter",
                                    "description": "Router provider",
                                },
                                {"name": "Routes", "description": "Routes container"},
                                {"name": "Route", "description": "Route definition"},
                            ],
                        },
                        {
                            "from_path": "./components/Navbar",
                            "imports": [
                                {"name": "Navbar", "description": "Top navigation bar"}
                            ],
                        },
                        {
                            "from_path": "./pages/Home",
                            "imports": [
                                {"name": "Home", "description": "Landing page component"}
                            ],
                        },
                        {
                            "from_path": "./pages/Projects",
                            "imports": [
                                {
                                    "name": "Projects",
                                    "description": "Projects listing page",
                                }
                            ],
                        },
                    ],
                    "props": "",
                    "routes": [
                        {"name": "/", "component": "Home"},
                        {"name": "/projects", "component": "Projects"},
                    ],
                },
                {
                    "path": "src/pages",
                    "filename": "Home.tsx",
                    "functions": [
                        {"name": "Home", "description": "Home page hero and CTA"}
                    ],
                    "dependencies": [],
                    "props": "",
                    "routes": [],
                },
            ],
        }

    def test_orchestrator_parses_plan_with_routes(self):
        plan_payload = self._plan_payload()
        orchestrator.client = SequenceClient(
            [f"```json\n{json.dumps(plan_payload)}\n```"]
        )

        result = asyncio.run(
            orchestrator.process_chat("Plan a dashboard", session_id="orch-test")
        )
        self.assertEqual(result["type"], "plan")
        plan = result["content"]
        self.assertEqual(len(plan.files), 3)
        navbar_plan = next(fp for fp in plan.files if fp.filename == "Navbar.tsx")
        self.assertEqual(len(navbar_plan.routes), 2)
        self.assertEqual(navbar_plan.routes[0].name, "/")

    def test_orchestrator_output_feeds_junior_dev(self):
        plan_payload = self._plan_payload()
        orchestrator.client = SequenceClient(
            [f"```json\n{json.dumps(plan_payload)}\n```"]
        )

        plan_result = asyncio.run(
            orchestrator.process_chat(
                "Create the router-aware plan", session_id="orch-to-junior"
            )
        )
        self.assertEqual(plan_result["type"], "plan")
        plan = plan_result["content"]

        junior_dev.client = SequenceClient(
            [
                "```tsx\nconst Navbar = () => null;\nexport default Navbar;\n```",
                "```tsx\nconst App = () => null;\nexport default App;\n```",
                "```tsx\nconst Home = () => null;\nexport default Home;\n```",
            ]
        )

        implementations = asyncio.run(
            junior_dev.implement_multiple_components(
                plan.files,
                plan.global_style.model_dump() if plan.global_style else None,
                session_id="junior-flow",
            )
        )

        self.assertEqual(implementations["type"], "batch_implementation")
        self.assertEqual(implementations["failed"], 0)
        self.assertEqual(implementations["successful"], len(plan.files))

        contents = [imp["content"] for imp in implementations["implementations"]]
        for code in contents:
            self.assertNotIn("```", code)

        calls = junior_dev.client.chat.completions.calls
        self.assertGreaterEqual(len(calls), 1)
        user_prompt = calls[0]["messages"][-1]["content"]
        self.assertIn("Routes to Implement", user_prompt)
        self.assertIn("/projects", user_prompt)


if __name__ == "__main__":
    unittest.main()

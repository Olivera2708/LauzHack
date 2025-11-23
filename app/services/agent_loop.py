import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services import orchestrator, junior_dev


def _summarize_feedback(impl_results: Dict[str, Any], plan_files: List[Any]) -> List[Dict[str, Any]]:
    feedback_items: List[Dict[str, Any]] = []

    for impl in impl_results.get("implementations", []):
        if impl.get("type") == "feedback":
            feedback_items.append(impl)

    for err in impl_results.get("errors", []):
        feedback_items.append(
            {
                "type": "feedback",
                "filename": err.get("filename", "unknown"),
                "message": err.get("error", "Unknown error"),
                "blocking": True,
            }
        )

    filename_order = {fp.filename: idx for idx, fp in enumerate(plan_files)}
    feedback_items.sort(key=lambda item: filename_order.get(item.get("filename", ""), 999))
    return feedback_items


def _build_feedback_instructions(base_instructions: str, round_index: int, feedback_items: List[Dict[str, Any]], build_error: Optional[str] = None) -> str:
    feedback_lines = []
    for item in feedback_items:
        line = f"- {item.get('filename', 'unknown')}: {item.get('message', '').strip()}"
        if item.get("blocking"):
            line += " (blocking)"
        feedback_lines.append(line)

    if build_error:
        feedback_lines.append(f"- build: {build_error} (blocking)")

    feedback_block = "\n".join(feedback_lines) if feedback_lines else "No feedback."

    return (
        f"{base_instructions}\n\n"
        f"Feedback summary (round {round_index + 1}):\n"
        f"{feedback_block}\n\n"
        "Revise the plan to address the above feedback. Keep already-implemented files stable unless a blocking issue requires changes."
    )


def _run_build_check(file_plans: Dict[str, Any], implementations: Dict[str, str]) -> Tuple[bool, str]:
    """
    Write all implementations into a temp template copy and run npm install + npm run build.
    """
    if not shutil.which("npm"):
        return True, "npm not available in environment; build check skipped."

    template_root = Path(__file__).parent.parent / "frontend_template"
    if not template_root.exists():
        return False, f"Template source missing at {template_root}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        dest = tmp_path / "project"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["cp", "-R", str(template_root), str(dest)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            return False, f"Template copy failed: {e.stderr or e.stdout}"

        for filename, content in implementations.items():
            plan = file_plans.get(filename)
            if not plan:
                return False, f"No plan info for {filename}"
            file_path = dest / plan["path"] / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        env = {"PATH": os.environ.get("PATH", ""), **os.environ}
        try:
            install_proc = subprocess.run(
                ["npm", "install", "--silent"],
                cwd=dest,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            build_proc = subprocess.run(
                ["npm", "run", "build"],
                cwd=dest,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            return True, build_proc.stdout
        except subprocess.CalledProcessError as e:
            combined = f"{e.stdout}\n{e.stderr}"
            return False, combined.strip()


async def _run_juniors_parallel(file_plans, global_style, session_map: Dict[str, str]):
    loop = asyncio.get_event_loop()
    tasks = []
    with ThreadPoolExecutor(max_workers=len(file_plans)) as executor:
        for fp in file_plans:
            sid = session_map.setdefault(fp.filename, str(uuid.uuid4()))
            tasks.append(
                loop.run_in_executor(None, lambda plan=fp, sid=sid: asyncio.run(junior_dev.implement_component(plan, global_style, sid)))
            )
        return await asyncio.gather(*tasks, return_exceptions=True)


async def run_orchestration_with_feedback(
    instructions: str,
    max_rounds: int = 3,
    orchestrator_session: Optional[str] = None,
    images: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Alternate between orchestrator planning and junior implementation with feedback and build verification.
    Keeps orchestrator session and per-file junior sessions across rounds.
    """
    iterations: List[Dict[str, Any]] = []
    current_instructions = instructions
    orch_session = orchestrator_session or f"orch-loop-{uuid.uuid4()}"
    file_plan_map: Dict[str, Any] = {}
    implementation_map: Dict[str, str] = {}
    junior_session_map: Dict[str, str] = {}

    for round_index in range(max_rounds):
        plan_result = await orchestrator.process_chat(
            current_instructions, session_id=orch_session, images=images
        )
        if plan_result.get("type") != "plan":
            return {
                "type": "error",
                "content": plan_result.get("content", "Orchestrator did not return a plan"),
                "iterations": iterations,
            }

        plan = plan_result["content"]
        for fp in plan.files:
            file_plan_map[fp.filename] = fp.model_dump()

        global_style = plan.global_style.model_dump() if plan.global_style else None
        impl_results_list = await _run_juniors_parallel(plan.files, global_style, junior_session_map)

        impl_results = {"implementations": [], "errors": []}
        for impl in impl_results_list:
            if isinstance(impl, Exception):
                impl_results["errors"].append({"filename": "unknown", "error": str(impl)})
                continue
            impl_results["implementations"].append(impl)
            if impl.get("type") == "implementation":
                implementation_map[impl["filename"]] = impl["content"]

        feedback_items = _summarize_feedback(impl_results, plan.files)
        iterations.append(
            {
                "plan": plan.model_dump(),
                "implementations": impl_results,
                "feedback": feedback_items,
            }
        )

        blocking = any(item.get("blocking") for item in feedback_items)
        missing_files = [
            fp.filename for fp in plan.files if fp.filename not in implementation_map
        ]
        if missing_files:
            blocking = True
            feedback_items.append(
                {
                    "type": "feedback",
                    "filename": ",".join(missing_files),
                    "message": "Missing implementations for planned files",
                    "blocking": True,
                }
            )

        if not blocking and impl_results.get("failed", 0) == 0:
            build_ok, build_log = _run_build_check(file_plan_map, implementation_map)
            if build_ok:
                return {
                    "type": "feedback_loop",
                    "status": "completed",
                    "iterations": iterations,
                    "build_status": "passed",
                    "build_log": build_log,
                    "implementations": implementation_map,
                    "file_plans": file_plan_map,
                    "orchestrator_session": orch_session,
                    "junior_sessions": junior_session_map,
                }
            else:
                feedback_items.append(
                    {
                        "type": "feedback",
                        "filename": "build",
                        "message": build_log[:2000],
                        "blocking": True,
                    }
                )
                blocking = True

        if round_index == max_rounds - 1 and not blocking:
            return {
                "type": "feedback_loop",
                "status": "soft_limit_reached",
                "iterations": iterations,
                "build_status": "skipped",
                "implementations": implementation_map,
                "file_plans": file_plan_map,
                "orchestrator_session": orch_session,
                "junior_sessions": junior_session_map,
            }

        current_instructions = _build_feedback_instructions(
            instructions, round_index, feedback_items, None
        )

    return {
        "type": "feedback_loop",
        "status": "max_rounds_reached",
        "iterations": iterations,
        "implementations": implementation_map,
        "file_plans": file_plan_map,
        "orchestrator_session": orch_session,
        "junior_sessions": junior_session_map,
    }

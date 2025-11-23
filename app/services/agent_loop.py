import asyncio
import uuid
from typing import Any, Dict, List, Optional

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

    # Ensure ordering matches plan file order for readability
    filename_order = {fp.filename: idx for idx, fp in enumerate(plan_files)}
    feedback_items.sort(key=lambda item: filename_order.get(item.get("filename", ""), 999))
    return feedback_items


def _build_feedback_instructions(base_instructions: str, round_index: int, feedback_items: List[Dict[str, Any]]) -> str:
    feedback_lines = []
    for item in feedback_items:
        line = f"- {item.get('filename', 'unknown')}: {item.get('message', '').strip()}"
        if item.get("blocking"):
            line += " (blocking)"
        feedback_lines.append(line)

    feedback_block = "\n".join(feedback_lines) if feedback_lines else "No feedback."

    return (
        f"{base_instructions}\n\n"
        f"Feedback summary (round {round_index + 1}):\n"
        f"{feedback_block}\n\n"
        "Revise the plan to address the above feedback. Keep already-implemented files stable unless a blocking issue requires changes."
    )


async def run_orchestration_with_feedback(
    instructions: str,
    max_rounds: int = 3,
) -> Dict[str, Any]:
    """
    Alternate between orchestrator planning and junior implementation with feedback.
    Stops early when all implementations succeed and no feedback remains.
    Soft limit: if max_rounds reached but no blocking feedback, return the latest state as runnable.
    """
    iterations: List[Dict[str, Any]] = []
    current_instructions = instructions

    for round_index in range(max_rounds):
        orch_session = f"orch-loop-{uuid.uuid4()}"
        plan_result = await orchestrator.process_chat(current_instructions, session_id=orch_session)
        if plan_result.get("type") != "plan":
            return {
                "type": "error",
                "content": plan_result.get("content", "Orchestrator did not return a plan"),
                "iterations": iterations,
            }

        plan = plan_result["content"]
        global_style = plan.global_style.model_dump() if plan.global_style else None

        junior_session = f"junior-loop-{uuid.uuid4()}"
        impl_results = await junior_dev.implement_multiple_components(
            plan.files, global_style, session_id=junior_session
        )

        feedback_items = _summarize_feedback(impl_results, plan.files)
        iterations.append(
            {
                "plan": plan.model_dump(),
                "implementations": impl_results,
                "feedback": feedback_items,
            }
        )

        blocking = any(item.get("blocking") for item in feedback_items)
        done = not feedback_items and impl_results.get("failed", 0) == 0

        if done:
            return {"type": "feedback_loop", "status": "completed", "iterations": iterations}

        if round_index == max_rounds - 1 and not blocking:
            return {
                "type": "feedback_loop",
                "status": "soft_limit_reached",
                "iterations": iterations,
            }

        current_instructions = _build_feedback_instructions(
            instructions, round_index, feedback_items
        )

    return {
        "type": "feedback_loop",
        "status": "max_rounds_reached",
        "iterations": iterations,
    }

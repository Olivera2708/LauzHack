import asyncio
import os
import shutil
import zipfile
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse
from app.services.orchestrator import process_chat
from app.services.junior_dev import implement_component
from app.services.agent_loop import run_orchestration_with_feedback
from app.schemas.plan import ChatResponse, OrchestrationPlan

router = APIRouter()

def _run_implement_component(file_plan, global_style, session_id):
    """Helper function to run async implement_component in a thread."""
    return asyncio.run(implement_component(file_plan, global_style, session_id))


def _write_template_zip(plan: OrchestrationPlan, impl_results: dict, session_id: str):
    """
    Copy frontend template, write implementation files, and return a FileResponse zip.
    """
    print("[process_instructions] Step 4: Creating temporary directory...")
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"[process_instructions] Temporary directory created: {temp_dir}")
        template_source = Path(__file__).parent.parent.parent.parent / "frontend_template"
        template_dest = Path(temp_dir) / "new_template"
        print(f"[process_instructions] Template source: {template_source}")
        print(f"[process_instructions] Template destination: {template_dest}")

        if not template_source.exists():
            return {
                "type": "error",
                "content": f"Template source not found at {template_source}",
                "session_id": session_id,
            }

        print("[process_instructions] Copying template directory...")
        shutil.copytree(
            template_source,
            template_dest,
            ignore=shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc", ".git"),
        )
        print(f"[process_instructions] Template copied successfully to {template_dest}")

        print("[process_instructions] Step 5: Processing agent implementations...")
        errors = []
        successful_files = []
        impl_list = impl_results.get("implementations", [])

        for idx, impl in enumerate(impl_list):
            if isinstance(impl, Exception):
                errors.append(
                    {
                        "filename": plan.files[idx].filename if idx < len(plan.files) else "unknown",
                        "error": str(impl),
                    }
                )
                continue

            if impl.get("type") != "implementation":
                continue

            filename = impl.get("filename")
            content = impl.get("content", "")
            if not filename:
                errors.append({"filename": "unknown", "error": "Missing filename"})
                continue

            file_plan = next((fp for fp in plan.files if fp.filename == filename), None)
            if not file_plan:
                errors.append({"filename": filename, "error": "File plan not found"})
                continue

            file_path = template_dest / file_plan.path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                file_path.write_text(content, encoding="utf-8")
                successful_files.append(filename)
                print(f"[process_instructions]   ✓ Wrote {filename}")
            except Exception as e:
                errors.append({"filename": filename, "error": f"Failed to write file: {e}"})

        print(f"[process_instructions] File writing completed - {len(successful_files)} successful, {len(errors)} errors")

        print("[process_instructions] Step 6: Creating zip file...")
        zip_path = Path(temp_dir) / "template.zip"
        file_count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(template_dest):
                dirs[:] = [d for d in dirs if d not in ["node_modules", "__pycache__", ".git"]]
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(template_dest)
                    zipf.write(file_path, arcname)
                    file_count += 1
        print(f"[process_instructions] Zip file created with {file_count} files")

        if not session_id:
            session_id = "temp"
        persistent_zip = Path(tempfile.gettempdir()) / f"template_{session_id}.zip"
        shutil.copy2(zip_path, persistent_zip)
        print(f"[process_instructions] Zip file ready at: {persistent_zip}")

        return FileResponse(
            path=str(persistent_zip),
            filename="template.zip",
            media_type="application/zip",
            headers={
                "X-Successful-Files": str(len(successful_files)),
                "X-Failed-Files": str(len(errors)),
            },
        )


def _write_template_zip_from_maps(file_plans: Dict[str, Any], implementations: Dict[str, str], session_id: str):
    """
    Write implementations provided as maps using their stored plan metadata.
    """
    # Build a pseudo plan with file objects for path resolution
    class DummyPlan:
        def __init__(self, files):
            self.files = files
    files = []
    for _, fp in file_plans.items():
        files.append(
            type("FP", (), fp)
        )
    plan = DummyPlan(files)
    impl_list = [{"type": "implementation", "filename": fname, "content": content} for fname, content in implementations.items()]
    return _write_template_zip(plan, {"implementations": impl_list}, session_id)

@router.post("/process")
async def process_instructions(
    instructions: str = Body(..., embed=True),
    session_id: str = Body(None, embed=True),
    feedback_loop: bool = Body(True, embed=True),
    max_rounds: int = Body(3, embed=True),
):
    """
    Endpoint to receive instructions, process them with parallel agents, and return a zip file.
    """
    print(f"[process_instructions] Starting - session_id: {session_id}")
    print(f"[process_instructions] Instructions received: {instructions[:100]}...")
    
    try:
        if feedback_loop:
            print("[process_instructions] Running feedback loop flow...")
            loop_result = await run_orchestration_with_feedback(
                instructions, max_rounds=max_rounds
            )
            print("[process_instructions] Feedback loop completed")
            if loop_result.get("type") != "feedback_loop":
                return loop_result
            if loop_result.get("implementations") and loop_result.get("file_plans"):
                return _write_template_zip_from_maps(
                    loop_result["file_plans"],
                    loop_result["implementations"],
                    session_id or str(uuid.uuid4()),
                )
            iterations = loop_result.get("iterations", [])
            if not iterations:
                return {
                    "type": "error",
                    "content": "Feedback loop returned no iterations",
                    "session_id": session_id,
                }
            last_iteration = iterations[-1]
            plan_data = last_iteration.get("plan")
            impl_results = last_iteration.get("implementations", {})
            if not plan_data:
                return {
                    "type": "error",
                    "content": "No plan data in feedback loop result",
                    "session_id": session_id,
                }
            plan = OrchestrationPlan(**plan_data)
            return _write_template_zip(plan, impl_results, session_id or str(uuid.uuid4()))

        # Step 1: Get orchestration plan
        print("[process_instructions] Step 1: Calling orchestrator to get plan...")
        result = await process_chat(instructions, session_id)
        print(f"[process_instructions] Orchestrator result type: {result.get('type')}")
        print(f"[process_instructions] Orchestrator result: {result}")
        
        # If we got an error or question, return it as before
        if result.get("type") != "plan":
            print(f"[process_instructions] Early return - type: {result.get('type')}")
            return result
        
        # Step 2: Extract the plan
        print("[process_instructions] Step 2: Extracting orchestration plan...")
        plan: OrchestrationPlan = result.get("content")
        if not plan or not plan.files:
            print("[process_instructions] ERROR: No files in plan")
            return {
                "type": "error",
                "content": "No files to implement in the plan",
                "session_id": session_id
            }
        
        print(f"[process_instructions] Plan extracted - {len(plan.files)} files to implement")
        for idx, file_plan in enumerate(plan.files):
            print(f"[process_instructions]   File {idx+1}: {file_plan.filename} at {file_plan.path}")
        
        # Step 3: Call multiple junior_dev agents in parallel with separate session_ids
        print("[process_instructions] Step 3: Creating parallel implementation tasks...")
        
        # Generate unique session_id (pure UUID) for each file implementation
        file_plans_with_sessions = [
            (file_plan, str(uuid.uuid4()))  # Unique UUID session_id for each
            for file_plan in plan.files
        ]
        print(f"[process_instructions] Created {len(file_plans_with_sessions)} parallel tasks with separate session_ids")
        
        # Execute in truly parallel threads - wrap blocking API calls in threads
        print("[process_instructions] Executing parallel agent calls in threads...")
        loop = asyncio.get_event_loop()
        
        # Create a ThreadPoolExecutor for true parallel execution
        global_style_dict = (
            plan.global_style.model_dump() if plan.global_style else None
        )
        with ThreadPoolExecutor(max_workers=len(file_plans_with_sessions)) as executor:
            # Run each blocking API call in a separate thread
            implementation_tasks = [
                loop.run_in_executor(
                    executor,
                    _run_implement_component,
                    file_plan,
                    global_style_dict,
                    session_id
                )
                for file_plan, session_id in file_plans_with_sessions
            ]
            implementations = await asyncio.gather(*implementation_tasks, return_exceptions=True)
        
        print(f"[process_instructions] Parallel execution completed - {len(implementations)} results received")
        
        return _write_template_zip(
            plan,
            {"implementations": implementations},
            session_id or str(uuid.uuid4()),
        )
    
    except Exception as e:
        print(f"[process_instructions] EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "type": "error",
            "content": f"Unexpected error: {str(e)}",
            "session_id": session_id
        }


import asyncio
import os
import shutil
import zipfile
import tempfile
import uuid
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Union
from fastapi import APIRouter, Body, File, UploadFile, Form, Request
from fastapi.responses import FileResponse
from app.services.orchestrator import process_chat
from app.services.junior_dev import implement_component
from app.schemas.plan import ChatResponse, OrchestrationPlan, TestRequest, TestResponse
import asyncio
import re
import os
import json
from typing import Optional
import time
from fastapi import HTTPException

router = APIRouter()

def _run_implement_component(file_plan, global_style, session_id):
    """Helper function to run async implement_component in a thread."""
    return asyncio.run(implement_component(file_plan, global_style, session_id))

# async def test_endpoint(request: TestRequest):
#     """
#     Test endpoint that prints received data and returns a response
#     """
#     print("🔵 TEST ENDPOINT CALLED!")
#     print(f"📨 Received message: {request.message}")
    
#     if request.image_data:
#         print(f"🖼️ Received image data (first 100 chars): {request.image_data[:100]}...")
#         image_size = len(request.image_data)
#         print(f"📊 Image data size: {image_size} characters")
#     else:
#         print("📭 No image data received")
    
#     local_url = None
#     project_path = "../frontend"
#     package_json_path = os.path.join(project_path, "package.json")
#     if not os.path.exists(package_json_path):
#         print(f"❌ package.json not found at: {package_json_path}")
#         raise HTTPException(status_code=400, detail="Not a valid React project (package.json not found)")

#     print("🏗️ Starting build and start process...")
#     try:
#         local_url = await build_and_start(project_path)
#         print(f"✅ Local URL obtained: {local_url}")
#     except Exception as e:
#         print(f"❌ Build and start failed: {e}")
    
#     print("`📋 Request details logged successfully")
    
#     return TestResponse(
#         success=True,
#         message="Backend received your data successfully!" + (f" Local server started at {local_url}" if local_url else ""),
#         received_data={
#             "message": request.message,
#             "has_image": bool(request.image_data),
#             "image_size": len(request.image_data) if request.image_data else 0,
#             "local_url": local_url
#         },
#         backend_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
#         local_url=local_url
#     )

async def build_and_start(project_path: str) -> str:
    """Build existing React project and deploy to Netlify"""
     # 1️⃣ Install dependencies
    print("Installing dependencies...")
    install = await asyncio.create_subprocess_exec(
        "npm", "install",
        cwd=project_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await install.wait()
    print("✅ npm install complete")

    # 2️⃣ Read package.json to determine run script
    package_json_path = os.path.join(project_path, "package.json")
    with open(package_json_path, "r") as f:
        package = json.load(f)

    run_script = None
    scripts = package.get("scripts", {})

    if "dev" in scripts:
        run_script = "dev"        # Vite, Next.js, etc.
    elif "start" in scripts:
        run_script = "start"      # CRA, default node start
    else:
        raise Exception("No dev or start script found in package.json.")

    print(f"Using script: npm run {run_script}")

    # 3️⃣ Run local dev server
    process = await asyncio.create_subprocess_exec(
        "npm", "run", run_script,
        cwd=project_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    url_regex = re.compile(r"(http://localhost:\d+)")
    url_found = None

    print("Waiting for local server to start...")

    # 4️⃣ Read output in real time until we detect URL
    while True:
        line = await process.stdout.readline()
        if not line:
            break

        decoded = line.decode("utf-8").strip()
        print(decoded)

        match = url_regex.search(decoded)
        if match:
            url_found = match.group(1)
            print(f"🎉 Found local URL: {url_found}")
            return url_found  # return immediately

    raise Exception("Could not detect local development URL.")

@router.post("/process")
async def process_instructions(request: Request):
    """
    Endpoint to receive instructions (with optional images/sketches), process them with parallel agents, and return a zip file.
    
    Supports both:
    - JSON format (backward compatible): {"instructions": "...", "session_id": "..."}
    - Multipart/form-data format (with images): form data with instructions, session_id, and optional images
    
    Args:
        request: FastAPI request object to detect content type and handle form data
        instructions: Text instructions describing what to build (from JSON body or form)
        session_id: Optional session ID for maintaining context
    """
    # Handle multipart/form-data requests (for images)
    content_type = request.headers.get("content-type", "")
    image_data_list = []
    instructions = None
    session_id = None
    
    if "multipart/form-data" in content_type:
        # Parse form data manually for multipart requests
        form = await request.form()
        instructions = form.get("instructions", "")
        session_id = form.get("session_id")
        
        # Handle images from form data
        image_files = form.getlist("images")
        if not image_files:
            # Try single file upload
            image_file = form.get("images")
            if image_file and hasattr(image_file, 'read'):
                image_files = [image_file]
        
        if image_files:
            print(f"[process_instructions] Processing {len(image_files)} image(s)...")
            for idx, image_file in enumerate(image_files):
                try:
                    # Read image content
                    if hasattr(image_file, 'read'):
                        image_content = await image_file.read()
                        mime_type = image_file.content_type or "image/jpeg"
                    else:
                        # Handle string file paths if needed
                        continue
                    
                    # Convert to base64
                    image_base64 = base64.b64encode(image_content).decode('utf-8')
                    image_data_list.append({
                        "mime_type": mime_type,
                        "data": image_base64
                    })
                    filename = getattr(image_file, 'filename', f'image_{idx}')
                    print(f"[process_instructions]   Image {idx+1}: {filename}, type: {mime_type}, size: {len(image_content)} bytes")
                except Exception as e:
                    print(f"[process_instructions]   ERROR processing image {idx+1}: {str(e)}")
                    # Continue with other images even if one fails
            print(f"[process_instructions] Successfully processed {len(image_data_list)} image(s)")
    
    # Handle JSON requests (backward compatible)
    elif "application/json" in content_type:
        try:
            body = await request.json()
            instructions = body.get("instructions", "")
            session_id = body.get("session_id")
        except Exception as e:
            print(f"[process_instructions] Error parsing JSON body: {str(e)}")
            return {
                "type": "error",
                "content": f"Invalid JSON body: {str(e)}",
                "session_id": session_id
            }
    
    # Validate instructions
    if not instructions:
        return {
            "type": "error",
            "content": "Instructions are required",
            "session_id": session_id
        }
    
    print(f"[process_instructions] Starting - session_id: {session_id}")
    print(f"[process_instructions] Instructions received: {instructions[:100]}...")
    
    try:
        # Step 1: Get orchestration plan (with images if provided)
        print("[process_instructions] Step 1: Calling orchestrator to get plan...")
        result = await process_chat(instructions, session_id, images=image_data_list if image_data_list else None)
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
        global_style_dict = plan.global_style.dict() if plan.global_style else None
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
        
        # Step 4: Create a temporary directory for the new template
        print("[process_instructions] Step 4: Creating temporary directory...")
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"[process_instructions] Temporary directory created: {temp_dir}")
            template_source = Path(__file__).parent.parent.parent.parent / "frontend_template"
            template_dest = Path(temp_dir) / "new_template"
            print(f"[process_instructions] Template source: {template_source}")
            print(f"[process_instructions] Template destination: {template_dest}")
            
            if not template_source.exists():
                print(f"[process_instructions] ERROR: Template source not found at {template_source}")
                return {
                    "type": "error",
                    "content": f"Template source not found at {template_source}",
                    "session_id": session_id
                }
            persistent_build_dir = Path("persistent_builds") / f"build_{int(time.time())}"
            persistent_build_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy the entire frontend_template directory
            print("[process_instructions] Copying template directory...")
            shutil.copytree(
                template_dest, persistent_build_dir / "template",
                ignore=shutil.ignore_patterns('node_modules', '__pycache__', '*.pyc', '.git')
            )
            print(f"[process_instructions] Template copied successfully to {template_dest}")
            
            # Step 5: Write new files from agent implementations
            print("[process_instructions] Step 5: Processing agent implementations...")
            errors = []
            successful_files = []
            
            for idx, impl_result in enumerate(implementations):
                print(f"[process_instructions] Processing implementation {idx+1}/{len(implementations)}")
                
                # Handle exceptions from gather
                if isinstance(impl_result, Exception):
                    print(f"[process_instructions]   Exception caught: {str(impl_result)}")
                    errors.append({
                        "filename": plan.files[idx].filename if idx < len(plan.files) else "unknown",
                        "error": str(impl_result)
                    })
                    continue
                
                if impl_result.get("type") == "error":
                    print(f"[process_instructions]   Error result: {impl_result.get('content', 'Unknown error')}")
                    errors.append({
                        "filename": impl_result.get("filename", "unknown"),
                        "error": impl_result.get("content", "Unknown error")
                    })
                    continue
                
                filename = impl_result.get("filename")
                content = impl_result.get("content", "")
                print(f"[process_instructions]   Processing file: {filename} ({len(content)} chars)")
                
                if not filename:
                    print("[process_instructions]   ERROR: No filename in result")
                    errors.append({
                        "filename": "unknown",
                        "error": "No filename in implementation result"
                    })
                    continue
                
                # Find the corresponding file plan to get the path
                file_plan = next((fp for fp in plan.files if fp.filename == filename), None)
                if not file_plan:
                    print(f"[process_instructions]   ERROR: File plan not found for {filename}")
                    errors.append({
                        "filename": filename,
                        "error": "File plan not found"
                    })
                    continue
                
                # Create the directory structure
                file_path = template_dest / file_plan.path / filename
                print(f"[process_instructions]   Writing file to: {file_path}")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write the file
                try:
                    file_path.write_text(content, encoding='utf-8')
                    successful_files.append(filename)
                    print(f"[process_instructions]   ✓ Successfully wrote {filename}")
                except Exception as e:
                    print(f"[process_instructions]   ✗ Failed to write {filename}: {str(e)}")
                    errors.append({
                        "filename": filename,
                        "error": f"Failed to write file: {str(e)}"
                    })
            local_url = None
            print("🏗️ Starting build and start process...")
            try:
                local_url = await build_and_start(template_dest)

                print(f"✅ Local URL obtained: {local_url}")
            except Exception as e:
                print(f"❌ Build and start failed: {e}")
            
            print(f"[process_instructions] File writing completed - {len(successful_files)} successful, {len(errors)} errors")
            
            # Step 6: Create zip file
            print("[process_instructions] Step 6: Creating zip file...")
            zip_path = Path(temp_dir) / "template.zip"
            print(f"[process_instructions] Zip file path: {zip_path}")
            
            file_count = 0
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(template_dest):
                    # Skip node_modules and other unnecessary directories
                    dirs[:] = [d for d in dirs if d not in ['node_modules', '__pycache__', '.git']]
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(template_dest)
                        zipf.write(file_path, arcname)
                        file_count += 1
                        if file_count % 10 == 0:
                            print(f"[process_instructions]   Added {file_count} files to zip...")
            
            print(f"[process_instructions] Zip file created with {file_count} files")
            
            # Step 7: Return the zip file
            print("[process_instructions] Step 7: Preparing zip file response...")
            # We need to copy it to a persistent location since temp_dir will be deleted
            if not session_id:
                session_id = "temp"
            persistent_zip = Path(tempfile.gettempdir()) / f"template_{session_id}.zip"
            print(f"[process_instructions] Copying zip to persistent location: {persistent_zip}")
            shutil.copy2(zip_path, persistent_zip)
            print(f"[process_instructions] Zip file ready at: {persistent_zip}")
            print(f"[process_instructions] Returning FileResponse - {len(successful_files)} successful, {len(errors)} errors")
            
            return FileResponse(
                path=str(persistent_zip),
                filename="template.zip",
                media_type="application/zip",
                headers={
                    "X-Successful-Files": str(len(successful_files)),
                    "X-Failed-Files": str(len(errors)),
                    "X-Documentation-URL": local_url
                }
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


# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
import json
from typing import Optional
import traceback  # Add this import
import time
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import re


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
)

class TestRequest(BaseModel):
    message: str
    image_data: Optional[str] = None

class TestResponse(BaseModel):
    success: bool
    message: str
    received_data: dict
    backend_timestamp: str
    local_url: Optional[str] = None 

@app.post("/test", response_model=TestResponse)
async def test_endpoint(request: TestRequest):
    """
    Test endpoint that prints received data and returns a response
    """
    print("🔵 TEST ENDPOINT CALLED!")
    print(f"📨 Received message: {request.message}")
    
    if request.image_data:
        print(f"🖼️ Received image data (first 100 chars): {request.image_data[:100]}...")
        image_size = len(request.image_data)
        print(f"📊 Image data size: {image_size} characters")
    else:
        print("📭 No image data received")
    
    local_url = None
    project_path = "../frontend"
    package_json_path = os.path.join(project_path, "package.json")
    if not os.path.exists(package_json_path):
        print(f"❌ package.json not found at: {package_json_path}")
        raise HTTPException(status_code=400, detail="Not a valid React project (package.json not found)")

    print("🏗️ Starting build and start process...")
    try:
        local_url = await build_and_start(project_path)
        print(f"✅ Local URL obtained: {local_url}")
    except Exception as e:
        print(f"❌ Build and start failed: {e}")
    
    print("📋 Request details logged successfully")
    
    return TestResponse(
        success=True,
        message="Backend received your data successfully!" + (f" Local server started at {local_url}" if local_url else ""),
        received_data={
            "message": request.message,
            "has_image": bool(request.image_data),
            "image_size": len(request.image_data) if request.image_data else 0,
            "local_url": local_url
        },
        backend_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        local_url=local_url
    )

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
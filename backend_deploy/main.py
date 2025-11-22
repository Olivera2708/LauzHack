# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
import json
from typing import Optional
import traceback  # Add this import
import time

app = FastAPI()

class DeployRequest(BaseModel):
    project_path: str

class DeployResponse(BaseModel):
    url: str
    success: bool
    message: str

@app.post("/deploy", response_model=DeployResponse)
async def deploy_react_app(request: DeployRequest):
    """
    Build and deploy existing React project from folder
    """
    try:
        project_path = request.project_path
        print(f"Received request for project: {project_path}")  # Debug log
        
        # Validate project path
        if not os.path.exists(project_path):
            print(f"Path does not exist: {project_path}")  # Debug log
            raise HTTPException(status_code=400, detail="Project path does not exist")
        
        package_json_path = os.path.join(project_path, "package.json")
        if not os.path.exists(package_json_path):
            print(f"package.json not found at: {package_json_path}")  # Debug log
            raise HTTPException(status_code=400, detail="Not a valid React project (package.json not found)")
        
        # Validate Netlify token
        netlify_token = "nfp_wcwS4sWKycMsWBr7Cu7c7m7rBhpGNYUBb854"
        if not netlify_token:
            raise HTTPException(status_code=500, detail="Netlify token not configured")
        
        print("Starting build and deploy process...")  # Debug log
        # Build and deploy
        url = await build_and_deploy(project_path, netlify_token)
        
        return DeployResponse(
            url=url,
            success=True,
            message="App deployed successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Print full error traceback
        print(f"Unexpected error: {str(e)}")
        print(traceback.format_exc())  # This will show the full error stack
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

async def build_and_deploy(project_path: str, netlify_token: str) -> str:
    """Build existing React project and deploy to Netlify"""
    
    # Install dependencies
    print(f"Installing dependencies in {project_path}...")
    result = subprocess.run(
        ["npm", "install"], 
        cwd=project_path, 
        capture_output=True, 
        text=True,
        timeout=300
    )
    if result.returncode != 0:
        error_msg = f"npm install failed: {result.stderr}"
        print(error_msg)
        raise Exception(error_msg)
    print("✅ npm install successful")

   # Build the app
    print("Building React app...")
    # Check available build scripts
    package_json_path = os.path.join(project_path, "package.json")
    with open(package_json_path, 'r') as f:
        package_data = json.load(f)

    # Define build_script with a default value FIRST
    build_script = "build"  # Default value

    if "scripts" in package_data:
        available_scripts = package_data["scripts"]
        print(f"Available scripts: {available_scripts}")
        
        if "build" in available_scripts:
            build_script = "build"
        elif "build:prod" in available_scripts:
            build_script = "build:prod"
        else:
            raise Exception(f"No build script found. Available: {list(available_scripts.keys())}")

    print(f"Using build script: {build_script}")
    result = subprocess.run(
        ["npm", "run", build_script], 
        cwd=project_path, 
        capture_output=True, 
        text=True,
        timeout=300  # Add timeout
    )

    # Print BOTH stdout and stderr for debugging
    print(f"Build STDOUT: {result.stdout}")
    print(f"Build STDERR: {result.stderr}")
    print(f"Build return code: {result.returncode}")

    if result.returncode != 0:
        raise Exception(f"Build failed: {result.stderr}\n{result.stdout}")
    print("✅ Build successful")

    # Determine build output directory
    build_dir = "dist"
    if os.path.exists(os.path.join(project_path, "build")):
        build_dir = "build"
    elif os.path.exists(os.path.join(project_path, "dist")):
        build_dir = "dist"
    
    build_output_path = os.path.join(project_path, build_dir)
    
    if not os.path.exists(build_output_path):
        raise Exception(f"Build output directory not found: {build_dir}")
    print(f"✅ Build output found: {build_output_path}")

    # Deploy to Netlify
    print("Deploying to Netlify...")
    
    # Install Netlify CLI if not present
    print("Installing Netlify CLI...")
    result = subprocess.run(
        ["npm", "install", "-g", "netlify-cli"], 
        capture_output=True, 
        text=True
    )
    if result.returncode != 0:
        print(f"⚠️ Netlify CLI install warning: {result.stderr}")
    else:
        print("✅ Netlify CLI installed")

    # Test Netlify CLI
    result = subprocess.run(
        ["netlify", "--version"],
        capture_output=True,
        text=True
    )
    print(f"Netlify CLI version: {result.stdout}")
    # Test Netlify authentication first
    print("Testing Netlify authentication...")
    auth_test = subprocess.run([
        "npx", "netlify", "status",
        "--auth", netlify_token
    ], capture_output=True, text=True, timeout=30)
    
    print(f"Auth test STDOUT: {auth_test.stdout}")
    print(f"Auth test STDERR: {auth_test.stderr}")
    print(f"Auth test return code: {auth_test.returncode}")

    # Deploy with detailed logging
    print(f"Running Netlify deploy with token: {netlify_token[:10]}...")
    
    # Deploy to Netlify
    print("Deploying to Netlify...")
    
    # First, create a new site using the Netlify API
    import urllib.request
    import urllib.error
    
    print("Creating new Netlify site...")
    
    site_name = f"react-preview-{int(time.time())}"
    
    create_site_req = urllib.request.Request(
        "https://api.netlify.com/api/v1/sites",
        data=json.dumps({"name": site_name}).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {netlify_token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(create_site_req) as response:
            site_data = json.loads(response.read().decode())
            site_id = site_data["site_id"]
            print(f"✅ Created site: {site_id}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Failed to create site: {error_body}")
        raise Exception(f"Failed to create Netlify site: {error_body}")

    # Now deploy to the created site using the site_id
    print(f"Deploying to site {site_id}...")
    
    result = subprocess.run([
        "npx", "netlify", "deploy",
        "--auth", netlify_token,
        "--site", site_id,  # Use the actual site_id from API
        "--dir", build_output_path,
        "--prod",
        "--json",
        "--message", "Auto-deploy from React chat"
    ], capture_output=True, text=True, cwd=project_path, timeout=120)

    # Parse Netlify response to get URL
    try:
        deploy_data = json.loads(result.stdout)
        print(f"Netlify response data: {deploy_data}")
        
        site_url = deploy_data.get("deploy_url") or deploy_data.get("live_url") or deploy_data.get("url")
        if site_url:
            print(f"✅ Deployment successful: {site_url}")
            return site_url
        else:
            # Get site ID and construct URL
            site_id = deploy_data.get("site_id")
            if site_id:
                url = f"https://{site_id}.netlify.app"
                print(f"✅ Deployment successful: {url}")
                return url
            else:
                raise Exception("No URL or site_id found in Netlify response")
    except Exception as e:
        print(f"Error parsing Netlify response: {e}")
        raise Exception(f"Failed to parse Netlify response: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Quick Start Guide

## What Was Fixed

This document summarizes the fixes made to get the LauzHack project working:

### Backend Fixes

1. **Fixed frontend_template path** (`app/api/v1/endpoints/instructions.py`):
   - Updated path from `Path(__file__).parent.parent.parent.parent` to `Path(__file__).parent.parent.parent`
   - Now correctly points to `app/frontend_template/` after the directory was moved

2. **Fixed dependency imports** (`app/services/junior_dev.py`):
   - Fixed `dep.imports` to extract names from FunctionInfo objects: `[imp.name for imp in dep.imports]`
   - Fixed `dep.filename` to `dep.from_path` (correct schema attribute)

3. **Added CORS middleware** (`app/main.py`):
   - Added `CORSMiddleware` to allow frontend-backend communication
   - Configured to allow all origins (change in production)

4. **Added missing __init__.py** (`app/services/`):
   - Created missing `__init__.py` file in services directory

5. **Updated requirements.txt**:
   - Changed `uvicorn` to `uvicorn[standard]` for production features

### Frontend Fixes

1. **Added missing dependency** (`app/frontend_template/package.json`):
   - Added `@radix-ui/react-icons` package (required by shadcn/ui components)

2. **Verified all components**:
   - All shadcn/ui components are properly configured
   - Path aliases (`@/`) working correctly
   - Tailwind CSS theme configured

## Getting Started

### 1. Backend Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt

# Run the test script to verify setup
python test_setup.py

# Start the backend server
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

API Documentation:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 2. Frontend Template

The frontend template is already set up with all dependencies installed.

To run it in development mode:

```bash
cd app/frontend_template
npm run dev
```

The frontend will be available at `http://localhost:5173`

To build for production:

```bash
cd app/frontend_template
npm run build
```

### 3. Environment Variables

Make sure you have a `.env` file in the project root with your API keys:

```env
# Required: At least one API key
GEMINI_API_KEY=your_gemini_api_key_here
TOGETHER_API_KEY=your_together_api_key_here

# Model configuration
ORCHESTRATOR_MODEL=gemini-3-pro-preview
JUNIOR_DEV_MODEL=Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8

# Base URLs
ORCHESTRATOR_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
JUNIOR_DEV_BASE_URL=https://api.together.xyz/v1
```

## Testing the API

### Option 1: Using the Swagger UI

1. Go to `http://127.0.0.1:8000/docs`
2. Click on `POST /api/v1/instructions/process`
3. Click "Try it out"
4. Enter your instructions in the request body:
   ```json
   {
     "instructions": "Create a user profile card with avatar, name, email, and edit button"
   }
   ```
5. Click "Execute"
6. Download the generated template.zip file

### Option 2: Using curl

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/instructions/process" \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "Create a user profile card with avatar, name, email, and edit button"
  }' \
  --output template.zip
```

## Project Structure

```
LauzHack/
├── app/
│   ├── api/               # API endpoints
│   │   └── v1/endpoints/
│   │       └── instructions.py
│   ├── core/              # Configuration
│   │   └── config.py
│   ├── schemas/           # Pydantic models
│   │   ├── plan.py
│   │   └── instruction.py
│   ├── services/          # Business logic
│   │   ├── orchestrator.py
│   │   └── junior_dev.py
│   ├── frontend_template/ # React template
│   │   ├── src/
│   │   │   ├── components/ui/
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   └── package.json
│   └── main.py           # FastAPI app
├── requirements.txt
├── test_setup.py         # Setup verification script
└── README.md

```

## How It Works

1. **User sends instructions** → API endpoint receives request
2. **Orchestrator Agent** → Analyzes instructions and creates a component plan
3. **Junior Dev Agents** → Multiple agents work in parallel to implement each component
4. **Template Builder** → Combines implementations with the base template
5. **Zip File** → Returns a complete React project ready to run

## Troubleshooting

### Backend won't start
- Ensure you're in the virtual environment: `source venv/bin/activate`
- Verify dependencies: `python test_setup.py`
- Check if port 8000 is already in use

### Frontend build fails
- Install dependencies: `cd app/frontend_template && npm install`
- Clear cache: `rm -rf node_modules package-lock.json && npm install`

### API returns errors
- Check `.env` file has valid API keys
- Verify the model names are correct
- Check the logs in the terminal

## Next Steps

- Modify the orchestrator prompt in `app/services/orchestrator.py`
- Add more shadcn/ui components to the template
- Customize the design system in `app/frontend_template/src/index.css`
- Deploy to production (update CORS settings first!)

## Support

For issues, check:
1. The logs in the terminal
2. The API documentation at `/docs`
3. The test script output: `python test_setup.py`


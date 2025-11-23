# LauzHack API

A React component generator API powered by AI agents. This system uses an orchestrator to plan components and parallel junior dev agents to implement them.

## Setup

### Backend Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```env
   # API Keys
   TOGETHER_API_KEY=your_together_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here

   # Model Configuration
   ORCHESTRATOR_MODEL=gemini-3-pro-preview
   JUNIOR_DEV_MODEL=Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8

   # Base URLs
   ORCHESTRATOR_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   JUNIOR_DEV_BASE_URL=https://api.together.xyz/v1
   ```

### Frontend Template

The frontend template is a React + TypeScript + Vite + Tailwind CSS + shadcn/ui setup located at `app/frontend_template/`.

Components included:
- Button, Card, Input, Label, Select, Textarea
- Dialog, Dropdown Menu, Avatar, Badge, Switch, Checkbox

## Running the App

### Start the Backend Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Run the Frontend Template (Optional)

```bash
cd app/frontend_template
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## Documentation

Interactive API documentation is available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Endpoints

### `POST /api/v1/instructions/process`

Process natural language instructions and generate a React component template.

**Request Body:**
```json
{
  "instructions": "Create a user profile card with avatar, name, and email",
  "session_id": "optional-session-id"
}
```

**Response:**
- If the orchestrator needs clarification: Returns a question
- If successful: Returns a zip file containing the generated React template

## Architecture

1. **Orchestrator Agent**: Analyzes user instructions and creates a detailed component plan
2. **Junior Dev Agents**: Multiple agents work in parallel to implement each component
3. **Template Builder**: Combines implementations with the base template and returns a zip file

## Features

- 🤖 AI-powered component generation
- ⚡ Parallel implementation for faster generation
- 🎨 Consistent design with shadcn/ui components
- 📦 Complete project template output
- 💬 Interactive clarification when needed

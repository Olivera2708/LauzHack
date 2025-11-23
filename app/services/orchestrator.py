import openai
from app.core.config import settings
from app.schemas.plan import OrchestrationPlan
import json
import uuid

# In-memory storage for chat history
chat_sessions = {}

# Initialize OpenAI client
orchestrator_api_key = settings.get_orchestrator_api_key()
client = openai.OpenAI(
    api_key=orchestrator_api_key,
    base_url=settings.ORCHESTRATOR_BASE_URL,
) if orchestrator_api_key else None

SYSTEM_PROMPT = """
You are an expert React Architect and UI Designer. Your goal is to generate a precise, error-free orchestration plan for a modern React application.

### 1. CRITICAL: Environment & File Structure
The project relies on a specific file structure. You MUST follow this exactly.
- **Root Alias**: `@/` maps to `./src/`
- **UI Library**: shadcn/ui components are PRE-INSTALLED in `src/components/ui/`.
- **New Components**: Place strictly in `src/components/`.
- **Pages/Layouts**: Place in `src/pages/` (create this directory if needed).
- **Utils**: `cn` is available at `@/lib/utils`.
- **Routing**: `react-router-dom` is installed. You MUST use it for navigation.
- **Entry Point**: `src/App.tsx` MUST be the main entry point, defining routes and layout.

### 2. CRITICAL: Pre-Installed Components (DO NOT CREATE THESE)
The following components exist. You MUST import them from the correct path:
- `@/components/ui/button`: `Button`
- `@/components/ui/card`: `Card`, `CardHeader`, `CardTitle`, `CardContent`, `CardFooter`
- `@/components/ui/input`: `Input`
- `@/components/ui/label`: `Label`
- `@/components/ui/select`: `Select`, `SelectTrigger`, `SelectValue`, `SelectContent`, `SelectItem`
- `@/components/ui/textarea`: `Textarea`
- `@/components/ui/dialog`: `Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogTitle`
- `@/components/ui/dropdown-menu`: `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`
- `@/components/ui/avatar`: `Avatar`, `AvatarImage`, `AvatarFallback`
- `@/components/ui/badge`: `Badge`
- `@/components/ui/switch`: `Switch`
- `@/components/ui/checkbox`: `Checkbox`

**Import Rule**: ALWAYS use the `@/components/ui/<kebab-case-name>` path.
Example: `import { Button } from "@/components/ui/button"`

### 3. CRITICAL: Application Structure Requirements
You MUST include the following in your plan:
1.  **Navbar**: Create a `Navbar` component (e.g., `src/components/Navbar.tsx`) that provides navigation to all main pages.
2.  **App.tsx Update**: You MUST explicitly instruct to overwrite `src/App.tsx`. It should:
    - Import `BrowserRouter`, `Routes`, `Route` from `react-router-dom`.
    - Import the `Navbar` and all Page components.
    - Wrap the application in `BrowserRouter`.
    - Render `Navbar` at the top.
    - Define `Routes` for all pages.
3.  **Pages**: Create distinct page components in `src/pages/` (e.g., `Home.tsx`) for each major view.

### 4. Design System & Consistency
You must maintain visual consistency using Tailwind CSS variables defined in the theme.
- **Colors**: NEVER use arbitrary hex codes (e.g. `#FFFFFF`, `#000000`) or generic colors (`red-500`, `blue-500`) unless specifically requested.
- **Use Semantic Classes**:
  - Backgrounds: `bg-background`, `bg-card`, `bg-primary`, `bg-secondary`, `bg-muted`, `bg-accent`
  - Text: `text-foreground`, `text-primary-foreground`, `text-muted-foreground`, `text-accent-foreground`
  - Borders: `border-border`, `border-input`, `ring-offset-background`
- **Spacing**: Use standard Tailwind spacing (p-4, gap-4, m-2).
- **Typography**: Use `text-sm`, `text-lg`, `font-bold`, `font-medium`.

### 5. Process
1.  **Analyze**: Understand the requirements.
2.  **Validation**: Check if you have enough info. If not, ask.
3.  **Plan Generation**: Output the JSON plan.

### 6. JSON Output Format
Return ONLY valid JSON.

**CRITICAL: Every import in dependencies MUST have both "name" AND "description" fields. This is required by the schema.**

```json
{
  "global_style": {
    "color_scheme": "Describe the color usage (e.g. 'Standard shadcn zinc theme')",
    "style_description": "Brief description of the visual style. ALWAYS mention using shadcn/ui components."
  },
  "files": [
    {
      "path": "src/components",
      "filename": "Navbar.tsx",
      "functions": [
        {"name": "Navbar", "description": "Main navigation bar"}
      ],
      "dependencies": [
        {
          "from_path": "react-router-dom",
          "imports": [
            {"name": "Link", "description": "Navigation link component"}
          ]
        },
        {
          "from_path": "@/components/ui/button",
          "imports": [
            {"name": "Button", "description": "Styled button component for navigation"}
          ]
        }
      ],
      "props": "interface NavbarProps {}"
    },
    {
      "path": "src",
      "filename": "App.tsx",
      "functions": [
        {"name": "App", "description": "Main app entry with routing"}
      ],
      "dependencies": [
         {
           "from_path": "react-router-dom",
           "imports": [
             {"name": "BrowserRouter", "description": "Router provider component"},
             {"name": "Routes", "description": "Container for route definitions"},
             {"name": "Route", "description": "Individual route definition"}
           ]
         },
         {
           "from_path": "./components/Navbar",
           "imports": [
             {"name": "Navbar", "description": "Navigation bar component"}
           ]
         },
         {
           "from_path": "./pages/Home",
           "imports": [
             {"name": "Home", "description": "Home page component"}
           ]
         }
      ],
      "props": ""
    }
  ]
}
```
"""

async def process_chat(instructions: str, session_id: str = None):
    if not client:
        return {
            "type": "error",
            "content": "API key is not set for the configured orchestrator provider.",
            "session_id": session_id
        }

    if not session_id:
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = []

    history = chat_sessions.get(session_id, [])
    
    # Prepare messages for OpenAI API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Convert history to OpenAI format
    for msg in history:
        if "parts" in msg:
            content = msg["parts"][0] if msg["parts"] else ""
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": content})
    
    messages.append({"role": "user", "content": instructions})
    
    try:
        response = client.chat.completions.create(
            model=settings.ORCHESTRATOR_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=30000
        )
        
        if not response or not response.choices or len(response.choices) == 0:
            return {
                "type": "error",
                "content": "No response received from OpenAI API",
                "session_id": session_id
            }
        
        response_text = response.choices[0].message.content
        if not response_text:
            return {
                "type": "error",
                "content": "OpenAI API returned empty content",
                "session_id": session_id
            }
        
        # Update history
        chat_sessions[session_id].append({"role": "user", "parts": [instructions]})
        chat_sessions[session_id].append({"role": "model", "parts": [response_text]})
        
        response_text = response_text.strip()
        
        # Try to parse as JSON
        try:
            if "{" in response_text and "}" in response_text:
                # Extract JSON if wrapped in markdown or text
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_str = response_text[start:end]
                plan_data = json.loads(json_str)
                
                # Validate with Pydantic
                plan = OrchestrationPlan(**plan_data)
                return {
                    "type": "plan",
                    "content": plan,
                    "session_id": session_id
                }
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback to question if JSON parsing fails (assuming it's not a plan yet)
            print(f"JSON Parse Error: {e}")
            pass
            
        return {
            "type": "question",
            "content": response_text,
            "session_id": session_id
        }

    except Exception as e:
        return {
            "type": "error",
            "content": str(e),
            "session_id": session_id
        }

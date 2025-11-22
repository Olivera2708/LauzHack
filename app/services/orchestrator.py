import google.generativeai as genai
from app.core.config import settings
from app.schemas.plan import OrchestrationPlan
import json
import uuid

# In-memory storage for chat history
chat_sessions = {}

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are an expert React Architect and UI Designer. Your goal is to generate a precise, error-free orchestration plan for a modern React application.

### 1. CRITICAL: Environment & File Structure
The project relies on a specific file structure. You MUST follow this exactly.
- **Root Alias**: `@/` maps to `./src/`
- **UI Library**: shadcn/ui components are PRE-INSTALLED in `src/components/ui/`.
- **New Components**: Place strictly in `src/components/`.
- **Pages/Layouts**: Place in `src/pages/` or define in `src/App.tsx`.
- **Utils**: `cn` is available at `@/lib/utils`.

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

### 3. Design System & Consistency
You must maintain visual consistency using Tailwind CSS variables defined in the theme.
- **Colors**: NEVER use arbitrary hex codes (e.g. `#FFFFFF`, `#000000`) or generic colors (`red-500`, `blue-500`) unless specifically requested.
- **Use Semantic Classes**:
  - Backgrounds: `bg-background`, `bg-card`, `bg-primary`, `bg-secondary`, `bg-muted`, `bg-accent`
  - Text: `text-foreground`, `text-primary-foreground`, `text-muted-foreground`, `text-accent-foreground`
  - Borders: `border-border`, `border-input`, `ring-offset-background`
- **Spacing**: Use standard Tailwind spacing (p-4, gap-4, m-2).
- **Typography**: Use `text-sm`, `text-lg`, `font-bold`, `font-medium`.

### 4. Process
1.  **Analyze**: Understand the requirements.
2.  **Validation**: Check if you have enough info. If not, ask.
3.  **Plan Generation**: Output the JSON plan.

### 5. JSON Output Format
Return ONLY valid JSON.

```json
{
  "global_style": {
    "color_scheme": "Describe the color usage (e.g. 'Standard shadcn zinc theme')",
    "style_description": "Brief description of the visual style. ALWAYS mention using shadcn/ui components."
  },
  "files": [
    {
      "path": "src/components",
      "filename": "UserProfile.tsx",
      "functions": [
        {"name": "UserProfile", "description": "Displays user info card"}
      ],
      "dependencies": [
        {
          "from_path": "@/components/ui/card",
          "imports": [
            {"name": "Card", "description": "Container"},
            {"name": "CardHeader", "description": "Header"}
          ]
        },
        {
          "from_path": "@/components/ui/button",
          "imports": [{"name": "Button", "description": "Edit action"}]
        },
        {
          "from_path": "lucide-react",
          "imports": [{"name": "User", "description": "Icon"}]
        }
      ],
      "props": "interface UserProfileProps { name: string; email: string; }"
    }
  ]
}
```
"""

async def process_chat(instructions: str, session_id: str = None):
    if not settings.GEMINI_API_KEY:
        return {
            "type": "error",
            "content": "GEMINI_API_KEY is not set.",
            "session_id": session_id
        }

    if not session_id:
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = []

    history = chat_sessions.get(session_id, [])
    
    # Initialize model
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT
    )
    
    # Start chat with history
    chat = model.start_chat(history=history)
    
    try:
        response = chat.send_message(instructions)
        
        # Update history
        chat_sessions[session_id].append({"role": "user", "parts": [instructions]})
        chat_sessions[session_id].append({"role": "model", "parts": [response.text]})
        
        response_text = response.text.strip()
        
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

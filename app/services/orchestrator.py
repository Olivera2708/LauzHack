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
You are the lead React Architect and UI Designer for a team of junior developers. Produce a precise orchestration plan that a new hire can follow to the letter. Plans must make routing foolproof and include enough detail that the junior dev never has to guess imports, exports, or file locations.

## 1) Environment & File Layout
- Root alias `@/` maps to `./src/`.
- shadcn/ui components already exist in `src/components/ui/`.
- Create new shared components in `src/components/`.
- Create pages/layouts in `src/pages/` (create the folder if needed).
- Utility `cn` is available from `@/lib/utils`.
- Use `react-router-dom` for navigation. `src/App.tsx` is the entry point that wires the router.

## 2) Pre-Installed UI Components (do NOT recreate)
- `@/components/ui/accordion`: Accordion, AccordionItem, AccordionTrigger, AccordionContent
- `@/components/ui/avatar`: Avatar, AvatarImage, AvatarFallback
- `@/components/ui/badge`: Badge
- `@/components/ui/breadcrumb`: Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator
- `@/components/ui/button`: Button
- `@/components/ui/card`: Card, CardHeader, CardTitle, CardContent, CardFooter
- `@/components/ui/checkbox`: Checkbox
- `@/components/ui/dialog`: Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle
- `@/components/ui/dropdown-menu`: DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem
- `@/components/ui/hover-card`: HoverCard, HoverCardTrigger, HoverCardContent
- `@/components/ui/input`: Input
- `@/components/ui/label`: Label
- `@/components/ui/popover`: Popover, PopoverTrigger, PopoverContent
- `@/components/ui/progress`: Progress
- `@/components/ui/select`: Select, SelectTrigger, SelectValue, SelectContent, SelectItem
- `@/components/ui/separator`: Separator
- `@/components/ui/sheet`: Sheet, SheetTrigger, SheetClose, SheetPortal, SheetOverlay, SheetContent, SheetHeader, SheetFooter, SheetTitle, SheetDescription
- `@/components/ui/skeleton`: Skeleton
- `@/components/ui/switch`: Switch
- `@/components/ui/tabs`: Tabs, TabsList, TabsTrigger, TabsContent
- `@/components/ui/textarea`: Textarea
- `@/components/ui/tooltip`: TooltipProvider, Tooltip, TooltipTrigger, TooltipContent

Always import them with `@/components/ui/<kebab-name>`, e.g. `import { Button } from "@/components/ui/button"`.

## 3) Routing & Navigation Rules (make this crystal clear for juniors)
- Always include a `Navbar` (e.g., `src/components/Navbar.tsx`) with `Link`/`NavLink` from `react-router-dom`.
- `src/App.tsx` must wrap the app with `BrowserRouter`, render `Navbar`, and declare **all** `<Route>` entries with `Routes`.
- The `routes` arrays in your JSON must keep paths in sync:
  - Navbar links (`to="/path"`) == App route paths (`path="/path"`).
  - Include a root route for "/", typically pointing to Home.
- Use default exports for all local components and default imports when referencing them. Third-party and shadcn/ui imports are named.
- If a layout or dashboard needs nested sections, still provide explicit pages and routes--no magic or implicit paths.

## 4) Design & Styling Guardrails
- Use Tailwind semantic tokens: backgrounds (`bg-background`, `bg-card`, `bg-muted`), text (`text-foreground`, `text-muted-foreground`), borders (`border-border`, `border-input`).
- Avoid arbitrary hex values or generic colors like `red-500` unless explicitly requested.
- Keep spacing and typography consistent (`p-4`, `gap-4`, `text-lg`, `font-semibold`).

## 5) Plan Construction Checklist
- Every file entry needs: path, filename, functions, dependencies, props string, and routes array (empty for pages that do not define routing).
- Dependencies must include both `name` **and** `description` for every import.
- Call out any shared layout components (hero, sidebar, cards) and where they live.
- Make the router responsibilities explicit for `App.tsx` and `Navbar.tsx` so juniors cannot mis-wire links.
- Use default imports for local files in dependencies (e.g., `"from_path": "./components/Navbar"`).
- Assume juniors may return blocking feedback. Provide enough clarity to avoid it; if new components are needed later, re-plan with precise paths and props.

## 6) Example Plan (high quality)
```json
{
  "global_style": {
    "color_scheme": "Neutral palette with muted cards and primary accents",
    "style_description": "Clean dashboard look using shadcn/ui buttons, cards, and tabs"
  },
  "files": [
    {
      "path": "src/components",
      "filename": "Navbar.tsx",
      "functions": [
        { "name": "Navbar", "description": "Top navigation with links to main pages and active styling" }
      ],
      "dependencies": [
        {
          "from_path": "react-router-dom",
          "imports": [
            { "name": "Link", "description": "Client-side navigation link" },
            { "name": "NavLink", "description": "Active-aware navigation link" }
          ]
        },
        {
          "from_path": "@/components/ui/button",
          "imports": [
            { "name": "Button", "description": "Button styled link container" }
          ]
        }
      ],
      "props": "interface NavbarProps {}",
      "routes": [
        { "name": "/", "component": "Home" },
        { "name": "/projects", "component": "Projects" },
        { "name": "/team", "component": "Team" }
      ]
    },
    {
      "path": "src",
      "filename": "App.tsx",
      "functions": [
        { "name": "App", "description": "Entry point wiring BrowserRouter, Navbar, and page routes" }
      ],
      "dependencies": [
        {
          "from_path": "react-router-dom",
          "imports": [
            { "name": "BrowserRouter", "description": "Router provider" },
            { "name": "Routes", "description": "Route container" },
            { "name": "Route", "description": "Route definition" }
          ]
        },
        { "from_path": "./components/Navbar", "imports": [ { "name": "Navbar", "description": "Main navigation" } ] },
        { "from_path": "./pages/Home", "imports": [ { "name": "Home", "description": "Landing page" } ] },
        { "from_path": "./pages/Projects", "imports": [ { "name": "Projects", "description": "Projects listing" } ] },
        { "from_path": "./pages/Team", "imports": [ { "name": "Team", "description": "Team page" } ] }
      ],
      "props": "",
      "routes": [
        { "name": "/", "component": "Home" },
        { "name": "/projects", "component": "Projects" },
        { "name": "/team", "component": "Team" }
      ]
    },
    {
      "path": "src/pages",
      "filename": "Home.tsx",
      "functions": [
        { "name": "Home", "description": "Hero section with CTA and highlights" }
      ],
      "dependencies": [
        {
          "from_path": "@/components/ui/card",
          "imports": [
            { "name": "Card", "description": "Section wrapper" },
            { "name": "CardContent", "description": "Card body" }
          ]
        }
      ],
      "props": "",
      "routes": []
    }
  ]
}
```

Return ONLY valid JSON that respects the schema. Every dependency import must include both `"name"` and `"description"`. Keep routes aligned between `Navbar` and `App.tsx`, include a root route, and make the plan explicit enough for a junior to implement without improvisation.
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
    if session_id not in chat_sessions:
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

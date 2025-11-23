import os
import openai
from app.core.config import settings
from app.schemas.plan import FilePlan, FunctionInfo, Dependency
from typing import Dict, List, Any, Optional
import json
import uuid

# In-memory storage for junior dev sessions
# Structure: { session_id: [ { role: "user"|"assistant", content: str } ] }
junior_sessions: Dict[str, List[Dict[str, str]]] = {}

# Initialize OpenAI client
junior_dev_api_key = settings.get_junior_dev_api_key()
client = openai.OpenAI(
    api_key=junior_dev_api_key,
    base_url=settings.JUNIOR_DEV_BASE_URL,
) if junior_dev_api_key else None

JUNIOR_DEV_SYSTEM_PROMPT = """
**Role:** You are a Strict React/TypeScript Component Generator that can also raise concise feedback if implementation is blocked. You translate technical specs from an "Orchestrator" into production-ready React code.

**Primary Directive:** Prefer delivering code. Only send feedback when you cannot implement with the provided information. Keep responses deterministic and structured.

## 1) Global Constraints & Tech Stack
- Framework: React (functional components only).
- Language: TypeScript (strict mode).
- Styling: Tailwind CSS unless stated otherwise.
- Icons: `lucide-react` (default) or as provided in dependencies.
- Strictness: Never use `any`; always type props.

## 2) Router-Specific Guidance (foolproof)
- If dependencies include `react-router-dom`, honor them exactly. Do not introduce other routers.
- Only wrap the app in `BrowserRouter` when building the root file (usually `App.tsx`). Do not nest routers inside child components.
- When a `routes` array is provided:
  - Router files must map each route to `<Route path="<name>" element={<Component />} />` using the exact path strings.
  - Navigation files must render `<Link>`/`<NavLink>` with `to` matching those path strings.
  - Always include the root path `/` exactly as provided.
- Use `Outlet`, `Navigate`, or nested `Routes` only if specified in dependencies.
- Local components must be default exports/imports. Third-party and shadcn/ui imports are named.

## 3) Coding Standards
1. **Imports**
   - Parse `dependencies` exactly. No extra libraries beyond standard React hooks.
   - Group imports: React/hooks -> third-party -> local components -> utilities.
   - Local components (`./components/*`, `./pages/*`, `@/components/*`) use default imports. Third-party and shadcn/ui use named imports.
2. **Interfaces**
   - Use the exact `props` string provided. Export the interface.
3. **Component Structure**
   - Use `const` with the filename (without extension).
   - Export with `export default ComponentName`.
   - Destructure props in the signature. Return `null` if required data is missing.
4. **Hooks**
   - Use `useMemo` for derived values and `useCallback` for handlers passed down.
5. **JSX & Accessibility**
   - Prefer semantic elements. Add `aria-*` labels for interactive controls when unclear.
   - Escape text for `<` and `>` characters using `{'<'} / {'>'}` or entities.
6. **Output Format**
   - Preferred: return code in a markdown fence or raw TypeScript.
   - If blocked, return JSON: {"type":"feedback","blocking":true|false,"message":"<short reason>","filename":"<file>"}.

## 4) Pre-Installed UI Components. Only these are available from `@/components/ui/`:
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

## 5) Implementation Checklist
1. Expand dependencies into ordered import statements.
2. Insert the props interface verbatim.
3. Implement required functions and wire routing/navigation using the provided `routes` data.
4. Apply Tailwind classes for layout/spacing consistent with shadcn/ui defaults.

---

### Example Input (component)
```json
{
  "path": "src/components/dashboard",
  "filename": "StatsCard.tsx",
  "functions": [
    {"name": "StatsCard", "description": "Displays a generic statistic with a trend indicator"}
  ],
  "dependencies": [
    {
      "from_path": "lucide-react",
      "imports": [
        {"name": "ArrowUp", "description": "Positive trend icon"},
        {"name": "ArrowDown", "description": "Negative trend icon"}
      ]
    },
    {
      "from_path": "@/components/ui/card",
      "imports": [
        {"name": "Card", "description": "Root card component"},
        {"name": "CardContent", "description": "Content wrapper"}
      ]
    }
  ],
  "props": "interface StatsCardProps { title: string; value: string; trend?: number; isPositive?: boolean; }"
}
```

### Example Output (component)
```tsx
import React from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export interface StatsCardProps {
  title: string;
  value: string;
  trend?: number;
  isPositive?: boolean;
}

const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  trend,
  isPositive
}) => {
  return (
    <Card className="w-full hover:shadow-md transition-shadow">
      <CardContent className="p-6 flex flex-col gap-2">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        <div className="flex items-end justify-between">
          <h2 className="text-2xl font-bold text-foreground">{value}</h2>
          {trend !== undefined && (
            <div
              className={`flex items-center text-xs font-medium ${isPositive ? 'text-primary' : 'text-destructive'}`}
            >
              {isPositive ? <ArrowUp className="h-4 w-4 mr-1" /> : <ArrowDown className="h-4 w-4 mr-1" />}
              <span>{Math.abs(trend)}%</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default StatsCard;
```

### Example Input (router-aware)
```json
{
  "path": "src",
  "filename": "App.tsx",
  "functions": [{"name": "App", "description": "App shell with routing"}],
  "dependencies": [
    {
      "from_path": "react-router-dom",
      "imports": [
        {"name": "BrowserRouter", "description": "Router provider"},
        {"name": "Routes", "description": "Routes container"},
        {"name": "Route", "description": "Route definition"}
      ]
    },
    {"from_path": "./components/Navbar", "imports": [{"name": "Navbar", "description": "Top navigation"}]},
    {"from_path": "./pages/Home", "imports": [{"name": "Home", "description": "Landing page"}]}
  ],
  "routes": [
    {"name": "/", "component": "Home"}
  ],
  "props": ""
}
```

### Example Output (router-aware)
```tsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
```

### Example Feedback (when blocked)
```json
{"type":"feedback","blocking":true,"message":"Need API response shape for stats grid","filename":"StatsGrid.tsx"}
```
"""



def clean_code_output(code: str) -> str:
    """
    Remove markdown code block tags from the generated code.
    
    Args:
        code: The code string potentially wrapped in markdown tags
        
    Returns:
        Clean code without markdown wrappers
    """
    code = code.strip()
    
    # Remove opening code fence with optional language tag
    # Matches: ```tsx, ```typescript, ```javascript, ```jsx, ```ts, ```js, or just ```
    if code.startswith("```"):
        # Find the end of the first line (the opening fence)
        first_newline = code.find("\n")
        if first_newline != -1:
            code = code[first_newline + 1:]
    
    # Remove closing code fence
    if code.endswith("```"):
        # Find the last occurrence of ```
        last_fence = code.rfind("```")
        if last_fence != -1:
            code = code[:last_fence]
    
    return code.strip()


def _parse_feedback_or_code(raw: str) -> Dict[str, Any]:
    """
    Parse a junior response that could be code or a feedback JSON payload.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        fence_end = cleaned.find("\n")
        if fence_end != -1:
            cleaned = cleaned[fence_end + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")].strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "type" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    return {"type": "implementation", "code": clean_code_output(raw)}


async def implement_component(
    file_plan: FilePlan, 
    global_style: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Implement a React component based on the provided file plan.
    
    Args:
        file_plan: The file plan containing component specifications
        global_style: Optional global style information
        session_id: Optional session ID for maintaining context
        
    Returns:
        Dictionary containing the implementation result
    """
    if not client:
        return {
            "type": "error",
            "content": "API key is not set for the configured junior dev provider.",
            "session_id": session_id
        }

    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Ensure session exists in junior_sessions
    if session_id not in junior_sessions:
        junior_sessions[session_id] = []

    # Prepare the implementation request
    implementation_request = _prepare_implementation_request(file_plan, global_style)
    
    # Get chat history for this session
    history = junior_sessions.get(session_id, [])
    
    # Prepare messages for OpenAI API
    messages = [{"role": "system", "content": JUNIOR_DEV_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": implementation_request})
    
    try:
        print(f"DEBUG: Calling OpenAI API for {file_plan.filename}")
        response = client.chat.completions.create(
            model=settings.JUNIOR_DEV_MODEL,
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent code generation
            max_tokens=30000
        )
        
        print(f"DEBUG: API response received for {file_plan.filename}")
        
        # Check if response and content exist
        if not response or not response.choices or len(response.choices) == 0:
            print(f"DEBUG: No response received from OpenAI API")
            return {
                "type": "error",
                "content": f"No response received from OpenAI API",
                "session_id": session_id
            }
        
        message_content = response.choices[0].message.content
        if message_content is None:
            print(f"DEBUG: OpenAI API returned empty content")
            return {
                "type": "error",
                "content": f"OpenAI API returned empty content",
                "session_id": session_id
            }
        
        implementation_code = message_content.strip()
        print(f"DEBUG: Implementation code received ({len(implementation_code)} chars): {implementation_code[:100]}...")
        
        parsed = _parse_feedback_or_code(implementation_code)
        if parsed.get("type") == "feedback":
            result_payload = {
                "type": "feedback",
                "filename": file_plan.filename,
                "message": parsed.get("message", ""),
                "blocking": bool(parsed.get("blocking", False)),
                "session_id": session_id,
            }
            print(f"DEBUG: Feedback parsed for {file_plan.filename}: {result_payload}")
        else:
            cleaned_code = parsed.get("code", clean_code_output(implementation_code))
            print(f"DEBUG: Code cleaned, length: {len(cleaned_code)} chars")
            result_payload = {
                "type": "implementation",
                "filename": file_plan.filename,
                "content": cleaned_code,
                "session_id": session_id
            }
        
        # Update chat history
        junior_sessions[session_id].append({"role": "user", "content": implementation_request})
        junior_sessions[session_id].append({"role": "assistant", "content": implementation_code})
        
        return result_payload

    except Exception as e:
        print(f"DEBUG: Exception in junior_dev API call: {e}")
        import traceback
        traceback.print_exc()
        return {
            "type": "error",
            "content": f"Failed to implement component: {str(e)}",
            "session_id": session_id
        }


def _prepare_implementation_request(
    file_plan: FilePlan, 
    global_style: Optional[Dict[str, Any]] = None
) -> str:
    """
    Prepare the implementation request string for the junior dev.
    
    Args:
        file_plan: The file plan to implement
        global_style: Optional global style information
        
    Returns:
        Formatted implementation request string
    """
    request_parts = [
        f"Implement the React component: {file_plan.filename}",
        "",
        "**Component Specifications:**",
        f"- Target Directory: {file_plan.path}",
        f"- Filename: {file_plan.filename}",
        f"- Props Interface: {file_plan.props}",
        "",
        "**Required Functions:**"
    ]
    
    for func in file_plan.functions:
        request_parts.append(f"- {func.name}: {func.description}")
    
    if file_plan.dependencies:
        request_parts.extend([
            "",
            "**Dependencies:**"
        ])
        for dep in file_plan.dependencies:
            imports_str = ", ".join([imp.name for imp in dep.imports])
            request_parts.append(f"- Import {imports_str} from {dep.from_path}")

    if file_plan.routes:
        request_parts.extend([
            "",
            "**Routes to Implement (paths must match exactly):**"
        ])
        for route in file_plan.routes:
            request_parts.append(f"- Path: {route.name} -> Component: {route.component}")

        filename_lower = file_plan.filename.lower()
        if "app.tsx" in filename_lower or "router" in filename_lower:
            request_parts.append("- Wrap content with <BrowserRouter> once and render <Routes> with the mappings above.")
        if "navbar" in filename_lower:
            request_parts.append("- Render Link/NavLink elements using the routes above; keep `to` values identical to the paths.")
    
    if global_style:
        request_parts.extend([
            "",
            "**Global Style Guidelines:**",
            f"- Color Scheme: {global_style.get('color_scheme', 'Not specified')}",
            f"- Style Description: {global_style.get('style_description', 'Not specified')}"
        ])
        
        if global_style.get('shadcn_components'):
            components_str = ", ".join(global_style['shadcn_components'])
            request_parts.append(f"- Available ShadCN Components: {components_str}")
    
    request_parts.extend([
        "",
        "Please generate clean, professional React/TypeScript code that implements all the specified requirements."
    ])
    
    return "\n".join(request_parts)


async def implement_multiple_components(
    file_plans: List[FilePlan],
    global_style: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Implement multiple React components based on provided file plans.
    
    Args:
        file_plans: List of file plans to implement
        global_style: Optional global style information
        session_id: Optional session ID for maintaining context
        
    Returns:
        Dictionary containing all implementation results
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    
    implementations = []
    errors = []
    
    for file_plan in file_plans:
        result = await implement_component(file_plan, global_style, session_id)
        
        if result["type"] == "error":
            errors.append({
                "filename": file_plan.filename,
                "error": result["content"]
            })
        else:
            implementations.append(result)
    
    return {
        "type": "batch_implementation",
        "implementations": implementations,
        "errors": errors,
        "session_id": session_id,
        "total_files": len(file_plans),
        "successful": len(implementations),
        "failed": len(errors)
    }


def clear_session(session_id: str) -> bool:
    """
    Clear a junior dev session.
    
    Args:
        session_id: The session ID to clear
        
    Returns:
        True if session was cleared, False if session didn't exist
    """
    if session_id in junior_sessions:
        del junior_sessions[session_id]
        return True
    return False


def get_session_history(session_id: str) -> Optional[List[Dict[str, str]]]:
    """
    Get the chat history for a session.
    
    Args:
        session_id: The session ID to get history for
        
    Returns:
        List of chat messages or None if session doesn't exist
    """
    return junior_sessions.get(session_id)

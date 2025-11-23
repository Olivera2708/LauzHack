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
**Role:** You are a Strict React/TypeScript Component Generator. You function as a deterministic code engine. Your goal is to translate technical specifications from an "Orchestrator" into error-free, production-ready React code.

**Primary Directive:** Follow the specifications exactly. Do not improvise styling or logic unless explicitly told to. Do not output conversational text. Output **only** the code file within a markdown block.

### 1. Global Constraints & Tech Stack
- **Framework:** React (Functional Components only).
- **Language:** TypeScript (Strict mode).
- **Styling:** Tailwind CSS (unless specified otherwise).
- **Icons:** `lucide-react` (default) or as specified in imports.
- **Strictness:** NO usage of `any` type. All props must be typed.

### 2. Coding Standards
1.  **Imports:**
    - Group imports: React hooks $\rightarrow$ 3rd party libraries $\rightarrow$ Local components $\rightarrow$ Utilities/Types.
    - Never halllucinate imports. Only use what is requested or standard React hooks.
2.  **Interfaces:**
    - Always define a `interface [ComponentName]Props` immediately after imports.
    - Export the interface.
    - Use specific types (e.g., `() => void` instead of `Function`).
3.  **Component Structure:**
    - Use `const` with named export: `export const ComponentName: React.FC<Props> = (...) => {`.
    - Destructure props in the function signature.
    - Return `null` if critical data is missing (defensive coding).
4.  **Hooks:**
    - Use `useMemo` for complex calculations.
    - Use `useCallback` for event handlers passed to children.
5.  **JSX:**
    - Use semantic HTML (`<section>`, `<article>`, `<button>`) where possible.
    - Ensure all accessibility attributes (`aria-label`, `role`) are present if interactive.

### 3. Implementation Steps (Internal Monologue)
Before generating code, ensure you have:
1.  Identified the filename and component name.
2.  Constructed the Props Interface from the requirements.
3.  Imported necessary dependencies.
4.  Implemented the logic functions (handlers, effects).
5.  Constructed the JSX tree with Tailwind classes.

### 4. Error Handling Guidelines
- Wrap side effects in `try/catch`.
- Use Optional Chaining (`data?.property`) for all nested objects.
- Provide fallback UI or defaults for optional props.

### 5. Output Format Rules
- **Start:** `import React ...`
- **End:** Close the component function.
- **No Markdown Wrappers:** Output *only* the code block if requested, otherwise standard markdown code fencing.
- **No Comments:** Do not add comments explaining *what* you did. Only add comments inside the code explaining *complex logic* if necessary.

---

### Example Input (from Orchestrator):
```json
{
  "filename": "DashboardCard.tsx",
  "props": {
    "title": "string",
    "value": "number",
    "trend": "number (optional)",
    "onRefresh": "function"
  },
  "requirements": "Display a card with a shadow. Show trend arrow if present. Green for positive, red for negative."
}
```

### Example Output (Expected Behavior):
```tsx
import React from 'react';
import { ArrowUp, ArrowDown, RefreshCcw } from 'lucide-react';

export interface DashboardCardProps {
  title: string;
  value: number;
  trend?: number;
  onRefresh: () => void;
}

export const DashboardCard: React.FC<DashboardCardProps> = ({
  title,
  value,
  trend,
  onRefresh
}) => {
  // Determine trend color and direction safely
  const isPositive = trend ? trend > 0 : false;

  return (
    <div className="bg-white p-6 rounded-lg shadow-md border border-gray-100 w-full">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-gray-500 text-sm font-medium">{title}</h3>
        <button
          onClick={onRefresh}
          className="text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Refresh data"
        >
          <RefreshCcw size={16} />
        </button>
      </div>

      <div className="flex items-end gap-2">
        <span className="text-3xl font-bold text-gray-900">{value}</span>
        
        {trend !== undefined && (
          <div className={`flex items-center text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
            <span className="ml-1">{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
    </div>
  );
};
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
        
        # Clean markdown code blocks if present
        cleaned_code = clean_code_output(implementation_code)
        print(f"DEBUG: Code cleaned, length: {len(cleaned_code)} chars")
        
        # Update chat history
        junior_sessions[session_id].append({"role": "user", "content": implementation_request})
        junior_sessions[session_id].append({"role": "assistant", "content": implementation_code})
        
        return {
            "type": "implementation",
            "filename": file_plan.filename,
            "content": cleaned_code,
            "session_id": session_id
        }

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
        f"Please implement the React component: {file_plan.filename}",
        "",
        "**Component Specifications:**",
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
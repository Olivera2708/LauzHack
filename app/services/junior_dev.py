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

# Initialize OpenAI client for Together.ai
client = openai.OpenAI(
    api_key=os.environ.get("TOGETHER_API_KEY"),
    base_url="https://api.together.xyz/v1",
) if settings.TOGETHER_API_KEY else None

JUNIOR_DEV_SYSTEM_PROMPT = """
You are a skilled Junior React Developer. Your role is to implement React components based on detailed specifications provided by the orchestrator.

Your responsibilities:
1. **Analyze the Component Specification**: Carefully read the file plan including filename, functions, dependencies, and props.
2. **Generate Clean Code**: Write professional, readable React/TypeScript code following best practices.
3. **Handle Dependencies**: Properly import and use dependencies as specified.
4. **Implement Functions**: Create all specified functions with appropriate logic.
5. **Use Props Interface**: Implement the provided props interface correctly.

**Output Format**:
- Always output valid React/TypeScript code
- Include proper imports at the top
- Use functional components with TypeScript
- Follow modern React patterns (hooks, etc.)
- Add brief comments for complex logic
- Ensure code is production-ready

**Code Style**:
- Use TypeScript interfaces for props
- Use arrow functions for components
- Use proper naming conventions (PascalCase for components, camelCase for functions)
- Include proper error handling where appropriate
"""


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
            "content": "TOGETHER_API_KEY is not set.",
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
        print(f"DEBUG: Calling Together.ai API for {file_plan.filename}")
        response = client.chat.completions.create(
            model=settings.JUNIOR_MODEL,
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent code generation
            max_tokens=3000
        )
        
        print(f"DEBUG: API response received for {file_plan.filename}")
        
        # Check if response and content exist
        if not response or not response.choices or len(response.choices) == 0:
            print(f"DEBUG: No response received from Together.ai API")
            return {
                "type": "error",
                "content": f"No response received from Together.ai API",
                "session_id": session_id
            }
        
        message_content = response.choices[0].message.content
        if message_content is None:
            print(f"DEBUG: Together.ai API returned empty content")
            return {
                "type": "error",
                "content": f"Together.ai API returned empty content",
                "session_id": session_id
            }
        
        implementation_code = message_content.strip()
        print(f"DEBUG: Implementation code received ({len(implementation_code)} chars): {implementation_code[:100]}...")
        
        # Update chat history
        junior_sessions[session_id].append({"role": "user", "content": implementation_request})
        junior_sessions[session_id].append({"role": "assistant", "content": implementation_code})
        
        return {
            "type": "implementation",
            "filename": file_plan.filename,
            "content": implementation_code,
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
            imports_str = ", ".join(dep.imports)
            request_parts.append(f"- Import {imports_str} from {dep.filename}")
    
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
import os
import openai
from app.core.config import settings
from app.schemas.plan import OrchestrationPlan
import json
import uuid
from typing import Dict, List, Any

# In-memory storage for chat history
# Structure: { session_id: [ { role: "user"|"assistant", content: str } ] }
chat_sessions: Dict[str, List[Dict[str, str]]] = {}

# Initialize OpenAI client for Gemini via OpenAI API
client = openai.OpenAI(
    api_key=settings.GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
) if settings.GEMINI_API_KEY else None

SYSTEM_PROMPT = """
You are an expert React Architect. Your goal is to gather requirements for a React web application and then generate a detailed orchestration plan.

1.  **Analyze the Request**: Carefully read the user's instructions.
2.  **Clarify**: If the request is vague, missing critical details (e.g., purpose, target audience, specific features, style preferences), or if you need more context to build a solid plan, ASK clarifying questions. Do NOT generate the plan yet.
3.  **Plan**: Once you have sufficient information and the user has answered your questions, generate a JSON object representing the orchestration plan.

**Output Format**:
- If you are asking questions, output plain text.
- If you are generating the plan, output ONLY valid JSON matching the following structure:
{
  "global_style": {
    "color_scheme": "...",
    "shadcn_components": ["Button", "Card", ...],
    "style_description": "..."
  },
  "files": [
    {
      "filename": "ComponentName.tsx",
      "functions": [{"name": "funcName", "description": "..."}],
      "dependencies": [{"filename": "OtherComponent.tsx", "imports": ["funcName"]}],
      "props": "interface Props { ... }"
    }
  ]
}
"""

def _fix_common_json_issues(json_str: str) -> str:
    """
    Attempt to fix common JSON syntax issues that might occur in LLM responses.
    
    Args:
        json_str: The potentially malformed JSON string
        
    Returns:
        Fixed JSON string
    """
    # Remove any trailing commas before closing braces/brackets
    import re
    
    # Fix trailing commas before closing braces
    json_str = re.sub(r',(\s*})', r'\1', json_str)
    
    # Fix trailing commas before closing brackets
    json_str = re.sub(r',(\s*])', r'\1', json_str)
    
    # Fix missing commas between object properties (basic heuristic)
    # This is more complex and might need refinement
    json_str = re.sub(r'"\s*\n\s*"', r'",\n    "', json_str)
    
    # Fix missing commas between array elements
    json_str = re.sub(r'}\s*\n\s*{', r'},\n    {', json_str)
    
    # Fix null props values - replace with empty strings
    json_str = re.sub(r'"props":\s*null', r'"props": ""', json_str)
    
    return json_str

async def process_chat(instructions: str, session_id: str = None) -> Dict[str, Any]:
    """
    Process chat instructions using OpenAI API with Gemini model.
    
    Args:
        instructions: User instructions for the React application
        session_id: Optional session ID for maintaining chat history
        
    Returns:
        Dictionary containing response type, content, and session_id
    """
    if not client:
        return {
            "type": "error",
            "content": "GEMINI_API_KEY is not set.",
            "session_id": session_id
        }

    if not session_id:
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = []

    # Get chat history for this session
    history = chat_sessions.get(session_id, [])
    
    # Prepare messages for OpenAI API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": instructions})
    
    try:
        response = client.chat.completions.create(
            model=settings.ORCHESTRATOR_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        
        # Check if response and content exist
        if not response or not response.choices or len(response.choices) == 0:
            return {
                "type": "error",
                "content": "No response received from Gemini API",
                "session_id": session_id
            }
        
        message_content = response.choices[0].message.content
        if message_content is None:
            return {
                "type": "error",
                "content": "Gemini API returned empty content. This might be due to incorrect API endpoint or model configuration.",
                "session_id": session_id
            }
        
        response_text = message_content.strip()
        
        # Update chat history
        chat_sessions[session_id].append({"role": "user", "content": instructions})
        chat_sessions[session_id].append({"role": "assistant", "content": response_text})
        
        # Try to parse as JSON to see if it's the plan
        try:
            # Find JSON start and end if mixed with text (though prompt says ONLY JSON)
            if "{" in response_text and "}" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_str = response_text[start:end]
                print(f"DEBUG: Extracted JSON string (first 200 chars): {json_str[:200]}...")
                
                # Try to fix common JSON issues
                json_str = _fix_common_json_issues(json_str)
                
                plan_data = json.loads(json_str)
                print(f"DEBUG: JSON parsing successful, keys: {list(plan_data.keys())}")
                # Validate with Pydantic
                plan = OrchestrationPlan(**plan_data)
                print(f"DEBUG: Pydantic validation successful")
                return {
                    "type": "plan",
                    "content": plan,
                    "session_id": session_id
                }
            else:
                print(f"DEBUG: No JSON braces found in response")
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON decode error: {e}")
            print(f"DEBUG: Problematic JSON around error: {json_str[max(0, e.pos-50):e.pos+50]}")
            # Return error with more details
            return {
                "type": "error",
                "content": f"Gemini generated malformed JSON: {str(e)}. Please try again.",
                "session_id": session_id
            }
        except ValueError as e:
            print(f"DEBUG: Pydantic validation error: {e}")
            return {
                "type": "error", 
                "content": f"Generated plan doesn't match expected schema: {str(e)}",
                "session_id": session_id
            }
        except Exception as e:
            print(f"DEBUG: Unexpected error during JSON parsing: {e}")
            import traceback
            traceback.print_exc()
            return {
                "type": "error",
                "content": f"Unexpected error processing plan: {str(e)}",
                "session_id": session_id
            }
            
        # If not JSON, it's a question/text response
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

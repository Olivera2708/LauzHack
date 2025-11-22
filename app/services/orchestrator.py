import google.generativeai as genai
from app.core.config import settings
from app.schemas.plan import OrchestrationPlan
import json
import uuid

# In-memory storage for chat history
# Structure: { session_id: [ { role: "user"|"model", parts: [...] } ] }
chat_sessions = {}

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

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
        
        # Update our local history (Gemini object manages its own, but we might want to persist it later)
        # For now, relying on the chat object's state within the scope if we kept it alive, 
        # but since we recreate the model/chat each time (stateless service), we need to pass history.
        # Actually, `start_chat(history=...)` expects a specific format.
        # Let's update our stored history.
        chat_sessions[session_id].append({"role": "user", "parts": [instructions]})
        chat_sessions[session_id].append({"role": "model", "parts": [response.text]})
        
        response_text = response.text.strip()
        
        # Try to parse as JSON to see if it's the plan
        try:
            # Find JSON start and end if mixed with text (though prompt says ONLY JSON)
            if "{" in response_text and "}" in response_text:
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
        except (json.JSONDecodeError, ValueError):
            pass
            
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

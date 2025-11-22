from fastapi import APIRouter, Body
from app.services.orchestrator import process_chat
from app.schemas.plan import ChatResponse

router = APIRouter()

@router.post("/process", response_model=ChatResponse)
async def process_instructions(
    instructions: str = Body(..., embed=True),
    session_id: str = Body(None, embed=True)
):
    """
    Endpoint to receive instructions and return them.
    """
    result = await process_chat(instructions, session_id)
    return result


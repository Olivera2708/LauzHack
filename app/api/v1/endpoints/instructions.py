from fastapi import APIRouter, Body

router = APIRouter()

@router.post("/process")
async def process_instructions(instructions: str = Body(..., embed=True)):
    """
    Endpoint to receive instructions and return them.
    """
    return {
        "instructions": instructions,
        "message": "Instructions received successfully"
    }

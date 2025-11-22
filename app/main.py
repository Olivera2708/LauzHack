from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.endpoints import instructions

app = FastAPI(title=settings.PROJECT_NAME)

# Include routers
app.include_router(
    instructions.router,
    prefix=f"{settings.API_V1_STR}/instructions",
    tags=["instructions"]
)

@app.get("/")
async def root():
    return {"message": "Welcome to LauzHack API"}

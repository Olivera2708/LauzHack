from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints import instructions

app = FastAPI(title=settings.PROJECT_NAME)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    instructions.router,
    prefix=f"{settings.API_V1_STR}/instructions",
    tags=["instructions"]
)

@app.get("/")
async def root():
    return {"message": "Welcome to LauzHack API"}

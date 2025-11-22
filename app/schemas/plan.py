from typing import List, Optional
from pydantic import BaseModel, Field

class FunctionInfo(BaseModel):
    name: str
    description: str

class Dependency(BaseModel):
    filename: str
    imports: List[str]

class FilePlan(BaseModel):
    filename: str
    functions: List[FunctionInfo]
    dependencies: List[Dependency]
    props: str = Field(..., description="Input props of the component")

class GlobalStyle(BaseModel):
    color_scheme: str
    shadcn_components: List[str]
    style_description: str

class OrchestrationPlan(BaseModel):
    global_style: GlobalStyle
    files: List[FilePlan]

class ChatResponse(BaseModel):
    type: str = Field(..., description="'question' or 'plan'")
    content: str | OrchestrationPlan
    session_id: str

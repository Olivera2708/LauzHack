from typing import List, Optional, Union
from pydantic import BaseModel, Field

class FunctionInfo(BaseModel):
    name: str
    description: str

class Dependency(BaseModel):
    from_path: str = Field(..., description="The path to import from, e.g., '@/components/ui/button'")
    imports: List[FunctionInfo] = Field(..., description="List of functions/components imported with their descriptions")

class Route(BaseModel):
    name: str = Field(..., description="The route name/path, e.g., '/home' or '/dashboard'")
    component: str = Field(..., description="The component (page) that this route opens, e.g., 'Home' or 'Dashboard'")

class FilePlan(BaseModel):
    path: str = Field(..., description="The directory where the file should be created, e.g., 'src/components'")
    filename: str = Field(..., description="The name of the file, e.g., 'Header.tsx'")
    functions: List[FunctionInfo] = Field(..., description="Functions exported by this file")
    dependencies: List[Dependency] = Field(..., description="Components and functions used by this file")
    props: str = Field(..., description="Input props of the component")
    routes: List[Route] = Field(default_factory=list, description="List of routes with their names and associated components (pages)")

class GlobalStyle(BaseModel):
    color_scheme: str
    style_description: str

class OrchestrationPlan(BaseModel):
    global_style: GlobalStyle
    files: List[FilePlan]

class ChatResponse(BaseModel):
    type: str = Field(..., description="'question', 'plan' or 'error'")
    content: Union[str, OrchestrationPlan]
    session_id: str

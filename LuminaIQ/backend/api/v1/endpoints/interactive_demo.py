"""
Interactive Demo API — Generate AI-powered HTML visualizations for topics.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from services.interactive_demo_service import interactive_demo_service
from utils.logger import logger

router = APIRouter()


class GenerateDemoRequest(BaseModel):
    project_id: str
    topic: str = Field(..., min_length=1, max_length=500)
    additional_info: Optional[str] = Field(default="", max_length=2000)
    context_topics: Optional[List[str]] = None


class GenerateDemoResponse(BaseModel):
    html_code: str
    title: str
    description: str


@router.post("/generate", response_model=GenerateDemoResponse)
async def generate_interactive_demo(req: GenerateDemoRequest):
    """Generate a self-contained interactive HTML demo for a learning topic."""
    try:
        result = await interactive_demo_service.generate_demo(
            topic=req.topic,
            additional_info=req.additional_info or "",
            context_topics=req.context_topics,
        )
        return result
    except Exception as e:
        logger.error(f"[InteractiveDemo] Generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate interactive demo: {str(e)}",
        )

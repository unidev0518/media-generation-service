"""Pydantic schemas for generation endpoints."""

import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class GenerationRequest(BaseModel):
    """Request schema for media generation."""

    prompt: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Text prompt for media generation",
        example="A beautiful sunset over the ocean"
    )
    
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional generation parameters",
        example={
            "width": 512,
            "height": 512,
            "num_inference_steps": 50,
            "guidance_scale": 7.5
        }
    )
    
    model: Optional[str] = Field(
        default="stability-ai/stable-diffusion:27b93a2413e7f36cd83da926f3656280b2931564ff050bf9575f1fdf9bcd7478",
        description="Replicate model to use for generation"
    )

    @validator("prompt")
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is not empty after stripping."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()

    @validator("parameters")
    def validate_parameters(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and sanitize parameters."""
        if v is None:
            return {}
        
        # Basic validation for common parameters
        if "width" in v and not isinstance(v["width"], int):
            raise ValueError("Width must be an integer")
        if "height" in v and not isinstance(v["height"], int):
            raise ValueError("Height must be an integer")
        if "num_inference_steps" in v and not isinstance(v["num_inference_steps"], int):
            raise ValueError("num_inference_steps must be an integer")
        if "guidance_scale" in v and not isinstance(v["guidance_scale"], (int, float)):
            raise ValueError("guidance_scale must be a number")
            
        return v


class GenerationResponse(BaseModel):
    """Response schema for media generation."""

    job_id: uuid.UUID = Field(
        description="Unique job identifier"
    )
    
    status: str = Field(
        description="Current job status"
    )
    
    message: str = Field(
        description="Response message",
        example="Job created successfully"
    )
    
    estimated_time: Optional[int] = Field(
        default=None,
        description="Estimated completion time in seconds"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            uuid.UUID: str
        }
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pending",
                "message": "Job created successfully",
                "estimated_time": 30
            }
        } 
"""Replicate API client with retry logic."""

import asyncio
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import get_settings
from app.core.exceptions import ReplicateAPIException


class ReplicateClient:
    """Client for interacting with Replicate API."""

    def __init__(self, api_token: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_token = api_token or settings.REPLICATE_API_TOKEN
        self.base_url = settings.REPLICATE_API_URL
        self.timeout = settings.JOB_TIMEOUT
        
        if not self.api_token:
            raise ValueError("Replicate API token is required")

    @property
    def headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def create_prediction(
        self, 
        model: str, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new prediction on Replicate."""
        url = f"{self.base_url}/predictions"
        payload = {
            "version": model,
            "input": input_data
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url, 
                    headers=self.headers, 
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                error_data = None
                try:
                    error_data = e.response.json()
                except Exception:
                    pass
                    
                raise ReplicateAPIException(
                    f"Failed to create prediction: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_data=error_data,
                )
            except httpx.RequestError as e:
                raise ReplicateAPIException(
                    f"Request failed: {str(e)}",
                    response_data={"error": str(e)},
                )

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Get prediction status and results."""
        url = f"{self.base_url}/predictions/{prediction_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                error_data = None
                try:
                    error_data = e.response.json()
                except Exception:
                    pass
                    
                raise ReplicateAPIException(
                    f"Failed to get prediction: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_data=error_data,
                )
            except httpx.RequestError as e:
                raise ReplicateAPIException(
                    f"Request failed: {str(e)}",
                    response_data={"error": str(e)},
                )

    async def wait_for_completion(
        self, 
        prediction_id: str, 
        max_wait_time: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """Wait for prediction to complete with polling."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            prediction = await self.get_prediction(prediction_id)
            status = prediction.get("status")
            
            if status in ("succeeded", "failed", "canceled"):
                return prediction
                
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > max_wait_time:
                raise ReplicateAPIException(
                    f"Prediction {prediction_id} timed out after {max_wait_time} seconds",
                    response_data={"prediction_id": prediction_id, "timeout": max_wait_time}
                )
                
            await asyncio.sleep(poll_interval)

    async def cancel_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Cancel a running prediction."""
        url = f"{self.base_url}/predictions/{prediction_id}/cancel"

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                error_data = None
                try:
                    error_data = e.response.json()
                except Exception:
                    pass
                    
                raise ReplicateAPIException(
                    f"Failed to cancel prediction: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_data=error_data,
                )
            except httpx.RequestError as e:
                raise ReplicateAPIException(
                    f"Request failed: {str(e)}",
                    response_data={"error": str(e)},
                )

    async def download_output(self, output_url: str) -> bytes:
        """Download the generated media from output URL."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(output_url)
                response.raise_for_status()
                return response.content
                
            except httpx.HTTPStatusError as e:
                raise ReplicateAPIException(
                    f"Failed to download output: {e.response.status_code}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise ReplicateAPIException(
                    f"Download failed: {str(e)}",
                    response_data={"error": str(e)},
                ) 
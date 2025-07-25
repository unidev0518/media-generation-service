"""Replicate API client with retry logic."""

import asyncio
from typing import Any, Dict, Optional
import uuid
import time

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
        
        # Enable mock mode if no API token provided
        self.mock_mode = not self.api_token
        
        if not self.api_token:
            print("⚠️  WARNING: No Replicate API token provided. Running in MOCK MODE.")
            print("   Sign up at https://replicate.com to get a real API token.")

    @property
    def headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }

    async def create_prediction(
        self, 
        model: str, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new prediction on Replicate."""
        if self.mock_mode:
            return await self._mock_create_prediction(model, input_data)
            
        return await self._real_create_prediction(model, input_data)

    async def _mock_create_prediction(
        self, 
        model: str, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock implementation for development."""
        prediction_id = str(uuid.uuid4())
        print(f"🔧 MOCK: Creating prediction {prediction_id}")
        print(f"   Model: {model}")
        print(f"   Input: {input_data}")
        
        return {
            "id": prediction_id,
            "status": "starting",
            "input": input_data,
            "created_at": time.time(),
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def _real_create_prediction(
        self, 
        model: str, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Real implementation using Replicate API."""
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

    async def get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Get prediction status and results."""
        if self.mock_mode:
            return await self._mock_get_prediction(prediction_id)
            
        return await self._real_get_prediction(prediction_id)

    async def _mock_get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Mock implementation that simulates completion."""
        print(f"🔧 MOCK: Getting prediction {prediction_id}")
        
        # Simulate processing time
        await asyncio.sleep(2)
        
        # Generate a mock image URL
        mock_output_url = f"https://via.placeholder.com/512x512/FFB6C1/000000?text=Generated+Image+{prediction_id[:8]}"
        
        return {
            "id": prediction_id,
            "status": "succeeded",
            "output": [mock_output_url],
            "completed_at": time.time(),
        }

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def _real_get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Real implementation using Replicate API."""
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
        if self.mock_mode:
            print(f"🔧 MOCK: Cancelling prediction {prediction_id}")
            return {"id": prediction_id, "status": "canceled"}
            
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
        if self.mock_mode:
            return await self._mock_download_output(output_url)
            
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

    async def _mock_download_output(self, output_url: str) -> bytes:
        """Mock implementation that generates a simple image."""
        print(f"🔧 MOCK: Downloading from {output_url}")
        
        # Generate a simple 1x1 pink PNG (minimal valid PNG)
        pink_png = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D,  # IHDR length
            0x49, 0x48, 0x44, 0x52,  # IHDR
            0x00, 0x00, 0x00, 0x01,  # width: 1
            0x00, 0x00, 0x00, 0x01,  # height: 1
            0x08, 0x02,              # bit depth: 8, color type: 2 (RGB)
            0x00, 0x00, 0x00,        # compression, filter, interlace
            0x90, 0x77, 0x53, 0xDE,  # CRC
            0x00, 0x00, 0x00, 0x0C,  # IDAT length
            0x49, 0x44, 0x41, 0x54,  # IDAT
            0x08, 0x99, 0x01, 0x01, 0x00, 0x00, 0x00, 0xFF,
            0xFF, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,
            0xE2, 0x21, 0xBC, 0x33,  # CRC
            0x00, 0x00, 0x00, 0x00,  # IEND length
            0x49, 0x45, 0x4E, 0x44,  # IEND
            0xAE, 0x42, 0x60, 0x82   # CRC
        ])
        
        return pink_png 
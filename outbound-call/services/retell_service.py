# services/retell_service.py
import httpx # Import httpx instead of requests
import logging
from typing import Dict, Any, Optional
from config.settings import settings
from models.lead_models import RetellCreateCallRequest
import json # Import json for JSON serialization

class RetellService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = settings.retell_base_url
        self.api_key = settings.retell_api_key
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        # Initialize an async HTTP client
        # It's good practice to manage the client's lifecycle (e.g., with a context manager)
        # but for a simple service like this, initializing it in __init__ is often acceptable
        # if the service instance lives for the app's duration.
        self._client = httpx.AsyncClient(headers=self.headers, base_url=self.base_url)
    
    # Add an async method to close the client when the application shuts down
    async def close(self):
        """Closes the httpx AsyncClient session."""
        await self._client.aclose()
        self.logger.info("httpx AsyncClient closed.")

    async def create_call(self, call_request: RetellCreateCallRequest) -> Optional[Dict[str, Any]]:
        """Create a new phone call via Retell API using httpx."""
        try:
            # Get the raw dictionary representation of the Pydantic model
            payload = call_request.model_dump(exclude_none=True)
            
            # Check if retell_llm_dynamic_variables exists and contains custom_data
            if 'retell_llm_dynamic_variables' in payload and \
               'custom_data' in payload['retell_llm_dynamic_variables']:
                
                custom_data_value = payload['retell_llm_dynamic_variables']['custom_data']
                
                # If custom_data is a dict (or anything not a string), convert it to JSON string
                # This handles cases where custom_data might be None, an empty dict, or a populated dict
                if not isinstance(custom_data_value, str):
                    try:
                        payload['retell_llm_dynamic_variables']['custom_data'] = json.dumps(custom_data_value)
                    except TypeError:
                        # Fallback if custom_data is not JSON serializable, send empty JSON string
                        self.logger.warning(f"custom_data is not JSON serializable ({type(custom_data_value)}), sending empty JSON object as string: {custom_data_value}")
                        payload['retell_llm_dynamic_variables']['custom_data'] = "{}"
                
            # httpx.AsyncClient already has base_url configured, so just provide the path
            response = await self._client.post("/v2/create-phone-call", json=payload, timeout=30)
            
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
            
            result = response.json()
            self.logger.info(f"Successfully created call: {result.get('call_id')}")
            return result
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error creating call: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            self.logger.error(f"Network error creating call: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating call: {str(e)}")
            return None
    
    async def get_concurrency(self) -> Optional[Dict[str, Any]]:
        """Get current call concurrency information using httpx."""
        try:
            response = await self._client.get("/get-concurrency", timeout=10)
            
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
            
            result = response.json()
            self.logger.debug(f"Current concurrency: {result}")
            return result
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error getting concurrency: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            self.logger.error(f"Network error getting concurrency: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting concurrency: {str(e)}")
            return None
    
    async def get_call_details(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific call using httpx."""
        try:
            response = await self._client.get(f"/get-call/{call_id}", timeout=10)
            
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
            
            result = response.json()
            self.logger.info(f"Retrieved call details for: {call_id}")
            return result
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error getting call details: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            self.logger.error(f"Network error getting call details: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting call details: {str(e)}")
            return None
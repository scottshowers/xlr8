"""
Model Checker for XLR8 Chat System

Verifies which models are available on the Ollama server.
Provides fallback recommendations if preferred models are unavailable.

Author: HCMPACT
Version: 1.0
"""

import requests
from requests.auth import HTTPBasicAuth
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ModelChecker:
    """
    Checks model availability on Ollama server.
    
    Provides:
    - List of available models
    - Model existence verification
    - Fallback recommendations
    - Connection testing
    """
    
    def __init__(self, 
                 endpoint: str,
                 auth: Optional[Tuple[str, str]] = None,
                 timeout: int = 10):
        """
        Initialize model checker.
        
        Args:
            endpoint: Ollama server URL (e.g., http://178.156.190.64:11435)
            auth: Optional (username, password) tuple
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint.rstrip('/')
        self.auth = auth
        self.timeout = timeout
        
        logger.info(f"Model Checker initialized for {self.endpoint}")
    
    def test_connection(self) -> bool:
        """
        Test if Ollama server is reachable.
        
        Returns:
            True if server responds, False otherwise
        """
        try:
            url = f"{self.endpoint}/api/tags"
            auth = HTTPBasicAuth(*self.auth) if self.auth else None
            
            response = requests.get(
                url,
                auth=auth,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info("Ollama server connection successful")
                return True
            else:
                logger.warning(f"Ollama server returned status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama server at {self.endpoint}")
            return False
            
        except requests.exceptions.Timeout:
            logger.error(f"Connection to Ollama server timed out after {self.timeout}s")
            return False
            
        except Exception as e:
            logger.error(f"Error testing Ollama connection: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """
        Get list of all available models on Ollama server.
        
        Returns:
            List of model names (e.g., ['mistral:7b', 'deepseek-r1:7b'])
            Returns empty list if connection fails
        """
        try:
            url = f"{self.endpoint}/api/tags"
            auth = HTTPBasicAuth(*self.auth) if self.auth else None
            
            response = requests.get(
                url,
                auth=auth,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract model names
            models = []
            if 'models' in data:
                for model_info in data['models']:
                    model_name = model_info.get('name', '')
                    if model_name:
                        models.append(model_name)
            
            logger.info(f"Found {len(models)} models on Ollama server")
            return models
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama server at {self.endpoint}")
            return []
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after {self.timeout}s")
            return []
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from Ollama server: {e}")
            return []
            
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def check_model(self, model_name: str) -> bool:
        """
        Check if a specific model is available.
        
        Args:
            model_name: Name of model to check (e.g., 'mistral:7b')
            
        Returns:
            True if model is available, False otherwise
        """
        available_models = self.list_models()
        
        # Check exact match
        if model_name in available_models:
            logger.info(f"Model {model_name} is available")
            return True
        
        # Check for variants (e.g., 'mistral:7b' vs 'mistral:latest')
        base_name = model_name.split(':')[0]
        for model in available_models:
            if model.startswith(base_name):
                logger.info(f"Model variant {model} found for {model_name}")
                return True
        
        logger.warning(f"Model {model_name} not found")
        return False
    
    def get_fallback_model(self, preferred_model: str) -> Optional[str]:
        """
        Get a fallback model if preferred model is unavailable.
        
        Args:
            preferred_model: Desired model name
            
        Returns:
            Fallback model name or None if no suitable fallback
        """
        available_models = self.list_models()
        
        if not available_models:
            logger.error("No models available for fallback")
            return None
        
        # Define fallback preferences
        fallback_map = {
            'mistral:7b': ['mistral:latest', 'mistral', 'mixtral:8x7b', 'llama2:7b'],
            'deepseek-r1:7b': ['deepseek-r1:latest', 'deepseek-r1', 'mixtral:8x7b', 'mistral:7b'],
            'mixtral:8x7b': ['mixtral:latest', 'mixtral', 'mistral:7b'],
        }
        
        # Get fallback list for preferred model
        fallback_list = fallback_map.get(preferred_model, [])
        
        # Try each fallback in order
        for fallback in fallback_list:
            if fallback in available_models:
                logger.info(f"Using fallback model {fallback} for {preferred_model}")
                return fallback
            
            # Check for variants
            base_name = fallback.split(':')[0]
            for model in available_models:
                if model.startswith(base_name):
                    logger.info(f"Using variant {model} as fallback for {preferred_model}")
                    return model
        
        # Last resort: use first available model
        fallback = available_models[0]
        logger.warning(f"No preferred fallback found, using {fallback}")
        return fallback
    
    def get_model_info(self, model_name: str) -> Optional[dict]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_name: Name of model
            
        Returns:
            Dict with model info or None if not found
        """
        try:
            url = f"{self.endpoint}/api/show"
            auth = HTTPBasicAuth(*self.auth) if self.auth else None
            
            response = requests.post(
                url,
                json={"name": model_name},
                auth=auth,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved info for model {model_name}")
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Model {model_name} not found")
            else:
                logger.error(f"HTTP error getting model info: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None
    
    def verify_models(self, required_models: List[str]) -> dict:
        """
        Verify multiple models and provide status report.
        
        Args:
            required_models: List of model names to check
            
        Returns:
            Dict with:
            - available: List of available models
            - missing: List of missing models
            - fallbacks: Dict of missing models to fallback recommendations
        """
        available_models = self.list_models()
        
        available = []
        missing = []
        fallbacks = {}
        
        for model in required_models:
            if self.check_model(model):
                available.append(model)
            else:
                missing.append(model)
                fallback = self.get_fallback_model(model)
                if fallback:
                    fallbacks[model] = fallback
        
        result = {
            'available': available,
            'missing': missing,
            'fallbacks': fallbacks,
            'total_on_server': len(available_models)
        }
        
        logger.info(f"Model verification: {len(available)} available, {len(missing)} missing")
        
        return result


# Convenience functions
def check_model_available(model_name: str,
                         endpoint: str,
                         auth: Optional[Tuple[str, str]] = None) -> bool:
    """
    Quick check if a model is available.
    
    Args:
        model_name: Model to check
        endpoint: Ollama server URL
        auth: Optional (username, password) tuple
        
    Returns:
        True if available
    """
    checker = ModelChecker(endpoint, auth)
    return checker.check_model(model_name)


def get_available_models(endpoint: str,
                        auth: Optional[Tuple[str, str]] = None) -> List[str]:
    """
    Get list of available models.
    
    Args:
        endpoint: Ollama server URL
        auth: Optional (username, password) tuple
        
    Returns:
        List of model names
    """
    checker = ModelChecker(endpoint, auth)
    return checker.list_models()


def test_ollama_connection(endpoint: str,
                          auth: Optional[Tuple[str, str]] = None) -> bool:
    """
    Test if Ollama server is reachable.
    
    Args:
        endpoint: Ollama server URL
        auth: Optional (username, password) tuple
        
    Returns:
        True if server responds
    """
    checker = ModelChecker(endpoint, auth)
    return checker.test_connection()

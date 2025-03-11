import logging
import os
import json
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Logger configuration
logger = logging.getLogger("api_client")

class APIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class DeepSeekClient:
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        self.base_url = os.getenv("API_ENDPOINT", "https://api.deepseek.com")
        self.model = os.getenv("API_MODEL", "deepseek-chat")
        self.timeout = int(os.getenv("API_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        
        if not self.api_key:
            logger.warning("API_KEY environment variable not set")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1),
    )
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        json_mode: bool = False,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ):
        """
        Generic chat completion with DeepSeek API
        
        Args:
            messages: List of message objects
            json_mode: Whether to force JSON output format
            tools: List of tool definitions
            **kwargs: Additional parameters for the API call
            
        Returns:
            API response
        """
        try:
            params = {
                "model": self.model,
                "messages": messages,
                "timeout": self.timeout,
                **kwargs
            }
            
            if json_mode:
                params["response_format"] = {"type": "json_object"}
                
            if tools:
                params["tools"] = tools
                
            response = self.client.chat.completions.create(**params)
            return response.choices[0].message
            
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise APIError(str(e))
    
    async def classify_content(self, content: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify content using JSON mode
        
        Args:
            content: Text to classify
            system_prompt: Custom system prompt for classification
            
        Returns:
            Classification results as dictionary
        """
        default_system = """
        Analyze the given content and classify it according to the following criteria. 
        Output the result in JSON format.
        
        Classification criteria:
        - intent: The primary intent (command, question, statement, spam)
        - sentiment: Overall sentiment (positive, negative, neutral)
        - topics: List of relevant topics
        
        Example output:
        {
            "intent": "question",
            "sentiment": "neutral",
            "topics": ["technology", "information"]
        }
        """
        
        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": content}
        ]
        
        try:
            response = await self.chat_completion(messages, json_mode=True)
            return json.loads(response.content)
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            return {"intent": "unknown", "sentiment": "neutral", "topics": []}
    
    async def tool_use(self, query: str, tools: List[Dict], conversation: Optional[List[Dict]] = None) -> Dict:
        """
        Use tools with DeepSeek API
        
        Args:
            query: User query
            tools: Tool definitions
            conversation: Optional existing conversation history
            
        Returns:
            Response including any tool calls
        """
        messages = conversation or []
        messages.append({"role": "user", "content": query})
        
        response = await self.chat_completion(messages, tools=tools)
        return response
    
    async def conversation(self, messages: List[Dict[str, str]]) -> str:
        """
        Continue a multi-turn conversation
        
        Args:
            messages: Conversation history
            
        Returns:
            Model response text
        """
        response = await self.chat_completion(messages)
        return response.content

# Create a global client instance
_client = None

def get_client() -> DeepSeekClient:
    """Get or create the DeepSeek client instance"""
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client 
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import random
from api_client import safe_api_call, APIResponse
from settings import get_settings

class ClassificationRequest(BaseModel):
    message: str
    current_price: int  # in cents
    temperature: float = get_settings().message_classification_temperature

class VoteIntent(BaseModel):
    intent: str
    confidence: float

class MessageClassificationRequest(BaseModel):
    system_prompt: str = """
    Analyze the given message and classify it according to the following criteria. Output in JSON format.
    
    Classification criteria:
    - intent: The primary intent (command, question, statement, spam)
    - sentiment: Overall sentiment (positive, negative, neutral)
    - toxicity: Toxicity level (0-1 scale)
    - topics: List of relevant topics
    - action_required: Whether moderator action is needed (true/false)
    
    Example output:
    {
        "intent": "command",
        "sentiment": "negative",
        "toxicity": 0.7,
        "topics": ["moderation", "user_behavior"],
        "action_required": true
    }
    """
    user_prompt: str

class Classifier:
    def __init__(self):
        self.ignore_list: Dict[str, float] = {}
        self.logger = logging.getLogger("classifier")
    
    async def classify_message(self, message: str, current_price: int) -> Optional[VoteIntent]:
        if message in self.ignore_list:
            if random.random() < self.ignore_list[message]:
                self.logger.info(f"Skipping message due to ignore list: {message[:30]}...")
                return None
        
        self.logger.info(f"Classifying message: {message[:30]}...")
        
        try:
            request = ClassificationRequest(
                message=message,
                current_price=current_price
            )
            
            response = await safe_api_call(request)
            
            if response and response.ok:
                self.logger.info(f"Successfully classified message as {response.json()}")
                return VoteIntent(**response.json())
            else:
                self.logger.warning(f"Failed to classify message, adding to ignore list: {message[:30]}...")
                self._update_ignore_list(message)
                return None
                
        except Exception as e:
            self.logger.error(f"Unexpected error during classification: {str(e)}")
            self._update_ignore_list(message)
            return None
    
    def _update_ignore_list(self, message: str):
        """Update the ignore list probability for a message"""
        self.ignore_list.setdefault(message, 0)
        self.ignore_list[message] = min(1.0, self.ignore_list[message] + get_settings().message_ignore_list_increment)

async def classify_message(message: str) -> Dict[str, Any]:
    """
    Classify a message using DeepSeek API
    
    Args:
        message: The message text to classify
        
    Returns:
        Dict containing classification results
    """
    request = MessageClassificationRequest(user_prompt=message)
    response = await safe_api_call(request)
    
    if not response or not response.data:
        return {
            "intent": "unknown",
            "sentiment": "neutral",
            "toxicity": 0.0,
            "topics": [],
            "action_required": False
        }
        
    return response.data
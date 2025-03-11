from typing import Optional, Dict, Any
import logging
from urllib.parse import urlparse
from settings import get_settings
from pydantic import BaseModel, validator, Field, ValidationError

logger = logging.getLogger("input_validator")

class ValidationResult:
    """Result of input validation"""
    def __init__(self, is_valid: bool, error: Optional[str] = None):
        self.is_valid = is_valid
        self.error = error

class VoteInput(BaseModel):
    """Vote input validation model"""
    user_id: str = Field(..., min_length=1, max_length=50)
    direction: str
    amount: Optional[int] = None
    
    @validator('direction')
    def validate_direction(cls, v):
        settings = get_settings()
        if v not in settings.input_allowed_vote_directions:
            raise ValueError(f"Invalid vote direction. Must be one of: {settings.input_allowed_vote_directions}")
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v is not None:
            settings = get_settings()
            if v < settings.input_min_vote_amount or v > settings.input_max_vote_amount:
                raise ValueError(
                    f"Vote amount must be between {settings.input_min_vote_amount} "
                    f"and {settings.input_max_vote_amount}"
                )
        return v

class MessageInput(BaseModel):
    """Message input validation model"""
    user_id: str = Field(..., min_length=1, max_length=50)
    message: str
    
    @validator('message')
    def validate_message(cls, v):
        settings = get_settings()
        if len(v) > settings.input_max_message_length:
            raise ValueError(f"Message too long. Maximum length is {settings.input_max_message_length}")
        return v

class ProfileInput(BaseModel):
    """Profile input validation model"""
    user_id: str = Field(..., min_length=1, max_length=50)
    profile_url: str
    
    @validator('profile_url')
    def validate_profile_url(cls, v):
        settings = get_settings()
        
        # Check URL length
        if len(v) > settings.input_max_profile_url_length:
            raise ValueError(f"URL too long. Maximum length is {settings.input_max_profile_url_length}")
        
        # Parse URL and check domain
        try:
            parsed = urlparse(v)
            domain = parsed.netloc.lower()
            
            if not domain:
                raise ValueError("Invalid URL format")
                
            if domain not in settings.input_allowed_profile_domains:
                raise ValueError(f"Domain not allowed. Must be one of: {settings.input_allowed_profile_domains}")
                
            if not parsed.scheme in ['http', 'https']:
                raise ValueError("URL must use HTTP or HTTPS protocol")
                
        except Exception as e:
            raise ValueError(f"Invalid URL: {str(e)}")
            
        return v

class InputValidator:
    """Input validation service"""
    
    @staticmethod
    def validate_vote(data: Dict[str, Any]) -> ValidationResult:
        """Validate vote input"""
        try:
            VoteInput(**data)
            return ValidationResult(True)
        except ValidationError as e:
            error = "; ".join(err["msg"] for err in e.errors())
            logger.warning(f"Vote validation failed: {error}")
            return ValidationResult(False, error)
    
    @staticmethod
    def validate_message(data: Dict[str, Any]) -> ValidationResult:
        """Validate message input"""
        try:
            MessageInput(**data)
            return ValidationResult(True)
        except ValidationError as e:
            error = "; ".join(err["msg"] for err in e.errors())
            logger.warning(f"Message validation failed: {error}")
            return ValidationResult(False, error)
    
    @staticmethod
    def validate_profile(data: Dict[str, Any]) -> ValidationResult:
        """Validate profile input"""
        try:
            ProfileInput(**data)
            return ValidationResult(True)
        except ValidationError as e:
            error = "; ".join(err["msg"] for err in e.errors())
            logger.warning(f"Profile validation failed: {error}")
            return ValidationResult(False, error)

# Global validator instance
_validator = None

def get_validator() -> InputValidator:
    """Get or create the global validator instance"""
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator 
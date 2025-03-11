from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import logging
from settings import get_settings

logger = logging.getLogger("rate_limiter")

class RateLimiter:
    """Rate limiter using token bucket algorithm"""
    def __init__(self):
        self.buckets: Dict[str, Tuple[float, datetime]] = {}  # {key: (tokens, last_update)}
        self.settings = get_settings()
    
    def _get_bucket(self, key: str) -> Tuple[float, datetime]:
        """Get or create a bucket for the given key"""
        if key not in self.buckets:
            self.buckets[key] = (self.settings.rate_limit_max_tokens, datetime.now())
        return self.buckets[key]
    
    def _refill_bucket(self, key: str) -> None:
        """Refill tokens based on time elapsed"""
        tokens, last_update = self._get_bucket(key)
        now = datetime.now()
        time_passed = (now - last_update).total_seconds()
        
        # Calculate tokens to add based on refill rate
        new_tokens = time_passed * self.settings.rate_limit_refill_rate
        
        # Update bucket with new tokens, capped at max
        self.buckets[key] = (
            min(self.settings.rate_limit_max_tokens, tokens + new_tokens),
            now
        )
    
    def check_rate_limit(self, key: str, cost: float = 1.0) -> Tuple[bool, Optional[float]]:
        """
        Check if an action is allowed under rate limiting
        
        Args:
            key: The rate limiting key (e.g. user_id)
            cost: Token cost of the action (default: 1.0)
            
        Returns:
            Tuple of (allowed: bool, retry_after: Optional[float])
        """
        self._refill_bucket(key)
        tokens, _ = self.buckets[key]
        
        if tokens >= cost:
            # Action is allowed, consume tokens
            self.buckets[key] = (tokens - cost, datetime.now())
            return True, None
        else:
            # Calculate time until enough tokens are available
            tokens_needed = cost - tokens
            retry_after = tokens_needed / self.settings.rate_limit_refill_rate
            return False, retry_after
    
    def get_remaining_tokens(self, key: str) -> float:
        """Get remaining tokens for a key"""
        self._refill_bucket(key)
        tokens, _ = self.buckets[key]
        return tokens

# Global rate limiter instance
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter 
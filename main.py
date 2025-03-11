from message_classification import Classifier, classify_message
from price_state import PriceState
from obs_controller import OBSController
from user_rep import UserManager, UserStats
from vote_weight import VoteCalculator
from logging_config import setup_logging
from profile_cache import get_profile_cache, close_profile_cache
from database import get_db_manager, close_database
from animation_manager import get_animation_manager, close_animation_manager
from rate_limiter import get_rate_limiter
from input_validator import get_validator, ValidationResult
from settings import get_settings
import logging
import asyncio
import signal
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Initialize logging system
logger = setup_logging()

class ProcessingError(Exception):
    """Base class for processing errors"""
    pass

class RateLimitError(ProcessingError):
    """Error when rate limit is exceeded"""
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Try again in {retry_after:.1f} seconds")

class ValidationError(ProcessingError):
    """Error when input validation fails"""
    pass

class NYPProcessor:
    def __init__(self):
        self.classifier = Classifier()
        self.user_manager = UserManager()
        self.price_state = PriceState(current_price=1000, base_price=1000)
        self.obs = OBSController()
        self.logger = logging.getLogger("processor")
        self.settings = get_settings()
        self.rate_limiter = get_rate_limiter()
        self.validator = get_validator()
        self.logger.info("Price of War processor initialized")

    async def initialize(self):
        """Initialize the processor with data from database"""
        # Initialize OBS controller with animation manager
        await self.obs.initialize()
        
        # Load active users
        await self.user_manager.load_active_users()
        self.logger.info("Initialized processor with data from database")
    
    async def process_message(self, user_id: str, message: str) -> Optional[Dict[str, Any]]:
        """Process a chat message"""
        # Validate input
        validation_result = self.validator.validate_message({
            "user_id": user_id,
            "message": message
        })
        if not validation_result.is_valid:
            raise ValidationError(validation_result.error)
        
        # Check rate limit
        allowed, retry_after = self.rate_limiter.check_rate_limit(
            f"message_{user_id}",
            cost=self.settings.rate_limit_message_cost
        )
        if not allowed:
            raise RateLimitError(retry_after)
        
        # Get user stats
        user = self.user_manager.get_user(user_id)
        
        # Classify message
        classification = await classify_message(message)
        if not classification:
            return None
            
        # Process vote if message was classified as a vote
        if classification["intent"] in self.settings.input_allowed_vote_directions:
            return await self.process_vote(user_id, classification["intent"], classification["amount"])
            
        # Take action based on classification
        if classification["action_required"]:
            # Handle moderation
            pass
        
        if classification["toxicity"] > 0.8:
            # Handle toxic content
            pass
        
        return classification
    
    async def process_vote(self, user_id: str, direction: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """Process a vote"""
        # Validate input
        validation_result = self.validator.validate_vote({
            "user_id": user_id,
            "direction": direction,
            "amount": amount
        })
        if not validation_result.is_valid:
            raise ValidationError(validation_result.error)
        
        # Check rate limit
        allowed, retry_after = self.rate_limiter.check_rate_limit(
            f"vote_{user_id}",
            cost=self.settings.rate_limit_vote_cost
        )
        if not allowed:
            raise RateLimitError(retry_after)
        
        # Get user stats
        user = self.user_manager.get_user(user_id)
        
        # Calculate vote weight
        vote_value = amount if amount is not None else self.price_state.current_price
        weight = VoteCalculator.calculate_weight(user, vote_value, self.price_state.current_price)
        
        self.logger.info(f"Vote value: {vote_value}, weight: {weight}")
        
        if weight == 0:
            await self._handle_fizzled_vote(user, vote_value)
            return {'status': 'fizzled'}
        
        # Apply vote to price state
        self.price_state.apply_vote(weight, direction)
        
        # Update user stats
        self._update_user_stats(user, vote_value)
        
        # Create OBS effect
        await self.obs.apply_effect(user, {
            'direction': direction,
            'intensity': weight
        })
        
        return {
            'status': 'success',
            'weight': weight,
            'new_price': self.price_state.current_price
        }
    
    async def update_profile_picture(self, user_id: str, profile_url: str) -> Dict[str, Any]:
        """Update a user's profile picture"""
        # Validate input
        validation_result = self.validator.validate_profile({
            "user_id": user_id,
            "profile_url": profile_url
        })
        if not validation_result.is_valid:
            raise ValidationError(validation_result.error)
        
        # Check rate limit
        allowed, retry_after = self.rate_limiter.check_rate_limit(
            f"profile_{user_id}",
            cost=self.settings.rate_limit_profile_cost
        )
        if not allowed:
            raise RateLimitError(retry_after)
        
        # Update profile picture
        user = self.user_manager.get_user(user_id)
        await user.set_profile_picture_url(profile_url)
        
        return {
            'status': 'success',
            'profile_url': profile_url
        }
    
    def _update_user_stats(self, user: UserStats, vote_value: int):
        """Update user statistics and save to database"""
        # Update user statistics
        user.lifetime_votes += 1
        user.show_votes += 1
        user.last_vote_time = datetime.now()
        
        # Additional stat updates would go here
        
        # Save to database
        self.user_manager.update_user_stats(user)
        
    async def preload_active_users_profile_pictures(self, user_ids: list):
        """Preload profile pictures for active users"""
        await self.user_manager.preload_profile_pictures(user_ids)
        
    async def get_top_voters(self, limit: int = None):
        """Get the top voters"""
        return self.user_manager.get_top_voters(limit)
        
    async def close(self):
        """Close all processor resources"""
        try:
            # Close OBS controller
            await self.obs.close()
            self.logger.info("Closed OBS controller")
        except Exception as e:
            self.logger.error(f"Error closing OBS controller: {str(e)}")

# Shutdown flag and handler
shutdown_event = asyncio.Event()

def handle_shutdown_signal(sig, frame):
    """Handle shutdown signals"""
    logger.info(f"Received shutdown signal {sig}")
    shutdown_event.set()

# Application entry point
async def main():
    processor = None
    try:
        # Setup signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, handle_shutdown_signal)
        
        logger.info("Starting Price of War application")
        
        # Initialize animation manager first (needed by OBS controller)
        animation_manager = get_animation_manager()
        await animation_manager.start()
        logger.info("Animation manager initialized")
        
        # Initialize database
        db_manager = get_db_manager()
        logger.info("Database initialized")
        
        # Initialize cache
        _ = get_profile_cache()
        logger.info("Profile cache initialized")
        
        # Create and initialize processor
        processor = NYPProcessor()
        await processor.initialize()
        
        # Application main loop
        logger.info("Application started successfully")
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
    except Exception as e:
        logger.critical(f"Failed to start or run application: {str(e)}", exc_info=True)
    finally:
        # Perform cleanup in reverse order of initialization
        logger.info("Shutting down application")
        
        # Close processor resources
        if processor:
            await processor.close()
            
        # Close animation manager
        await close_animation_manager()
        
        # Close profile cache
        await close_profile_cache()
        
        # Close database
        close_database()
        
        logger.info("Application shutdown complete")
        
if __name__ == "__main__":
    # Run with proper shutdown handling
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.critical(f"Application terminated unexpectedly: {str(e)}", exc_info=True)
from pydantic import BaseModel
from typing import List
from datetime import datetime
import logging
from settings import get_settings

# Configure logger for price state
logger = logging.getLogger("price_state")

class PriceState(BaseModel):
    current_price: int
    base_price: int
    votes: List[float] = []
    last_updated: datetime = datetime.now()

    def apply_vote(self, weight: float, direction: str):
        try:
            # Validate direction
            if direction not in ['up', 'down', 'set']:
                logger.warning(f"Invalid vote direction: {direction}, defaulting to 0 multiplier")
            
            # Get direction multiplier
            adjustment = weight * self._get_direction_multiplier(direction)
            self.votes.append(adjustment)
            
            logger.info(f"Applied vote: weight={weight}, direction={direction}, adjustment={adjustment}")
            
            # Maintain votes list size
            if len(self.votes) > get_settings().price_state_max_votes:
                removed = self.votes.pop(0)
                logger.debug(f"Removed oldest vote: {removed}")
            
            # Calculate new price    
            try:
                self.current_price = int(self.base_price * (1 + sum(self.votes)/get_settings().price_state_vote_divisor))
                logger.info(f"Updated price: {self.current_price} (base: {self.base_price}, votes sum: {sum(self.votes)})")
            except (ValueError, OverflowError) as e:
                logger.error(f"Error calculating price: {str(e)}")
                # Recover by resetting votes if calculation fails
                self.votes = []
                self.current_price = self.base_price
                logger.info("Reset votes and price to base price after calculation error")
                
            # Update timestamp
            self.last_updated = datetime.now()
        except Exception as e:
            logger.error(f"Unexpected error in apply_vote: {str(e)}")
            # Don't raise, just log the error to prevent crashes

    def _get_direction_multiplier(self, direction: str) -> float:
        """Get the multiplier for a vote direction"""
        settings = get_settings()
        return {
            'up': settings.price_state_up_multiplier,
            'down': settings.price_state_down_multiplier,
            'set': settings.price_state_set_multiplier
        }.get(direction, settings.price_state_default_multiplier)

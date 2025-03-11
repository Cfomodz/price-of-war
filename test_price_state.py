import pytest
from datetime import datetime, timedelta
from price_state import PriceState
from settings import get_settings
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def price_state():
    """Create a test price state instance"""
    return PriceState(current_price=1000, base_price=1000)

class TestPriceState:
    def test_initial_state(self, price_state):
        """Test initial price state"""
        assert price_state.current_price == 1000
        assert price_state.base_price == 1000
        assert len(price_state.votes) == 0
        assert isinstance(price_state.last_updated, datetime)
    
    def test_upvote(self, price_state):
        """Test applying an up vote"""
        settings = get_settings()
        weight = 1.0
        
        # Apply upvote
        price_state.apply_vote(weight, 'up')
        
        # Calculate expected adjustment
        expected_adjustment = weight * settings.price_state_up_multiplier
        
        # Test votes array
        assert len(price_state.votes) == 1
        assert price_state.votes[0] == expected_adjustment
        
        # Test price calculation
        expected_price = int(price_state.base_price * (1 + sum(price_state.votes)/settings.price_state_vote_divisor))
        assert price_state.current_price == expected_price
    
    def test_downvote(self, price_state):
        """Test applying a down vote"""
        settings = get_settings()
        weight = 1.0
        
        # Apply downvote
        price_state.apply_vote(weight, 'down')
        
        # Calculate expected adjustment
        expected_adjustment = weight * settings.price_state_down_multiplier
        
        # Test votes array
        assert len(price_state.votes) == 1
        assert price_state.votes[0] == expected_adjustment
        
        # Test price calculation
        expected_price = int(price_state.base_price * (1 + sum(price_state.votes)/settings.price_state_vote_divisor))
        assert price_state.current_price == expected_price
        
        # Check that price went down
        assert price_state.current_price < price_state.base_price
    
    def test_set_vote(self, price_state):
        """Test applying a set vote"""
        settings = get_settings()
        weight = 1.0
        
        # Apply set vote
        price_state.apply_vote(weight, 'set')
        
        # Calculate expected adjustment
        expected_adjustment = weight * settings.price_state_set_multiplier
        
        # Test votes array
        assert len(price_state.votes) == 1
        assert price_state.votes[0] == expected_adjustment
        
        # Test price calculation
        expected_price = int(price_state.base_price * (1 + sum(price_state.votes)/settings.price_state_vote_divisor))
        assert price_state.current_price == expected_price
    
    def test_invalid_direction(self, price_state):
        """Test applying vote with invalid direction"""
        settings = get_settings()
        weight = 1.0
        
        # Apply invalid vote
        price_state.apply_vote(weight, 'invalid')
        
        # Calculate expected adjustment
        expected_adjustment = weight * settings.price_state_default_multiplier
        
        # Test votes array
        assert len(price_state.votes) == 1
        assert price_state.votes[0] == expected_adjustment
        
        # Test price calculation (should be unchanged with default multiplier)
        assert price_state.current_price == price_state.base_price
    
    def test_multiple_votes(self, price_state):
        """Test applying multiple votes"""
        settings = get_settings()
        
        # Apply a series of votes
        price_state.apply_vote(1.0, 'up')
        price_state.apply_vote(0.5, 'up')
        price_state.apply_vote(0.8, 'down')
        
        # Calculate expected adjustments
        expected_votes = [
            1.0 * settings.price_state_up_multiplier,
            0.5 * settings.price_state_up_multiplier,
            0.8 * settings.price_state_down_multiplier
        ]
        
        # Test votes array
        assert len(price_state.votes) == 3
        for i, vote in enumerate(price_state.votes):
            assert vote == expected_votes[i]
        
        # Test price calculation
        expected_price = int(price_state.base_price * (1 + sum(expected_votes)/settings.price_state_vote_divisor))
        assert price_state.current_price == expected_price
    
    def test_votes_limit(self, price_state):
        """Test votes list size is limited"""
        settings = get_settings()
        max_votes = settings.price_state_max_votes
        
        # Apply more than the max number of votes
        for i in range(max_votes + 5):
            price_state.apply_vote(1.0, 'up')
        
        # Check that the votes list is limited to max size
        assert len(price_state.votes) == max_votes
        
        # Check that the oldest votes were removed
        for vote in price_state.votes:
            assert vote == settings.price_state_up_multiplier
    
    def test_error_recovery(self, price_state, monkeypatch):
        """Test recovery from calculation errors"""
        # Create a scenario that would cause an overflow
        def mock_sum(votes):
            raise OverflowError("Test overflow")
        
        # Apply a vote with normal calculation
        price_state.apply_vote(1.0, 'up')
        assert len(price_state.votes) == 1
        
        # Apply a vote with mocked calculation error
        monkeypatch.setattr('builtins.sum', mock_sum)
        price_state.apply_vote(1.0, 'up')
        
        # Check recovery - votes should be reset
        assert len(price_state.votes) == 0
        assert price_state.current_price == price_state.base_price
    
    def test_timestamp_updates(self, price_state):
        """Test last_updated timestamp updates with votes"""
        initial_time = price_state.last_updated
        
        # Wait a bit to ensure time difference
        import time
        time.sleep(0.01)
        
        # Apply vote
        price_state.apply_vote(1.0, 'up')
        
        # Check timestamp updated
        assert price_state.last_updated > initial_time

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov"])
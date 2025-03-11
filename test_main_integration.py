import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import logging
from datetime import datetime

from main import NYPProcessor, ValidationError, RateLimitError
from user_rep import UserStats
from message_classification import VoteIntent

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def mock_user_stats():
    """Create mock user stats for testing"""
    return UserStats(
        user_id="test_user",
        lifetime_votes=100,
        show_votes=50,
        lifetime_errors=5,
        show_errors=2,
        last_vote_time=datetime.now(),
        profile_url="https://i.pravatar.cc/300"
    )

@pytest.fixture
async def mock_processor():
    """Create a test processor with mocked dependencies"""
    with patch('main.UserManager') as mock_user_manager, \
         patch('main.Classifier') as mock_classifier, \
         patch('main.OBSController') as mock_obs, \
         patch('main.get_rate_limiter') as mock_rate_limiter, \
         patch('main.get_validator') as mock_validator:
        
        # Setup mocks
        mock_user_manager_instance = MagicMock()
        mock_user_manager.return_value = mock_user_manager_instance
        
        mock_classifier_instance = MagicMock()
        mock_classifier.return_value = mock_classifier_instance
        
        mock_obs_instance = AsyncMock()
        mock_obs.return_value = mock_obs_instance
        
        mock_rate_limiter_instance = MagicMock()
        mock_rate_limiter.return_value = mock_rate_limiter_instance
        
        mock_validator_instance = MagicMock()
        mock_validator.return_value = mock_validator_instance
        
        # Create processor
        processor = NYPProcessor()
        await processor.initialize()
        
        yield processor, {
            'user_manager': mock_user_manager_instance,
            'classifier': mock_classifier_instance,
            'obs': mock_obs_instance,
            'rate_limiter': mock_rate_limiter_instance,
            'validator': mock_validator_instance
        }

@pytest.mark.asyncio
class TestProcessorIntegration:
    async def test_process_message_to_vote(self, mock_processor, mock_user_stats):
        """Test processing a message that gets classified as a vote"""
        processor, mocks = mock_processor
        
        # Setup mocks
        mocks['validator'].validate_message.return_value = MagicMock(is_valid=True, error=None)
        mocks['rate_limiter'].check_rate_limit.return_value = (True, 0)
        mocks['user_manager'].get_user.return_value = mock_user_stats
        
        # Setup classify_message mock to return a vote
        mock_classification = {
            "intent": "up",
            "amount": 1500,
            "confidence": 0.95
        }
        
        # Mock process_vote to track calls
        processor.process_vote = AsyncMock(return_value={"status": "success"})
        
        with patch('main.classify_message', AsyncMock(return_value=mock_classification)):
            # Process message
            result = await processor.process_message("test_user", "price should be higher")
            
            # Verify message validation
            mocks['validator'].validate_message.assert_called_once()
            
            # Verify rate limit check
            mocks['rate_limiter'].check_rate_limit.assert_called_once()
            
            # Verify user retrieval
            mocks['user_manager'].get_user.assert_called_once_with("test_user")
            
            # Verify vote processing called with correct parameters
            processor.process_vote.assert_called_once_with("test_user", "up", 1500)
            
            # Verify result
            assert result == {"status": "success"}
    
    async def test_process_vote_successfully(self, mock_processor, mock_user_stats):
        """Test successful vote processing"""
        processor, mocks = mock_processor
        
        # Save original method for partial mocking
        original_process_vote = processor.process_vote
        
        # Setup mocks
        mocks['validator'].validate_vote.return_value = MagicMock(is_valid=True, error=None)
        mocks['rate_limiter'].check_rate_limit.return_value = (True, 0)
        mocks['user_manager'].get_user.return_value = mock_user_stats
        
        # Don't mock VoteCalculator - we'll test the real one
        
        # Process vote
        result = await original_process_vote("test_user", "up", 1500)
        
        # Verify validation
        mocks['validator'].validate_vote.assert_called_once()
        
        # Verify rate limit check
        mocks['rate_limiter'].check_rate_limit.assert_called_once()
        
        # Verify user retrieval
        mocks['user_manager'].get_user.assert_called_once_with("test_user")
        
        # Verify price state update
        assert processor.price_state.current_price != 1000  # Price should change
        
        # Verify OBS effect applied
        mocks['obs'].apply_effect.assert_called_once()
        
        # Verify result
        assert result['status'] == 'success'
        assert 'weight' in result
        assert 'new_price' in result
    
    async def test_validation_error_handling(self, mock_processor):
        """Test handling validation errors"""
        processor, mocks = mock_processor
        
        # Setup mocks to fail validation
        mocks['validator'].validate_message.return_value = MagicMock(is_valid=False, error="Invalid message")
        
        # Process message should raise ValidationError
        with pytest.raises(ValidationError) as excinfo:
            await processor.process_message("test_user", "invalid message")
        
        assert "Invalid message" in str(excinfo.value)
    
    async def test_rate_limit_error_handling(self, mock_processor):
        """Test handling rate limit errors"""
        processor, mocks = mock_processor
        
        # Setup mocks to pass validation but fail rate limit
        mocks['validator'].validate_message.return_value = MagicMock(is_valid=True, error=None)
        mocks['rate_limiter'].check_rate_limit.return_value = (False, 10.5)
        
        # Process message should raise RateLimitError
        with pytest.raises(RateLimitError) as excinfo:
            await processor.process_message("test_user", "rate limited message")
        
        assert "10.5" in str(excinfo.value)  # Should include retry time
    
    async def test_update_profile_picture(self, mock_processor, mock_user_stats):
        """Test profile picture update"""
        processor, mocks = mock_processor
        
        # Setup mocks
        mocks['validator'].validate_profile.return_value = MagicMock(is_valid=True, error=None)
        mocks['rate_limiter'].check_rate_limit.return_value = (True, 0)
        
        # Setup mock user
        mock_user = AsyncMock()
        mocks['user_manager'].get_user.return_value = mock_user
        
        # Update profile picture
        result = await processor.update_profile_picture("test_user", "https://i.pravatar.cc/300")
        
        # Verify validation
        mocks['validator'].validate_profile.assert_called_once()
        
        # Verify rate limit check
        mocks['rate_limiter'].check_rate_limit.assert_called_once()
        
        # Verify user retrieval
        mocks['user_manager'].get_user.assert_called_once_with("test_user")
        
        # Verify profile update
        mock_user.set_profile_picture_url.assert_called_once_with("https://i.pravatar.cc/300")
        
        # Verify result
        assert result['status'] == 'success'
        assert result['profile_url'] == 'https://i.pravatar.cc/300'

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov"])
import pytest
import asyncio
from unittest.mock import MagicMock, patch
import message_classification
from message_classification import Classifier, classify_message, VoteIntent
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

class MockResponse:
    def __init__(self, data=None, ok=True):
        self.data = data
        self.ok = ok
    
    def json(self):
        return self.data

@pytest.fixture
def classifier():
    """Create a test classifier instance"""
    return Classifier()

@pytest.mark.asyncio
class TestMessageClassification:
    async def test_classify_message_up(self, monkeypatch):
        """Test classifying a message as an up vote"""
        # Mock the API response
        mock_response = MockResponse(
            data={
                "intent": "up",
                "confidence": 0.95,
                "amount": 1000
            },
            ok=True
        )
        
        # Patch the safe_api_call function
        async def mock_api_call(*args, **kwargs):
            return mock_response
        
        monkeypatch.setattr(message_classification, "safe_api_call", mock_api_call)
        
        # Call the function
        result = await classify_message("price should be higher")
        
        # Check result
        assert result["intent"] == "up"
        assert result["confidence"] == 0.95
    
    async def test_classify_message_down(self, monkeypatch):
        """Test classifying a message as a down vote"""
        # Mock the API response
        mock_response = MockResponse(
            data={
                "intent": "down", 
                "confidence": 0.9,
                "amount": 800
            },
            ok=True
        )
        
        # Patch the safe_api_call function
        async def mock_api_call(*args, **kwargs):
            return mock_response
        
        monkeypatch.setattr(message_classification, "safe_api_call", mock_api_call)
        
        # Call the function
        result = await classify_message("price should be lower")
        
        # Check result
        assert result["intent"] == "down"
        assert result["confidence"] == 0.9
    
    async def test_classify_message_set(self, monkeypatch):
        """Test classifying a message as a set vote"""
        # Mock the API response
        mock_response = MockResponse(
            data={
                "intent": "set",
                "confidence": 0.98,
                "amount": 1500
            },
            ok=True
        )
        
        # Patch the safe_api_call function
        async def mock_api_call(*args, **kwargs):
            return mock_response
        
        monkeypatch.setattr(message_classification, "safe_api_call", mock_api_call)
        
        # Call the function
        result = await classify_message("the price should be $15")
        
        # Check result
        assert result["intent"] == "set"
        assert result["confidence"] == 0.98
    
    async def test_classify_message_api_error(self, monkeypatch):
        """Test handling API error in message classification"""
        # Patch the safe_api_call function to simulate an error
        async def mock_api_call(*args, **kwargs):
            return None
        
        monkeypatch.setattr(message_classification, "safe_api_call", mock_api_call)
        
        # Call the function
        result = await classify_message("some message")
        
        # Check default result on error
        assert result["intent"] == "unknown"
        assert result["sentiment"] == "neutral"
        assert result["action_required"] == False
    
    async def test_classifier_vote_intent(self, classifier, monkeypatch):
        """Test the Classifier class for vote intent"""
        mock_response = MockResponse(
            data={
                "intent": "up",
                "confidence": 0.95
            },
            ok=True
        )
        
        # Patch the safe_api_call function
        async def mock_api_call(*args, **kwargs):
            return mock_response
        
        monkeypatch.setattr(message_classification, "safe_api_call", mock_api_call)
        
        # Test classification
        result = await classifier.classify_message("price should be higher", 1000)
        
        # Check result
        assert isinstance(result, VoteIntent)
        assert result.intent == "up"
        assert result.confidence == 0.95
    
    async def test_classifier_ignore_list(self, classifier, monkeypatch):
        """Test the ignore list functionality"""
        # Add a message to the ignore list with 100% probability
        test_message = "test message to ignore"
        classifier.ignore_list[test_message] = 1.0
        
        # Should be skipped due to ignore list
        result = await classifier.classify_message(test_message, 1000)
        assert result is None
        
        # Verify no API call was made due to the ignore list
        mock_api_call = MagicMock(return_value=MockResponse())
        monkeypatch.setattr(message_classification, "safe_api_call", mock_api_call)
        
        result = await classifier.classify_message(test_message, 1000)
        assert result is None
        assert mock_api_call.call_count == 0
    
    async def test_classifier_update_ignore_list(self, classifier, monkeypatch):
        """Test updating the ignore list on API failure"""
        test_message = "message with API failure"
        
        # First simulate an API error
        async def mock_api_error(*args, **kwargs):
            return None
        
        monkeypatch.setattr(message_classification, "safe_api_call", mock_api_error)
        
        # Attempt classification - should fail and update ignore list
        result = await classifier.classify_message(test_message, 1000)
        assert result is None
        assert test_message in classifier.ignore_list
        assert classifier.ignore_list[test_message] > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov"])
import pytest
from datetime import datetime, timedelta
from rate_limiter import RateLimiter
from input_validator import InputValidator, ValidationResult
from vote_weight import VoteCalculator
from user_rep import UserStats
from settings import Settings, get_settings
from unittest.mock import patch, MagicMock
from freezegun import freeze_time
from hypothesis import given, strategies as st, assume
import math

# Test fixtures
@pytest.fixture
def settings():
    return get_settings()

@pytest.fixture
def rate_limiter():
    return RateLimiter()

@pytest.fixture
def validator():
    return InputValidator()

@pytest.fixture
def user_stats():
    return UserStats(
        user_id="test_user",
        lifetime_votes=100,
        show_votes=50,
        lifetime_errors=5,
        show_errors=2,
        last_vote_time=datetime.now()
    )

# Rate Limiter Tests
class TestRateLimiter:
    def test_initial_tokens(self, rate_limiter, settings):
        """Test initial token count matches max tokens setting"""
        bucket = rate_limiter._get_bucket("test_user")
        assert bucket[0] == settings.rate_limit_max_tokens

    def test_token_consumption(self, rate_limiter):
        """Test token consumption works correctly"""
        allowed, _ = rate_limiter.check_rate_limit("test_user", cost=2.0)
        assert allowed is True
        bucket = rate_limiter._get_bucket("test_user")
        assert bucket[0] == rate_limiter.settings.rate_limit_max_tokens - 2.0

    def test_rate_limit_exceeded(self, rate_limiter):
        """Test rate limiting when tokens are exhausted"""
        # Consume all tokens
        rate_limiter.check_rate_limit("test_user", cost=rate_limiter.settings.rate_limit_max_tokens)
        allowed, retry_after = rate_limiter.check_rate_limit("test_user", cost=1.0)
        assert allowed is False
        assert retry_after > 0

    @freeze_time("2023-01-01 12:00:00")
    def test_token_refill(self, rate_limiter):
        """Test tokens are refilled over time"""
        # Consume some tokens
        rate_limiter.check_rate_limit("test_user", cost=5.0)
        initial_tokens = rate_limiter._get_bucket("test_user")[0]
        
        with freeze_time("2023-01-01 12:00:02"):  # Advance time by 2 seconds
            rate_limiter._refill_bucket("test_user")
            new_tokens = rate_limiter._get_bucket("test_user")[0]
            expected_tokens = min(
                rate_limiter.settings.rate_limit_max_tokens,
                initial_tokens + (2 * rate_limiter.settings.rate_limit_refill_rate)
            )
            assert abs(new_tokens - expected_tokens) < 0.001  # Float comparison

    def test_multiple_users(self, rate_limiter):
        """Test rate limiting works independently for different users"""
        allowed1, _ = rate_limiter.check_rate_limit("user1", cost=5.0)
        allowed2, _ = rate_limiter.check_rate_limit("user2", cost=5.0)
        assert allowed1 and allowed2
        
        bucket1 = rate_limiter._get_bucket("user1")
        bucket2 = rate_limiter._get_bucket("user2")
        assert bucket1[0] == bucket2[0]  # Both should have same remaining tokens

# Input Validation Tests
class TestInputValidator:
    def test_valid_vote_input(self, validator):
        """Test valid vote input passes validation"""
        result = validator.validate_vote({
            "user_id": "test_user",
            "direction": "up",
            "amount": 100
        })
        assert result.is_valid is True
        assert result.error is None

    def test_invalid_vote_direction(self, validator):
        """Test invalid vote direction fails validation"""
        result = validator.validate_vote({
            "user_id": "test_user",
            "direction": "invalid",
            "amount": 100
        })
        assert result.is_valid is False
        assert "Invalid vote direction" in result.error

    def test_vote_amount_bounds(self, validator, settings):
        """Test vote amount bounds validation"""
        # Test minimum bound
        result = validator.validate_vote({
            "user_id": "test_user",
            "direction": "up",
            "amount": settings.input_min_vote_amount - 1
        })
        assert result.is_valid is False
        assert "Vote amount must be between" in result.error

        # Test maximum bound
        result = validator.validate_vote({
            "user_id": "test_user",
            "direction": "up",
            "amount": settings.input_max_vote_amount + 1
        })
        assert result.is_valid is False
        assert "Vote amount must be between" in result.error

    def test_vote_amount_edge_cases(self, validator, settings):
        """Test edge cases for vote amount"""
        # Test exact minimum
        result = validator.validate_vote({
            "user_id": "test_user",
            "direction": "up",
            "amount": settings.input_min_vote_amount
        })
        assert result.is_valid is True

        # Test exact maximum
        result = validator.validate_vote({
            "user_id": "test_user",
            "direction": "up",
            "amount": settings.input_max_vote_amount
        })
        assert result.is_valid is True

    def test_valid_message_input(self, validator):
        """Test valid message input passes validation"""
        result = validator.validate_message({
            "user_id": "test_user",
            "message": "Test message"
        })
        assert result.is_valid is True
        assert result.error is None

    def test_message_length_limit(self, validator, settings):
        """Test message length validation"""
        # Test maximum length message
        max_message = "x" * settings.input_max_message_length
        result = validator.validate_message({
            "user_id": "test_user",
            "message": max_message
        })
        assert result.is_valid is True

        # Test too long message
        long_message = "x" * (settings.input_max_message_length + 1)
        result = validator.validate_message({
            "user_id": "test_user",
            "message": long_message
        })
        assert result.is_valid is False
        assert "Message too long" in result.error

    def test_profile_url_validation(self, validator):
        """Test comprehensive profile URL validation"""
        valid_urls = [
            "https://i.pravatar.cc/300",
            "https://imgur.com/image.jpg",
            "http://i.pravatar.cc/150"
        ]
        invalid_urls = [
            "ftp://i.pravatar.cc/300",  # Wrong protocol
            "https://invalid-domain.com/image.jpg",  # Invalid domain
            "not-a-url",  # Invalid URL format
            "https://i.pravatar.cc/" + "x" * 2048  # Too long
        ]

        for url in valid_urls:
            result = validator.validate_profile({
                "user_id": "test_user",
                "profile_url": url
            })
            assert result.is_valid is True, f"URL should be valid: {url}"

        for url in invalid_urls:
            result = validator.validate_profile({
                "user_id": "test_user",
                "profile_url": url
            })
            assert result.is_valid is False, f"URL should be invalid: {url}"

# Vote Weight Calculator Tests
class TestVoteCalculator:
    def test_basic_vote_weight(self, user_stats):
        """Test basic vote weight calculation"""
        weight = VoteCalculator.calculate_weight(
            user_stats,
            vote_value=1000,
            current_price=1000
        )
        assert 0 < weight <= 2.0  # Weight should be positive and not exceed max

    @freeze_time("2023-01-01 12:00:00")
    def test_reputation_impact(self, user_stats):
        """Test reputation impact on vote weight"""
        # Test with high reputation
        user_stats.lifetime_votes = 1000
        user_stats.show_votes = 500
        high_rep_weight = VoteCalculator.calculate_weight(
            user_stats,
            vote_value=1000,
            current_price=1000
        )

        # Test with low reputation
        user_stats.lifetime_votes = 10
        user_stats.show_votes = 5
        low_rep_weight = VoteCalculator.calculate_weight(
            user_stats,
            vote_value=1000,
            current_price=1000
        )

        assert high_rep_weight > low_rep_weight

    def test_time_decay(self, user_stats):
        """Test time decay impact on vote weight"""
        with freeze_time("2023-01-01 12:00:00"):
            # Recent vote
            user_stats.last_vote_time = datetime.now()
            recent_weight = VoteCalculator.calculate_weight(
                user_stats,
                vote_value=1000,
                current_price=1000
            )

        with freeze_time("2023-01-01 14:00:00"):  # 2 hours later
            # Old vote
            user_stats.last_vote_time = datetime.now() - timedelta(hours=2)
            old_weight = VoteCalculator.calculate_weight(
                user_stats,
                vote_value=1000,
                current_price=1000
            )

        assert recent_weight > old_weight

    def test_vote_value_ratio(self, user_stats):
        """Test vote value to current price ratio impact"""
        test_cases = [
            (1000, 1000),  # 1:1 ratio
            (2000, 1000),  # 2:1 ratio
            (500, 1000),   # 1:2 ratio
            (10000, 1000), # 10:1 ratio
            (100, 1000)    # 1:10 ratio
        ]
        
        weights = []
        for vote_value, current_price in test_cases:
            weight = VoteCalculator.calculate_weight(
                user_stats,
                vote_value=vote_value,
                current_price=current_price
            )
            weights.append(weight)
            
        # Check that extreme ratios result in lower weights
        assert weights[0] > weights[3]  # Normal ratio > extreme high ratio
        assert weights[0] > weights[4]  # Normal ratio > extreme low ratio

    def test_error_impact(self, user_stats):
        """Test impact of user errors on vote weight"""
        # Test with few errors
        user_stats.lifetime_errors = 1
        user_stats.show_errors = 0
        clean_weight = VoteCalculator.calculate_weight(
            user_stats,
            vote_value=1000,
            current_price=1000
        )

        # Test with many errors
        user_stats.lifetime_errors = 20
        user_stats.show_errors = 10
        error_weight = VoteCalculator.calculate_weight(
            user_stats,
            vote_value=1000,
            current_price=1000
        )

        assert clean_weight > error_weight

# Property-based tests for Rate Limiter
class TestRateLimiterProperties:
    @given(
        cost=st.floats(min_value=0.1, max_value=20.0),
        time_passed=st.integers(min_value=0, max_value=3600)
    )
    def test_token_refill_properties(self, rate_limiter, cost, time_passed):
        """Property-based test for token refill behavior"""
        # Initial state
        initial_tokens = rate_limiter.settings.rate_limit_max_tokens
        
        # Consume tokens
        allowed, _ = rate_limiter.check_rate_limit("test_user", cost=cost)
        if allowed:
            tokens_after_consumption = rate_limiter._get_bucket("test_user")[0]
            assert tokens_after_consumption == pytest.approx(initial_tokens - cost, rel=1e-9)
            
            # Simulate time passing
            rate_limiter.buckets["test_user"] = (
                tokens_after_consumption,
                datetime.now() - timedelta(seconds=time_passed)
            )
            
            # Refill
            rate_limiter._refill_bucket("test_user")
            final_tokens = rate_limiter._get_bucket("test_user")[0]
            
            # Properties that should hold
            assert final_tokens <= rate_limiter.settings.rate_limit_max_tokens
            assert final_tokens >= tokens_after_consumption
            
            expected_tokens = min(
                rate_limiter.settings.rate_limit_max_tokens,
                tokens_after_consumption + (time_passed * rate_limiter.settings.rate_limit_refill_rate)
            )
            assert final_tokens == pytest.approx(expected_tokens, rel=1e-9)

# Property-based tests for Input Validation
class TestInputValidatorProperties:
    @given(
        message=st.text(max_size=1000),
        user_id=st.text(min_size=1, max_size=50)
    )
    def test_message_validation_properties(self, validator, message, user_id):
        """Property-based test for message validation"""
        settings = get_settings()
        result = validator.validate_message({
            "user_id": user_id,
            "message": message
        })
        
        if len(message) <= settings.input_max_message_length:
            assert result.is_valid
        else:
            assert not result.is_valid
            assert "Message too long" in result.error

    @given(
        amount=st.integers(),
        direction=st.sampled_from(["up", "down", "set", "invalid"]),
        user_id=st.text(min_size=1, max_size=50)
    )
    def test_vote_validation_properties(self, validator, amount, direction, user_id):
        """Property-based test for vote validation"""
        settings = get_settings()
        result = validator.validate_vote({
            "user_id": user_id,
            "direction": direction,
            "amount": amount
        })
        
        if (direction in settings.input_allowed_vote_directions and
            settings.input_min_vote_amount <= amount <= settings.input_max_vote_amount):
            assert result.is_valid
        else:
            assert not result.is_valid

# Property-based tests for Vote Weight Calculator
class TestVoteCalculatorProperties:
    @given(
        lifetime_votes=st.integers(min_value=0, max_value=10000),
        show_votes=st.integers(min_value=0, max_value=1000),
        lifetime_errors=st.integers(min_value=0, max_value=100),
        show_errors=st.integers(min_value=0, max_value=20),
        vote_value=st.integers(min_value=1, max_value=100000),
        current_price=st.integers(min_value=1, max_value=100000)
    )
    def test_vote_weight_properties(self, user_stats, lifetime_votes, show_votes,
                                  lifetime_errors, show_errors, vote_value, current_price):
        """Property-based test for vote weight calculation"""
        # Assume reasonable values
        assume(show_votes <= lifetime_votes)
        assume(show_errors <= lifetime_errors)
        
        # Update user stats
        user_stats.lifetime_votes = lifetime_votes
        user_stats.show_votes = show_votes
        user_stats.lifetime_errors = lifetime_errors
        user_stats.show_errors = show_errors
        
        # Calculate weight
        weight = VoteCalculator.calculate_weight(
            user_stats,
            vote_value=vote_value,
            current_price=current_price
        )
        
        # Properties that should always hold
        assert 0 <= weight <= get_settings().vote_weight_max
        
        # Higher reputation should lead to higher weight
        if lifetime_votes > 0:
            low_rep_stats = UserStats(
                user_id="test_user",
                lifetime_votes=lifetime_votes // 2,
                show_votes=show_votes // 2,
                lifetime_errors=lifetime_errors,
                show_errors=show_errors,
                last_vote_time=user_stats.last_vote_time
            )
            low_rep_weight = VoteCalculator.calculate_weight(
                low_rep_stats,
                vote_value=vote_value,
                current_price=current_price
            )
            assert weight >= low_rep_weight

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov", "-n", "auto"]) 
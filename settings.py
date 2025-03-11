import os
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger("settings")

class Settings:
    """Central configuration class for application settings and thresholds"""
    
    # Helper method to get environment variables with typed defaults
    @staticmethod
    def get_env(key: str, default: Any, var_type: type = str) -> Any:
        """
        Get environment variable with typed conversion
        
        Args:
            key: Environment variable name
            default: Default value if not found
            var_type: Type to convert to (str, int, float, bool)
            
        Returns:
            Converted value or default
        """
        value = os.getenv(key)
        if value is None:
            return default
            
        try:
            if var_type == bool:
                return value.lower() in ('true', 'yes', '1', 't', 'y')
            elif var_type == int:
                return int(value)
            elif var_type == float:
                return float(value)
            elif var_type == list:
                return [item.strip() for item in value.split(',') if item.strip()]
            else:
                return value
        except (ValueError, TypeError) as e:
            logger.warning(f"Error converting {key}={value} to {var_type.__name__}: {str(e)}")
            return default
    
    def __init__(self):
        # API settings
        self.api_endpoint = self.get_env("API_ENDPOINT", "https://api.deepseek.com/v1/classify")
        self.api_key = self.get_env("API_KEY", "")
        self.api_timeout = self.get_env("API_TIMEOUT", 10, int)
        
        # Retry configuration
        self.max_retries = self.get_env("MAX_RETRIES", 3, int)
        self.retry_backoff_multiplier = self.get_env("RETRY_BACKOFF_MULTIPLIER", 1, float)
        self.retry_min_seconds = self.get_env("RETRY_MIN_SECONDS", 1, int)
        self.retry_max_seconds = self.get_env("RETRY_MAX_SECONDS", 10, int)
        
        # Logging configuration
        self.log_level = self.get_env("LOG_LEVEL", "INFO")
        self.log_dir = self.get_env("LOG_DIR", "logs")
        self.log_max_size_mb = self.get_env("LOG_MAX_SIZE_MB", 10, int)
        self.log_backup_count = self.get_env("LOG_BACKUP_COUNT", 5, int)
        
        # Profile cache configuration
        self.profile_cache_dir = self.get_env("PROFILE_CACHE_DIR", "cache/profiles")
        self.profile_cache_max_size = self.get_env("PROFILE_CACHE_MAX_SIZE", 128, int)
        self.profile_cache_expiry_hours = self.get_env("PROFILE_CACHE_EXPIRY_HOURS", 24, int)
        self.profile_cache_disk_max_size_mb = self.get_env("PROFILE_CACHE_DISK_MAX_SIZE_MB", 100, int)
        
        # Database configuration
        self.db_type = self.get_env("DB_TYPE", "sqlite")
        self.db_name = self.get_env("DB_NAME", "price_of_war.db")
        self.db_host = self.get_env("DB_HOST", "")
        self.db_port = self.get_env("DB_PORT", "")
        self.db_user = self.get_env("DB_USER", "")
        self.db_password = self.get_env("DB_PASSWORD", "")
        
        # Animation configuration
        self.animation_update_rate_hz = self.get_env("ANIMATION_UPDATE_RATE_HZ", 60, int)
        self.animation_default_duration_ms = self.get_env("ANIMATION_DEFAULT_DURATION_MS", 1000, int)
        self.animation_default_easing = self.get_env("ANIMATION_DEFAULT_EASING", "ease_out")
        
        # Price state thresholds
        self.price_state_default_price = self.get_env("PRICE_STATE_DEFAULT_PRICE", 1000, int)
        self.price_state_max_votes = self.get_env("PRICE_STATE_MAX_VOTES", 50, int)
        self.price_state_vote_divisor = self.get_env("PRICE_STATE_VOTE_DIVISOR", 100, int)
        
        # Price state direction multipliers
        self.price_state_up_multiplier = self.get_env("PRICE_STATE_UP_MULTIPLIER", 1.0, float)
        self.price_state_down_multiplier = self.get_env("PRICE_STATE_DOWN_MULTIPLIER", -1.0, float)
        self.price_state_set_multiplier = self.get_env("PRICE_STATE_SET_MULTIPLIER", 0.5, float)
        self.price_state_default_multiplier = self.get_env("PRICE_STATE_DEFAULT_MULTIPLIER", 0.0, float)
        
        # Vote weight thresholds
        self.vote_weight_max = self.get_env("VOTE_WEIGHT_MAX", 2.0, float)
        self.vote_weight_min = self.get_env("VOTE_WEIGHT_MIN", 0.1, float)
        self.vote_weight_decay_factor = self.get_env("VOTE_WEIGHT_DECAY_FACTOR", 0.8, float)
        self.vote_weight_time_decay_hours = self.get_env("VOTE_WEIGHT_TIME_DECAY_HOURS", 1, float)
        self.vote_weight_reputation_factor = self.get_env("VOTE_WEIGHT_REPUTATION_FACTOR", 0.5, float)
        
        # Vote weight calculation factors
        self.vote_weight_naughty_power = self.get_env("VOTE_WEIGHT_NAUGHTY_POWER", 0.5, float)
        self.vote_weight_nice_power = self.get_env("VOTE_WEIGHT_NICE_POWER", 2.0, float)
        self.vote_weight_lifetime_base = self.get_env("VOTE_WEIGHT_LIFETIME_BASE", 5.0, float)
        self.vote_weight_show_base = self.get_env("VOTE_WEIGHT_SHOW_BASE", 10.0, float)
        self.vote_weight_show_multiplier = self.get_env("VOTE_WEIGHT_SHOW_MULTIPLIER", 2.0, float)
        self.vote_weight_ratio_min = self.get_env("VOTE_WEIGHT_RATIO_MIN", 0.1, float)
        self.vote_weight_ratio_max = self.get_env("VOTE_WEIGHT_RATIO_MAX", 10.0, float)
        self.vote_weight_ratio_sweet_min = self.get_env("VOTE_WEIGHT_RATIO_SWEET_MIN", 0.5, float)
        self.vote_weight_ratio_sweet_max = self.get_env("VOTE_WEIGHT_RATIO_SWEET_MAX", 3.0, float)
        self.vote_weight_sweet_multiplier = self.get_env("VOTE_WEIGHT_SWEET_MULTIPLIER", 2.0, float)
        self.vote_weight_extreme_multiplier = self.get_env("VOTE_WEIGHT_EXTREME_MULTIPLIER", 0.5, float)
        
        # User reputation thresholds
        self.user_rep_nice_lifetime_votes = self.get_env("USER_REP_NICE_LIFETIME_VOTES", 500, int)
        self.user_rep_nice_show_votes = self.get_env("USER_REP_NICE_SHOW_VOTES", 100, int)
        self.user_rep_naughty_lifetime_errors = self.get_env("USER_REP_NAUGHTY_LIFETIME_ERRORS", 20, int)
        self.user_rep_naughty_show_errors = self.get_env("USER_REP_NAUGHTY_SHOW_ERRORS", 5, int)
        
        # OBS controller thresholds
        self.obs_effect_duration_up = self.get_env("OBS_EFFECT_DURATION_UP", 1500, int)
        self.obs_effect_duration_down = self.get_env("OBS_EFFECT_DURATION_DOWN", 1500, int)
        self.obs_effect_duration_set = self.get_env("OBS_EFFECT_DURATION_SET", 2000, int)
        self.obs_effect_duration_nice_glow = self.get_env("OBS_EFFECT_DURATION_NICE_GLOW", 3000, int)
        self.obs_effect_duration_naughty_glow = self.get_env("OBS_EFFECT_DURATION_NAUGHTY_GLOW", 3000, int)
        self.obs_effect_duration_user_display = self.get_env("OBS_EFFECT_DURATION_USER_DISPLAY", 4000, int)

        # Animation component durations
        self.animation_fade_in_duration = self.get_env("ANIMATION_FADE_IN_DURATION", 200, int)
        self.animation_fade_out_duration = self.get_env("ANIMATION_FADE_OUT_DURATION", 300, int)
        self.animation_scale_duration = self.get_env("ANIMATION_SCALE_DURATION", 500, int)
        self.animation_color_duration = self.get_env("ANIMATION_COLOR_DURATION", 300, int)
        self.animation_move_duration = self.get_env("ANIMATION_MOVE_DURATION", 1000, int)
        self.animation_user_display_fade = self.get_env("ANIMATION_USER_DISPLAY_FADE", 500, int)
        
        # Animation values
        self.animation_scale_max = self.get_env("ANIMATION_SCALE_MAX", 1.2, float)
        self.animation_scale_min = self.get_env("ANIMATION_SCALE_MIN", 1.0, float)
        self.animation_move_distance = self.get_env("ANIMATION_MOVE_DISTANCE", 50, int)
        self.animation_set_color_start = self.get_env("ANIMATION_SET_COLOR_START", "0.7,0.7,0.1", str)
        self.animation_set_color_end = self.get_env("ANIMATION_SET_COLOR_END", "1.0,0.8,0.0", str)
        
        # Message classification settings
        self.message_classification_temperature = self.get_env("MESSAGE_CLASSIFICATION_TEMPERATURE", 0.7, float)
        self.message_ignore_list_increment = self.get_env("MESSAGE_IGNORE_LIST_INCREMENT", 0.33, float)
        
        # User limit settings
        self.user_active_limit = self.get_env("USER_ACTIVE_LIMIT", 100, int)
        self.user_top_voters_limit = self.get_env("USER_TOP_VOTERS_LIMIT", 10, int)
        
        # Rate limiting settings
        self.rate_limit_max_tokens = self.get_env("RATE_LIMIT_MAX_TOKENS", 10.0, float)
        self.rate_limit_refill_rate = self.get_env("RATE_LIMIT_REFILL_RATE", 1.0, float)  # tokens per second
        self.rate_limit_vote_cost = self.get_env("RATE_LIMIT_VOTE_COST", 1.0, float)
        self.rate_limit_message_cost = self.get_env("RATE_LIMIT_MESSAGE_COST", 0.5, float)
        self.rate_limit_profile_cost = self.get_env("RATE_LIMIT_PROFILE_COST", 2.0, float)
        
        # Input validation settings
        self.input_max_message_length = self.get_env("INPUT_MAX_MESSAGE_LENGTH", 500, int)
        self.input_min_vote_amount = self.get_env("INPUT_MIN_VOTE_AMOUNT", 1, int)
        self.input_max_vote_amount = self.get_env("INPUT_MAX_VOTE_AMOUNT", 1000000, int)
        self.input_allowed_vote_directions = self.get_env("INPUT_ALLOWED_VOTE_DIRECTIONS", "up,down,set", str).split(',')
        self.input_max_profile_url_length = self.get_env("INPUT_MAX_PROFILE_URL_LENGTH", 2048, int)
        self.input_allowed_profile_domains = self.get_env("INPUT_ALLOWED_PROFILE_DOMAINS", "i.pravatar.cc,imgur.com", str).split(',')
        
        # OBS nice/naughty calculation factors
        self.obs_nice_lifetime_factor = self.get_env("OBS_NICE_LIFETIME_FACTOR", 0.3, float)
        self.obs_nice_show_factor = self.get_env("OBS_NICE_SHOW_FACTOR", 0.7, float)
        self.obs_nice_votes_contribution = self.get_env("OBS_NICE_VOTES_CONTRIBUTION", 0.5, float)
        self.obs_nice_votes_threshold = self.get_env("OBS_NICE_VOTES_THRESHOLD", 1000, int)
        self.obs_naughty_lifetime_factor = self.get_env("OBS_NAUGHTY_LIFETIME_FACTOR", 0.3, float)
        self.obs_naughty_show_factor = self.get_env("OBS_NAUGHTY_SHOW_FACTOR", 0.7, float)
        self.obs_naughty_errors_contribution = self.get_env("OBS_NAUGHTY_ERRORS_CONTRIBUTION", 0.5, float)

# Singleton instance
_settings = None

def get_settings() -> Settings:
    """Get or create the singleton settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
        logger.info("Settings initialized from environment")
    return _settings 
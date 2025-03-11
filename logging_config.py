import logging
import os
from logging.handlers import RotatingFileHandler
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging():
    """
    Set up logging configuration for the application
    """
    # Get configuration from environment
    log_level_name = os.getenv("LOG_LEVEL", "INFO")
    log_dir = os.getenv("LOG_DIR", "logs")
    log_max_size = int(os.getenv("LOG_MAX_SIZE_MB", "10")) * 1024 * 1024  # Convert to bytes
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # Map log level string to logging constant
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers if any (to prevent duplicate handlers when called multiple times)
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create handlers
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    # Main file handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'application.log'),
        maxBytes=log_max_size,
        backupCount=log_backup_count
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    
    # Error file handler with rotation
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=log_max_size,
        backupCount=log_backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # API file handler with rotation
    api_handler = RotatingFileHandler(
        os.path.join(log_dir, 'api_calls.log'),
        maxBytes=log_max_size,
        backupCount=log_backup_count
    )
    api_handler.setLevel(log_level)
    api_handler.setFormatter(file_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Configure module-specific loggers
    api_logger = logging.getLogger('api_client')
    api_logger.addHandler(api_handler)
    
    # Log startup information
    root_logger.info("Logging system initialized")
    root_logger.info(f"Log level set to {log_level_name}")
    
    # Return the configured root logger
    return root_logger 
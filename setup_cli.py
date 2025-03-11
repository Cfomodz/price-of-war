import sys
import subprocess
from importlib.metadata import distributions
from pathlib import Path

def check_dependencies():
    """Check and install required dependencies"""
    required = {'click', 'colorama', 'python-dotenv'}
    installed = {dist.metadata['Name'].lower() for dist in distributions()}
    missing = required - installed

    if missing:
        print("Installing required dependencies...")
        try:
            python_executable = sys.executable
            for package in missing:
                print(f"Installing {package}...")
                subprocess.check_call([python_executable, '-m', 'pip', 'install', package])
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            sys.exit(1)

# Check and install dependencies before importing
check_dependencies()

import click
import os
import json
import sqlite3
from typing import Dict, Any
import secrets
import re
from dotenv import load_dotenv
import colorama
from datetime import datetime

# Initialize colorama for Windows color support
colorama.init()

def validate_url(url: str) -> bool:
    """Validate URL format"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def validate_positive_float(value: str) -> bool:
    """Validate positive float value"""
    try:
        float_val = float(value)
        return float_val > 0
    except ValueError:
        return False

def validate_positive_int(value: str) -> bool:
    """Validate positive integer value"""
    try:
        int_val = int(value)
        return int_val > 0
    except ValueError:
        return False

class SetupWizard:
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.env_file = Path('.env')
        self.db_file = Path('price_of_war.db')
        self.backup_dir = Path('backups')
        
    def create_backup(self):
        """Create backup of existing configuration"""
        if self.env_file.exists():
            self.backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f".env.backup_{timestamp}"
            self.env_file.rename(backup_file)
            click.echo(f"Created backup at {backup_file}")
        
    def load_existing_config(self):
        """Load existing configuration if available"""
        if self.env_file.exists():
            load_dotenv()
            # Load existing values into config
            for key in os.environ:
                if key.startswith(('API_', 'DB_', 'RATE_', 'INPUT_', 'OBS_', 'LOG_', 'PROFILE_')):
                    self.config[key] = os.environ[key]

    def prompt_api_settings(self):
        """Prompt for API settings"""
        click.secho("\n=== API Configuration ===", fg='green', bold=True)
        
        self.config['API_ENDPOINT'] = click.prompt(
            "API Endpoint",
            default=self.config.get('API_ENDPOINT', 'https://api.deepseek.com/v1/classify')
        )
        while not validate_url(self.config['API_ENDPOINT']):
            click.secho("Invalid URL format. Please enter a valid URL.", fg='red')
            self.config['API_ENDPOINT'] = click.prompt("API Endpoint")

        self.config['API_KEY'] = click.prompt(
            "API Key",
            default=self.config.get('API_KEY', secrets.token_urlsafe(32)),
            hide_input=True
        )
        
        self.config['API_TIMEOUT'] = click.prompt(
            "API Timeout (seconds)",
            default=self.config.get('API_TIMEOUT', '10')
        )

    def prompt_database_settings(self):
        """Prompt for database settings"""
        click.secho("\n=== Database Configuration ===", fg='green', bold=True)
        
        db_types = ['sqlite', 'postgresql', 'mysql']
        db_type = click.prompt(
            "Database type",
            type=click.Choice(db_types),
            default=self.config.get('DB_TYPE', 'sqlite')
        )
        self.config['DB_TYPE'] = db_type

        if db_type == 'sqlite':
            self.config['DB_NAME'] = click.prompt(
                "Database file name",
                default=self.config.get('DB_NAME', 'price_of_war.db')
            )
        else:
            self.config['DB_HOST'] = click.prompt(
                "Database host",
                default=self.config.get('DB_HOST', 'localhost')
            )
            self.config['DB_PORT'] = click.prompt(
                "Database port",
                default=self.config.get('DB_PORT', '5432' if db_type == 'postgresql' else '3306')
            )
            self.config['DB_NAME'] = click.prompt(
                "Database name",
                default=self.config.get('DB_NAME', 'price_of_war')
            )
            self.config['DB_USER'] = click.prompt(
                "Database user",
                default=self.config.get('DB_USER', 'postgres' if db_type == 'postgresql' else 'root')
            )
            self.config['DB_PASSWORD'] = click.prompt(
                "Database password",
                hide_input=True,
                default=self.config.get('DB_PASSWORD', '')
            )

    def prompt_logging_settings(self):
        """Prompt for logging settings"""
        click.secho("\n=== Logging Configuration ===", fg='green', bold=True)
        
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.config['LOG_LEVEL'] = click.prompt(
            "Log level",
            type=click.Choice(log_levels),
            default=self.config.get('LOG_LEVEL', 'INFO')
        )
        
        self.config['LOG_DIR'] = click.prompt(
            "Log directory",
            default=self.config.get('LOG_DIR', 'logs')
        )
        
        self.config['LOG_MAX_SIZE_MB'] = click.prompt(
            "Maximum log file size (MB)",
            default=self.config.get('LOG_MAX_SIZE_MB', '10')
        )
        
        self.config['LOG_BACKUP_COUNT'] = click.prompt(
            "Number of log backups to keep",
            default=self.config.get('LOG_BACKUP_COUNT', '5')
        )

    def prompt_rate_limit_settings(self):
        """Prompt for rate limit settings"""
        click.secho("\n=== Rate Limiting Configuration ===", fg='green', bold=True)
        
        self.config['RATE_LIMIT_MAX_TOKENS'] = click.prompt(
            "Maximum rate limit tokens",
            default=self.config.get('RATE_LIMIT_MAX_TOKENS', '10.0')
        )
        while not validate_positive_float(self.config['RATE_LIMIT_MAX_TOKENS']):
            click.secho("Please enter a positive number.", fg='red')
            self.config['RATE_LIMIT_MAX_TOKENS'] = click.prompt("Maximum rate limit tokens")

        self.config['RATE_LIMIT_REFILL_RATE'] = click.prompt(
            "Token refill rate per second",
            default=self.config.get('RATE_LIMIT_REFILL_RATE', '1.0')
        )
        while not validate_positive_float(self.config['RATE_LIMIT_REFILL_RATE']):
            click.secho("Please enter a positive number.", fg='red')
            self.config['RATE_LIMIT_REFILL_RATE'] = click.prompt("Token refill rate per second")

    def prompt_input_validation_settings(self):
        """Prompt for input validation settings"""
        click.secho("\n=== Input Validation Configuration ===", fg='green', bold=True)
        
        self.config['INPUT_MAX_MESSAGE_LENGTH'] = click.prompt(
            "Maximum message length",
            default=self.config.get('INPUT_MAX_MESSAGE_LENGTH', '500')
        )
        while not validate_positive_int(self.config['INPUT_MAX_MESSAGE_LENGTH']):
            click.secho("Please enter a positive integer.", fg='red')
            self.config['INPUT_MAX_MESSAGE_LENGTH'] = click.prompt("Maximum message length")

        self.config['INPUT_MIN_VOTE_AMOUNT'] = click.prompt(
            "Minimum vote amount",
            default=self.config.get('INPUT_MIN_VOTE_AMOUNT', '1')
        )
        while not validate_positive_int(self.config['INPUT_MIN_VOTE_AMOUNT']):
            click.secho("Please enter a positive integer.", fg='red')
            self.config['INPUT_MIN_VOTE_AMOUNT'] = click.prompt("Minimum vote amount")

    def save_configuration(self):
        """Save configuration to .env file"""
        with open(self.env_file, 'w') as f:
            f.write("# Price of War Configuration\n")
            f.write(f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Group settings by category
            categories = {
                'API Settings': ['API_'],
                'Database Settings': ['DB_'],
                'Rate Limiting': ['RATE_'],
                'Input Validation': ['INPUT_'],
                'Logging': ['LOG_']
            }
            
            for category, prefixes in categories.items():
                f.write(f"\n# {category}\n")
                for key in sorted(self.config.keys()):
                    if any(key.startswith(prefix) for prefix in prefixes):
                        f.write(f"{key}={self.config[key]}\n")
                        
        click.secho(f"\nConfiguration saved to {self.env_file}", fg='green')

    def initialize_database(self):
        """Initialize the database"""
        if self.config['DB_TYPE'] == 'sqlite':
            if not self.db_file.exists():
                try:
                    conn = sqlite3.connect(self.config['DB_NAME'])
                    conn.close()
                    click.secho(f"\nInitialized SQLite database at {self.config['DB_NAME']}", fg='green')
                except Exception as e:
                    click.secho(f"Error initializing database: {e}", fg='red')
            else:
                click.secho("\nDatabase file already exists", fg='yellow')

    def verify_configuration(self):
        """Verify the configuration"""
        click.secho("\n=== Configuration Summary ===", fg='green', bold=True)
        
        # Display non-sensitive settings
        safe_keys = [k for k in self.config.keys() if 'PASSWORD' not in k and 'KEY' not in k]
        for key in sorted(safe_keys):
            click.echo(f"{key}: {self.config[key]}")
        
        # Display masked sensitive settings
        sensitive_keys = [k for k in self.config.keys() if 'PASSWORD' in k or 'KEY' in k]
        for key in sorted(sensitive_keys):
            click.echo(f"{key}: {'*' * 8}")

        if not click.confirm("\nDoes this configuration look correct?"):
            if click.confirm("Would you like to start over?"):
                self.config.clear()
                self.run()
            else:
                sys.exit(1)

@click.command()
@click.option('--non-interactive', is_flag=True, help='Use default values without prompting')
@click.option('--backup/--no-backup', default=True, help='Create backup of existing configuration')
@click.option('--skip-db-init', is_flag=True, help='Skip database initialization')
@click.option('--config-file', type=click.Path(), help='Load configuration from JSON file')
def setup(non_interactive, backup, skip_db_init, config_file):
    """Interactive setup wizard for Price of War application"""
    wizard = SetupWizard()
    
    click.secho("Welcome to the Price of War Setup Wizard!", fg='green', bold=True)
    
    # Check for existing configuration
    if wizard.env_file.exists():
        if backup:
            wizard.create_backup()
        if not non_interactive and not click.confirm("Existing configuration found. Would you like to modify it?"):
            click.echo("Setup cancelled. Existing configuration retained.")
            return
        wizard.load_existing_config()
    
    # Load configuration from file if specified
    if config_file:
        try:
            with open(config_file) as f:
                wizard.config.update(json.load(f))
            click.secho(f"Loaded configuration from {config_file}", fg='green')
        except Exception as e:
            click.secho(f"Error loading configuration file: {e}", fg='red')
            sys.exit(1)
    
    if non_interactive:
        # Use defaults or existing values
        wizard.config.setdefault('API_ENDPOINT', 'https://api.deepseek.com/v1/classify')
        wizard.config.setdefault('API_KEY', secrets.token_urlsafe(32))
        wizard.config.setdefault('API_TIMEOUT', '10')
        wizard.config.setdefault('DB_TYPE', 'sqlite')
        wizard.config.setdefault('DB_NAME', 'price_of_war.db')
        wizard.config.setdefault('LOG_LEVEL', 'INFO')
        wizard.config.setdefault('LOG_DIR', 'logs')
        wizard.config.setdefault('RATE_LIMIT_MAX_TOKENS', '10.0')
        wizard.config.setdefault('RATE_LIMIT_REFILL_RATE', '1.0')
        wizard.config.setdefault('INPUT_MAX_MESSAGE_LENGTH', '500')
        wizard.config.setdefault('INPUT_MIN_VOTE_AMOUNT', '1')
    else:
        # Interactive configuration
        wizard.prompt_api_settings()
        wizard.prompt_database_settings()
        wizard.prompt_logging_settings()
        wizard.prompt_rate_limit_settings()
        wizard.prompt_input_validation_settings()
        wizard.verify_configuration()
    
    # Save configuration
    wizard.save_configuration()
    
    # Initialize database if needed
    if not skip_db_init:
        wizard.initialize_database()
    
    click.secho("\nSetup complete! You can now start the application.", fg='green', bold=True)

if __name__ == '__main__':
    setup() 
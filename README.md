# Price of War

An interactive pricing system for livestreams where viewers can influence the price of an item through chat messages and votes.

## Overview

Price of War is a system that processes messages from chat to allow viewers to influence the price of an item in real-time. The system:

1. Classifies chat messages to detect vote intent (up, down, or set a specific price)
2. Applies votes to the item price with weights based on user reputation
3. Displays visual effects in OBS based on votes
4. Tracks user statistics to build reputation

## Features

- Message classification to detect vote intent
- User reputation tracking (lifetime and per-show)
- Vote weighting based on user history
- Visual feedback in OBS for votes
- Profile picture animations based on user status (nice/naughty)
- Rate limiting to prevent spam
- Database storage of user statistics

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file (you can copy from `.env.example` and modify)
4. Initialize the database:
   ```
   python setup_cli.py
   ```

## Running Tests

Run all tests:
```
pytest -v --cov --cov-report=term-missing
```

Run a specific test file:
```
pytest test_price_state.py -v
```

Run a specific test:
```
pytest test_price_state.py::TestPriceState::test_upvote -v
```

## Running the Demo

The project includes a demonstration script to show the system in action:

```
# Run automated demo for 60 seconds
python run_demo.py --mode automated --duration 60

# Run interactive demo
python run_demo.py --mode interactive
```

## Running the Application

To run the full application:

```
python main.py
```

This will start the processing system that can be connected to your streaming platform via a WebSocket connector (extension).

## Components

- **api_client.py**: Interface to the message classification API
- **database.py**: Database operations for user statistics
- **input_validator.py**: Input validation for votes and messages
- **main.py**: Main application logic and message processing
- **message_classification.py**: Chat message intent classification
- **price_state.py**: Price state management and vote application
- **rate_limiter.py**: Rate limiting for API calls and user actions
- **user_rep.py**: User reputation and statistics tracking
- **animation_manager.py**: Animation orchestration and timing
- **obs_controller.py**: OBS Studio integration for visual effects

## Configuration

The system is configured through environment variables, which can be set in a `.env` file. See `.env.example` for all available options.

## License

See the LICENSE file for details.
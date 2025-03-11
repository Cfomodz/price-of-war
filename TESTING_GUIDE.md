# Testing Guide for Price of War

This document provides guidance on testing the Price of War application.

## Setup for Testing

1. Install testing dependencies:
   ```
   pip install pytest pytest-asyncio pytest-cov pytest-mock freezegun hypothesis
   ```

2. Ensure you have a `.env` file with test configuration (you can use the `.env` we created)

3. Run tests from the project root directory

## Test Files

The project includes the following test files:

1. **test_database.py** - Tests for database operations and user statistics repository
2. **test_calculations.py** - Tests for rate limiting, input validation, and vote weight calculations
3. **test_price_state.py** - Tests for price state management and vote application
4. **test_message_classification.py** - Tests for message classification with mocked API responses
5. **test_main_integration.py** - Integration tests for the main processor

## Running Tests

### Running All Tests

To run all tests with coverage reporting:

```
python -m pytest -v --cov --cov-report=term-missing
```

### Running Specific Tests

To run tests from a specific file:

```
python -m pytest test_price_state.py -v
```

To run a specific test:

```
python -m pytest test_price_state.py::TestPriceState::test_upvote -v
```

### Running Tests with Parallelism

To run tests in parallel (faster for large test suites):

```
python -m pytest -v -n auto
```

## Demonstration Script

The `run_demo.py` script demonstrates the system in action. It provides two modes:

1. **Automated Demo**:
   ```
   python run_demo.py --mode automated --duration 60
   ```
   This runs a simulation for 60 seconds with automated votes from demo users.

2. **Interactive Demo**:
   ```
   python run_demo.py --mode interactive
   ```
   This allows you to input messages and see the system's response.

## Mock Strategy

When testing:

1. For unit tests, we mock dependencies like:
   - API clients
   - Database connections
   - External services

2. For integration tests, we test multiple components working together:
   - Processor with real price state but mocked user manager and OBS controller
   - Full message processing pipeline with mocked API calls

3. For manual testing, use the demo script.

## Test Coverage

The tests aim to cover:

1. **Core Functionality**:
   - Price calculation with different vote types
   - User reputation tracking
   - Message classification logic
   - Vote weighting algorithms

2. **Edge Cases**:
   - Error handling
   - Rate limiting
   - Invalid inputs
   - Extreme vote values

3. **Integration Points**:
   - How modules interact with each other
   - Full processing pipeline
   - Initialization and shutdown procedures
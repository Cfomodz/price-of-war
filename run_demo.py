#!/usr/bin/env python3
import asyncio
import logging
import random
import argparse
import time
from datetime import datetime
from logging_config import setup_logging
from main import NYPProcessor, ValidationError, RateLimitError
from user_rep import UserStats
from animation_manager import get_animation_manager, close_animation_manager
from profile_cache import get_profile_cache, close_profile_cache
from database import get_db_manager, close_database

# Initialize logging
logger = setup_logging()

# Demo user data
DEMO_USERS = [
    {
        "user_id": "alice_123",
        "name": "Alice",
        "profile_url": "https://i.pravatar.cc/150?img=1",
        "vote_style": "optimistic"  # Tends to vote up
    },
    {
        "user_id": "bob_456",
        "name": "Bob",
        "profile_url": "https://i.pravatar.cc/150?img=2",
        "vote_style": "pessimistic"  # Tends to vote down
    },
    {
        "user_id": "charlie_789",
        "name": "Charlie",
        "profile_url": "https://i.pravatar.cc/150?img=3",
        "vote_style": "balanced"  # Votes both ways
    },
    {
        "user_id": "diana_012",
        "name": "Diana",
        "profile_url": "https://i.pravatar.cc/150?img=4",
        "vote_style": "extreme"  # Makes extreme votes
    },
    {
        "user_id": "evan_345",
        "name": "Evan",
        "profile_url": "https://i.pravatar.cc/150?img=5",
        "vote_style": "setter"  # Likes to set prices
    }
]

# Demo vote messages
VOTE_MESSAGES = {
    "up": [
        "Price should be higher!",
        "That's worth more",
        "I'd pay more than that",
        "Too cheap, raise it",
        "Definitely underpriced, go up 20%"
    ],
    "down": [
        "Price is too high",
        "That should be cheaper",
        "Lower the price",
        "Too expensive for what it is",
        "Needs to come down at least 15%"
    ],
    "set": [
        "That should be exactly $VALUE",
        "Price it at $VALUE",
        "I think $VALUE is fair",
        "Set it to $VALUE",
        "$VALUE is the right price"
    ]
}

async def setup_users(processor):
    """Set up demo users with profiles"""
    logger.info("Setting up demo users")
    
    # Initialize profile pictures for all users
    for user in DEMO_USERS:
        logger.info(f"Setting up user {user['name']}")
        
        # Update user profile
        await processor.update_profile_picture(user['user_id'], user['profile_url'])
        
        # Cast a couple votes to establish reputation
        for _ in range(3):
            direction = get_vote_direction(user['vote_style'])
            amount = get_vote_amount(direction, processor.price_state.current_price, user['vote_style'])
            
            try:
                await processor.process_vote(user['user_id'], direction, amount)
                logger.info(f"{user['name']} voted {direction} with amount {amount}")
            except (ValidationError, RateLimitError) as e:
                logger.warning(f"Error processing vote: {str(e)}")
            
            # Small delay between votes
            await asyncio.sleep(0.2)
    
    logger.info("Demo users setup complete")

def get_vote_direction(vote_style):
    """Get a vote direction based on user's voting style"""
    if vote_style == "optimistic":
        return random.choices(["up", "down", "set"], weights=[0.7, 0.2, 0.1])[0]
    elif vote_style == "pessimistic":
        return random.choices(["up", "down", "set"], weights=[0.2, 0.7, 0.1])[0]
    elif vote_style == "balanced":
        return random.choices(["up", "down", "set"], weights=[0.45, 0.45, 0.1])[0]
    elif vote_style == "extreme":
        return random.choices(["up", "down", "set"], weights=[0.4, 0.4, 0.2])[0]
    elif vote_style == "setter":
        return random.choices(["up", "down", "set"], weights=[0.3, 0.3, 0.4])[0]
    else:
        return random.choice(["up", "down", "set"])

def get_vote_amount(direction, current_price, vote_style):
    """Get a vote amount based on direction and user's voting style"""
    if direction == "set":
        if vote_style == "extreme":
            # More extreme price adjustments
            adjustment = random.uniform(0.5, 2.0)
        else:
            # More moderate price adjustments
            adjustment = random.uniform(0.8, 1.2)
        
        return int(current_price * adjustment)
    else:
        # For up/down votes, just return current price (weight will be applied later)
        return current_price

def get_vote_message(user, direction, amount, current_price):
    """Generate a message corresponding to vote intent"""
    message = random.choice(VOTE_MESSAGES[direction])
    
    # Replace $VALUE placeholder with actual amount
    if direction == "set":
        # Convert cents to dollars for display
        dollars = amount / 100
        message = message.replace("$VALUE", f"${dollars:.2f}")
    
    return f"{user['name']}: {message}"

async def simulate_chat_message(processor, user, current_price):
    """Simulate a chat message that might be a vote"""
    direction = get_vote_direction(user['vote_style'])
    amount = get_vote_amount(direction, current_price, user['vote_style'])
    message = get_vote_message(user, direction, amount, current_price)
    
    logger.info(f"User message: {message}")
    
    # In a real implementation, we would call the message classification API
    # For this demo, we'll directly process the vote instead of classifying
    try:
        # For demonstration, directly process the vote
        result = await processor.process_vote(user['user_id'], direction, amount)
        logger.info(f"Vote processed: {result}")
        return result
    except (ValidationError, RateLimitError) as e:
        logger.warning(f"Error processing vote: {str(e)}")
        return None

def display_price_update(new_price, old_price):
    """Display price update in a visually interesting way"""
    change = new_price - old_price
    percent = (change / old_price) * 100
    
    # Convert cents to dollars for display
    new_dollars = new_price / 100
    old_dollars = old_price / 100
    
    # Create visual indicator
    if change > 0:
        indicator = f"↑ ${new_dollars:.2f} (+{percent:.1f}%)"
        print(f"\033[92m{indicator}\033[0m")  # Green
    elif change < 0:
        indicator = f"↓ ${new_dollars:.2f} ({percent:.1f}%)"
        print(f"\033[91m{indicator}\033[0m")  # Red
    else:
        indicator = f"→ ${new_dollars:.2f} (0.0%)"
        print(f"\033[93m{indicator}\033[0m")  # Yellow

async def run_interactive_demo():
    """Run an interactive demo where user can input messages"""
    processor = None
    
    try:
        # Initialize processor
        logger.info("Starting interactive demo")
        
        # Initialize animation manager first (needed by OBS controller)
        animation_manager = get_animation_manager()
        await animation_manager.start()
        logger.info("Animation manager initialized")
        
        # Initialize database
        db_manager = get_db_manager()
        logger.info("Database initialized")
        
        # Initialize cache
        _ = get_profile_cache()
        logger.info("Profile cache initialized")
        
        # Create and initialize processor
        processor = NYPProcessor()
        await processor.initialize()
        
        # Display initial price
        current_price = processor.price_state.current_price
        print(f"\nCurrent price: ${current_price/100:.2f}")
        
        # Setup demo users
        await setup_users(processor)
        
        # Interactive loop
        print("\n=== Interactive Price of War Demo ===")
        print("Enter messages to simulate chat. Type 'exit' to quit.")
        print("Format: <user_index>|<message>  (e.g. '0|price is too high')")
        print(f"Available users: {', '.join([f'{i}:{user['name']}' for i, user in enumerate(DEMO_USERS)])}")
        
        while True:
            user_input = input("\nEnter message ('exit' to quit): ")
            
            if user_input.lower() == 'exit':
                break
            
            try:
                # Parse input format
                if '|' in user_input:
                    user_idx_str, message = user_input.split('|', 1)
                    user_idx = int(user_idx_str)
                    user = DEMO_USERS[user_idx]
                else:
                    # Default to random user if no user specified
                    user = random.choice(DEMO_USERS)
                    message = user_input
                
                # Process message
                old_price = processor.price_state.current_price
                
                # For demo purposes, directly process as an upvote
                direction = "up"  # Default to up for simplicity
                result = await processor.process_vote(user['user_id'], direction, old_price)
                
                # Display result
                if result:
                    new_price = processor.price_state.current_price
                    print(f"\n{user['name']} submitted: {message}")
                    
                    if 'new_price' in result:
                        display_price_update(new_price, old_price)
                    else:
                        print(f"Result: {result}")
                else:
                    print("Message did not result in a vote or action")
                
            except (ValueError, IndexError) as e:
                print(f"Invalid input format: {str(e)}")
            except Exception as e:
                print(f"Error processing message: {str(e)}")
        
    except Exception as e:
        logger.error(f"Demo error: {str(e)}", exc_info=True)
    finally:
        # Perform cleanup
        logger.info("Shutting down demo")
        
        if processor:
            await processor.close()
            
        # Close animation manager
        await close_animation_manager()
        
        # Close profile cache
        await close_profile_cache()
        
        # Close database
        close_database()
        
        logger.info("Demo shutdown complete")

async def run_automated_demo(duration=60, vote_interval=3):
    """Run an automated demo with simulated votes for a specified duration"""
    processor = None
    
    try:
        # Initialize processor
        logger.info(f"Starting automated demo for {duration} seconds")
        
        # Initialize animation manager first (needed by OBS controller)
        animation_manager = get_animation_manager()
        await animation_manager.start()
        logger.info("Animation manager initialized")
        
        # Initialize database
        db_manager = get_db_manager()
        logger.info("Database initialized")
        
        # Initialize cache
        _ = get_profile_cache()
        logger.info("Profile cache initialized")
        
        # Create and initialize processor
        processor = NYPProcessor()
        await processor.initialize()
        
        # Display initial price
        current_price = processor.price_state.current_price
        print(f"\nStarting price: ${current_price/100:.2f}")
        
        # Setup demo users
        await setup_users(processor)
        
        # Automated voting loop
        print(f"\n=== Automated Price of War Demo ({duration}s) ===")
        print(f"Vote interval: ~{vote_interval} seconds")
        
        start_time = time.time()
        end_time = start_time + duration
        
        while time.time() < end_time:
            # Select random user
            user = random.choice(DEMO_USERS)
            
            # Generate vote
            direction = get_vote_direction(user['vote_style'])
            amount = get_vote_amount(direction, processor.price_state.current_price, user['vote_style'])
            
            # Process vote
            old_price = processor.price_state.current_price
            
            try:
                result = await processor.process_vote(user['user_id'], direction, amount)
                
                # Display result
                message = get_vote_message(user, direction, amount, old_price)
                print(f"\n{message}")
                
                if result['status'] == 'success':
                    new_price = result['new_price']
                    display_price_update(new_price, old_price)
                else:
                    print(f"Vote result: {result['status']}")
                
            except (ValidationError, RateLimitError) as e:
                print(f"Error processing vote: {str(e)}")
            
            # Random interval between votes (average = vote_interval)
            sleep_time = random.uniform(vote_interval * 0.5, vote_interval * 1.5)
            remaining = end_time - time.time()
            await asyncio.sleep(min(sleep_time, remaining))
        
        # Display final price
        final_price = processor.price_state.current_price
        print(f"\nFinal price after {duration} seconds: ${final_price/100:.2f}")
        print(f"Change from starting price: ${(final_price-current_price)/100:.2f}")
        
    except Exception as e:
        logger.error(f"Demo error: {str(e)}", exc_info=True)
    finally:
        # Perform cleanup
        logger.info("Shutting down demo")
        
        if processor:
            await processor.close()
            
        # Close animation manager
        await close_animation_manager()
        
        # Close profile cache
        await close_profile_cache()
        
        # Close database
        close_database()
        
        logger.info("Demo shutdown complete")

if __name__ == "__main__":
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Price of War Demo")
    parser.add_argument('--mode', choices=['interactive', 'automated'], default='automated',
                      help='Demo mode: interactive or automated')
    parser.add_argument('--duration', type=int, default=60,
                      help='Duration of automated demo in seconds')
    parser.add_argument('--interval', type=int, default=3,
                      help='Average interval between votes in automated mode')
    
    args = parser.parse_args()
    
    # Run appropriate demo
    if args.mode == 'interactive':
        asyncio.run(run_interactive_demo())
    else:
        asyncio.run(run_automated_demo(args.duration, args.interval))
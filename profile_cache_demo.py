import asyncio
import time
import os
import logging
from datetime import datetime
from profile_cache import get_profile_cache, close_profile_cache
from logging_config import setup_logging
from user_rep import UserManager
import random
import string

# Initialize logging
logger = setup_logging()

# Demo user IDs - for demonstration
DEMO_USERS = [
    "user1",
    "user2",
    "user3",
    "user4",
    "user5"
]

# Demo profile URLs - would be fetched from API in real application
DEMO_URLS = [
    "https://i.pravatar.cc/150?img=1",
    "https://i.pravatar.cc/150?img=2",
    "https://i.pravatar.cc/150?img=3",
    "https://i.pravatar.cc/150?img=4",
    "https://i.pravatar.cc/150?img=5",
]

async def demo_cache_operations():
    """Demonstrate cache operations with various patterns"""
    logger.info("Starting profile cache demonstration")
    
    # Initialize user manager
    user_manager = UserManager()
    
    # Set profile picture URLs
    for i, user_id in enumerate(DEMO_USERS):
        await user_manager.set_user_profile_picture_url(user_id, DEMO_URLS[i % len(DEMO_URLS)])
    
    # Simulate app startup - preload all profile pictures
    logger.info("Simulating app startup - preloading all profile pictures")
    start_time = time.time()
    await user_manager.preload_profile_pictures(DEMO_USERS)
    logger.info(f"Initial load of {len(DEMO_USERS)} profile pictures took {time.time() - start_time:.2f} seconds")
    
    # Simulate random profile picture requests (should hit cache)
    logger.info("Simulating random profile access (should hit cache)")
    total_time = 0
    iterations = 20
    
    for i in range(iterations):
        user_id = random.choice(DEMO_USERS)
        start_time = time.time()
        profile_data = await user_manager.get_user_profile_picture(user_id)
        request_time = time.time() - start_time
        total_time += request_time
        
        logger.info(f"Request {i+1}: Loaded profile for {user_id} in {request_time:.4f} seconds")
        
        # Small delay to simulate app activity
        await asyncio.sleep(0.1)
    
    logger.info(f"Average cache hit time: {total_time/iterations:.4f} seconds")
    
    # Simulate cache invalidation
    user_to_update = DEMO_USERS[0]
    logger.info(f"Simulating profile picture update for {user_to_update}")
    new_url = f"https://i.pravatar.cc/150?img=10&u={int(time.time())}"
    await user_manager.set_user_profile_picture_url(user_to_update, new_url)
    
    # Load the updated profile
    start_time = time.time()
    profile_data = await user_manager.get_user_profile_picture(user_to_update)
    logger.info(f"Updated profile loaded in {time.time() - start_time:.4f} seconds (should be slower as cache was invalidated)")
    
    # Generate many random users to test cache eviction
    logger.info("Testing cache eviction with many random users")
    random_users = []
    
    for i in range(150):  # More than the cache max size
        user_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        random_users.append(user_id)
    
    # Load profiles for random users (should cause cache eviction)
    for user_id in random_users:
        await user_manager.get_user_profile_picture(user_id)
    
    logger.info(f"Loaded {len(random_users)} random user profiles to test cache eviction")
    
    # Check if original users are still cached by measuring access time
    logger.info("Testing if original users are still in cache")
    total_time = 0
    
    for user_id in DEMO_USERS:
        start_time = time.time()
        await user_manager.get_user_profile_picture(user_id)
        access_time = time.time() - start_time
        total_time += access_time
        logger.info(f"Access time for {user_id}: {access_time:.4f} seconds")
    
    logger.info(f"Average access time after eviction test: {total_time/len(DEMO_USERS):.4f} seconds")
    
    # Close cache
    await close_profile_cache()
    
    logger.info("Profile cache demonstration completed")

async def main():
    try:
        await demo_cache_operations()
    except Exception as e:
        logger.error(f"Error in demo: {str(e)}", exc_info=True)
    finally:
        await close_profile_cache()

if __name__ == "__main__":
    asyncio.run(main()) 
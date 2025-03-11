import asyncio
import time
import random
import string
import logging
from datetime import datetime, timedelta
from database import get_db_manager, get_user_stats_repository, close_database
from user_rep import UserManager, UserStats
from logging_config import setup_logging

# Initialize logging
logger = setup_logging()

async def generate_demo_users(user_manager, count=20):
    """Generate demo users with random statistics"""
    logger.info(f"Generating {count} demo users")
    
    for i in range(count):
        # Create random user ID
        user_id = f"user_{i+1}" if i < 5 else ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # Get or create user
        user = user_manager.get_user(user_id)
        
        # Set random statistics
        user.lifetime_votes = random.randint(0, 1000)
        user.show_votes = random.randint(0, user.lifetime_votes)
        user.erroneous_votes = random.randint(0, min(50, user.lifetime_votes // 10))
        user.show_erroneous = random.randint(0, user.erroneous_votes)
        
        # Set last vote time to a random time in the past week
        days_ago = random.randint(0, 7)
        user.last_vote_time = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        # Set naughty/nice status
        user.naughty_status = {
            "lifetime": user.erroneous_votes > 20,
            "show": user.show_erroneous > 5
        }
        user.nice_status = {
            "lifetime": user.lifetime_votes > 500,
            "show": user.show_votes > 100
        }
        
        # Set random profile picture URL
        user.profile_picture_url = f"https://i.pravatar.cc/150?u={user_id}"
        
        # Save to database
        user_manager.update_user_stats(user)
        
    logger.info(f"Generated and saved {count} demo users")

async def demo_database_operations():
    """Demonstrate database operations with user statistics"""
    logger.info("Starting database demonstration")
    
    # Initialize user manager with database connection
    user_manager = UserManager()
    repo = get_user_stats_repository()
    
    # Generate demo users if not exist
    users_count = len(repo.get_all_users())
    if users_count < 5:
        await generate_demo_users(user_manager)
    else:
        logger.info(f"Database already contains {users_count} users, skipping generation")
    
    # Demonstrate loading all users
    await user_manager.load_all_users()
    
    # Demonstrate getting a specific user
    test_user_id = "user_1"
    test_user = user_manager.get_user(test_user_id)
    logger.info(f"Retrieved user {test_user_id}: votes={test_user.lifetime_votes}, "
                f"last_vote={test_user.last_vote_time}")
    
    # Demonstrate updating a user
    test_user.lifetime_votes += 1
    test_user.last_vote_time = datetime.now()
    user_manager.update_user_stats(test_user)
    logger.info(f"Updated user {test_user_id}: votes={test_user.lifetime_votes}, "
                f"last_vote={test_user.last_vote_time}")
    
    # Demonstrate getting top voters
    top_voters = user_manager.get_top_voters(limit=5)
    logger.info("Top 5 voters:")
    for i, user in enumerate(top_voters, 1):
        logger.info(f"{i}. {user.user_id}: {user.lifetime_votes} votes")
    
    # Demonstrate loading active users
    await user_manager.load_active_users(limit=5)
    logger.info("Recently active users loaded")
    
    # Demonstrate deleting a user
    random_user_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    random_user = user_manager.get_user(random_user_id)
    random_user.lifetime_votes = 1
    user_manager.update_user_stats(random_user)
    logger.info(f"Created temporary user {random_user_id}")
    
    # Delete the user
    deleted = user_manager.delete_user(random_user_id)
    logger.info(f"Deleted user {random_user_id}: {deleted}")
    
    logger.info("Database demonstration completed")

async def main():
    try:
        # Initialize database
        db_manager = get_db_manager()
        
        # Run database demo
        await demo_database_operations()
    except Exception as e:
        logger.error(f"Error in database demo: {str(e)}", exc_info=True)
    finally:
        # Close database connections
        close_database()

if __name__ == "__main__":
    asyncio.run(main()) 
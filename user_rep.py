from datetime import datetime
from math import log
from typing import Dict, Optional, List, Any
from pydantic import BaseModel
import logging
import asyncio
from profile_cache import get_profile_cache
from database import get_user_stats_repository
from settings import get_settings

logger = logging.getLogger("user_manager")

class UserStats(BaseModel):
    user_id: str
    lifetime_votes: int = 0
    show_votes: int = 0
    erroneous_votes: int = 0
    show_erroneous: int = 0
    last_vote_time: Optional[datetime] = None
    naughty_status: Dict[str, bool] = {"lifetime": False, "show": False}
    nice_status: Dict[str, bool] = {"lifetime": False, "show": False}
    profile_picture_url: Optional[str] = None
    
    async def get_profile_picture(self) -> Optional[bytes]:
        """Get the user's profile picture data"""
        cache = get_profile_cache()
        return await cache.get_profile_picture(self.user_id, self.profile_picture_url)
    
    async def set_profile_picture_url(self, url: str) -> None:
        """Set a new profile picture URL and invalidate cache"""
        if url != self.profile_picture_url:
            old_url = self.profile_picture_url
            self.profile_picture_url = url
            
            # Invalidate cache if URL changed
            if old_url:
                cache = get_profile_cache()
                await cache.invalidate(self.user_id)
                logger.info(f"Profile picture URL changed for user {self.user_id}, cache invalidated")
            
            # Save the updated URL to database
            self._save_to_db()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "user_id": self.user_id,
            "lifetime_votes": self.lifetime_votes,
            "show_votes": self.show_votes,
            "erroneous_votes": self.erroneous_votes,
            "show_erroneous": self.show_erroneous,
            "last_vote_time": self.last_vote_time,
            "naughty_status": self.naughty_status,
            "nice_status": self.nice_status,
            "profile_picture_url": self.profile_picture_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserStats':
        """Create from dictionary loaded from database"""
        return cls(**data)
    
    def _save_to_db(self) -> bool:
        """Save user stats to database"""
        try:
            repo = get_user_stats_repository()
            return repo.save_user_stats(self.to_dict())
        except Exception as e:
            logger.error(f"Error saving user stats to database: {str(e)}")
            return False

class UserManager:
    def __init__(self):
        self.users: Dict[str, UserStats] = {}
        self.logger = logger
        self.repository = get_user_stats_repository()
        self.cache_loaded = False
    
    async def load_all_users(self) -> None:
        """Load all users from database into memory cache"""
        if self.cache_loaded:
            return
            
        try:
            self.logger.info("Loading all users from database")
            all_users = self.repository.get_all_users()
            
            # Initialize memory cache
            for user_data in all_users:
                self.users[user_data["user_id"]] = UserStats.from_dict(user_data)
                
            self.cache_loaded = True
            self.logger.info(f"Loaded {len(all_users)} users from database")
        except Exception as e:
            self.logger.error(f"Error loading users from database: {str(e)}")
    
    async def load_active_users(self, limit: int = None) -> None:
        """Load active users from database"""
        if limit is None:
            limit = get_settings().user_active_limit
            
        self.logger.info(f"Loading most active {limit} users from database")
        active_users = self.repository.get_recent_active_users(limit)
        
        # Update cache with active users
        for user_data in active_users:
            user = UserStats(**user_data)
            self.users[user.user_id] = user
            
        self.logger.info(f"Loaded {len(active_users)} active users")
    
    def get_user(self, user_id: str) -> UserStats:
        """Get a user by ID, creating if not exists"""
        # Check if in memory cache
        if user_id in self.users:
            return self.users[user_id]
        
        # Try to load from database
        try:
            user_data = self.repository.get_user_stats(user_id)
            
            if user_data:
                # User exists in database, add to memory cache
                self.logger.debug(f"Loaded user {user_id} from database")
                self.users[user_id] = UserStats.from_dict(user_data)
            else:
                # User doesn't exist, create new
                self.logger.info(f"Creating new user profile for user {user_id}")
                self.users[user_id] = UserStats(user_id=user_id)
                # Save new user to database
                self.users[user_id]._save_to_db()
                
            return self.users[user_id]
        except Exception as e:
            # Fallback to in-memory only if database fails
            self.logger.error(f"Database error loading user {user_id}: {str(e)}")
            self.logger.warning(f"Creating in-memory only user for {user_id}")
            self.users[user_id] = UserStats(user_id=user_id)
            return self.users[user_id]
    
    def save_user(self, user: UserStats) -> bool:
        """Save user changes to database"""
        try:
            return user._save_to_db()
        except Exception as e:
            self.logger.error(f"Error saving user {user.user_id}: {str(e)}")
            return False
    
    def update_user_stats(self, user: UserStats) -> None:
        """Update user statistics and save to database"""
        # Ensure user is in memory cache
        self.users[user.user_id] = user
        # Save to database
        self.save_user(user)
    
    async def get_user_profile_picture(self, user_id: str) -> Optional[bytes]:
        """Get a user's profile picture"""
        user = self.get_user(user_id)
        return await user.get_profile_picture()
    
    async def set_user_profile_picture_url(self, user_id: str, url: str) -> None:
        """Set a user's profile picture URL"""
        user = self.get_user(user_id)
        await user.set_profile_picture_url(url)
        
    async def preload_profile_pictures(self, user_ids: List[str]) -> None:
        """Preload profile pictures for a list of users"""
        cache = get_profile_cache()
        tasks = []
        
        for user_id in user_ids:
            user = self.get_user(user_id)
            tasks.append(cache.get_profile_picture(user_id, user.profile_picture_url))
            
        # Run tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info(f"Preloaded {len(tasks)} profile pictures")
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user from the database and memory cache"""
        if user_id in self.users:
            del self.users[user_id]
        
        try:
            return self.repository.delete_user(user_id)
        except Exception as e:
            self.logger.error(f"Error deleting user {user_id}: {str(e)}")
            return False
    
    def get_top_voters(self, limit: int = None) -> List[UserStats]:
        """Get the top voters by lifetime votes"""
        if limit is None:
            limit = get_settings().user_top_voters_limit
            
        top_voters_data = self.repository.get_top_voters(limit)
        return [UserStats(**data) for data in top_voters_data]
            
    def __del__(self):
        """Ensure all unsaved users are saved on object destruction"""
        for user_id, user in self.users.items():
            try:
                user._save_to_db()
            except Exception:
                # Just log, don't raise in destructor
                self.logger.error(f"Error saving user {user_id} during cleanup")
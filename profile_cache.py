import os
import time
import logging
import hashlib
import aiohttp
import asyncio
from typing import Dict, Optional, Tuple, Any, List
from functools import lru_cache
from io import BytesIO
from datetime import datetime, timedelta
import aiofiles
from aiofiles.os import makedirs
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger("profile_cache")

# Cache configuration from environment variables
CACHE_DIR = os.getenv("PROFILE_CACHE_DIR", "cache/profiles")
CACHE_MAX_SIZE = int(os.getenv("PROFILE_CACHE_MAX_SIZE", "128"))  # Number of items in memory
CACHE_EXPIRY_HOURS = int(os.getenv("PROFILE_CACHE_EXPIRY_HOURS", "24"))
CACHE_DISK_MAX_SIZE_MB = int(os.getenv("PROFILE_CACHE_DISK_MAX_SIZE_MB", "100"))  # Max disk usage in MB

class ProfilePicture(BaseModel):
    """Model representing a cached profile picture"""
    user_id: str
    url: str
    data: Optional[bytes] = None
    file_path: Optional[str] = None
    last_accessed: datetime = datetime.now()
    last_updated: datetime = datetime.now()
    size_bytes: int = 0
    etag: Optional[str] = None
    content_type: str = "image/jpeg"  # Default content type
    
    class Config:
        arbitrary_types_allowed = True

class ProfileCache:
    """LRU Cache for profile pictures with disk persistence"""
    def __init__(self):
        self.logger = logger
        self.memory_cache: Dict[str, ProfilePicture] = {}
        self.disk_cache_dir = CACHE_DIR
        self.memory_cache_max_size = CACHE_MAX_SIZE
        self.cache_expiry = timedelta(hours=CACHE_EXPIRY_HOURS)
        self.disk_cache_max_size = CACHE_DISK_MAX_SIZE_MB * 1024 * 1024  # Convert to bytes
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize cache
        self._initialize_cache()
    
    def _initialize_cache(self) -> None:
        """Initialize the cache directory and structures"""
        try:
            # Create cache directory if it doesn't exist
            if not os.path.exists(self.disk_cache_dir):
                os.makedirs(self.disk_cache_dir, exist_ok=True)
                
            self.logger.info(f"Profile cache initialized at {self.disk_cache_dir}")
        except Exception as e:
            self.logger.error(f"Failed to initialize profile cache: {str(e)}")
    
    async def _ensure_session(self) -> None:
        """Ensure HTTP session is created"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self) -> None:
        """Close resources"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_file_path(self, user_id: str) -> str:
        """Generate filesystem path for a user's profile picture"""
        # Create a hash of the user ID to avoid filesystem issues
        hashed_id = hashlib.md5(user_id.encode()).hexdigest()
        return os.path.join(self.disk_cache_dir, f"{hashed_id}.jpg")
    
    async def _fetch_profile_picture(self, url: str) -> Tuple[bytes, dict]:
        """Fetch profile picture from remote URL"""
        await self._ensure_session()
        
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch profile picture: HTTP {response.status}")
                
                data = await response.read()
                headers = dict(response.headers)
                return data, headers
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout fetching profile picture from {url}")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching profile picture from {url}: {str(e)}")
            raise
    
    async def _save_to_disk(self, profile: ProfilePicture) -> None:
        """Save profile picture to disk"""
        if not profile.data:
            return
            
        file_path = self._get_file_path(profile.user_id)
        profile.file_path = file_path
        
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(profile.data)
                
            self.logger.debug(f"Saved profile picture for {profile.user_id} to disk at {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save profile picture to disk: {str(e)}")
    
    async def _load_from_disk(self, user_id: str) -> Optional[bytes]:
        """Load profile picture from disk"""
        file_path = self._get_file_path(user_id)
        
        if not os.path.exists(file_path):
            return None
            
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                data = await f.read()
                
            self.logger.debug(f"Loaded profile picture for {user_id} from disk")
            return data
        except Exception as e:
            self.logger.error(f"Failed to load profile picture from disk: {str(e)}")
            return None
    
    def _evict_if_needed(self) -> None:
        """Evict least recently used items from memory cache if needed"""
        if len(self.memory_cache) < self.memory_cache_max_size:
            return
            
        # Sort by last accessed time and remove oldest
        sorted_cache = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest 25% of items
        items_to_remove = max(1, len(sorted_cache) // 4)
        for i in range(items_to_remove):
            if i < len(sorted_cache):
                user_id, _ = sorted_cache[i]
                del self.memory_cache[user_id]
                
        self.logger.info(f"Evicted {items_to_remove} items from profile cache")
    
    async def _clean_disk_cache(self) -> None:
        """Clean up disk cache based on size and expiry"""
        try:
            # Get all cache files
            cache_files = []
            total_size = 0
            
            for filename in os.listdir(self.disk_cache_dir):
                file_path = os.path.join(self.disk_cache_dir, filename)
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    cache_files.append((
                        file_path,
                        file_stat.st_size,
                        datetime.fromtimestamp(file_stat.st_mtime)
                    ))
                    total_size += file_stat.st_size
            
            # If we're under disk limit, no need to clean
            if total_size <= self.disk_cache_max_size:
                return
                
            # Sort by last modified time (oldest first)
            cache_files.sort(key=lambda x: x[2])
            
            # Remove files until we're under the limit
            space_to_free = total_size - self.disk_cache_max_size
            freed_space = 0
            
            for file_path, size, mtime in cache_files:
                try:
                    os.remove(file_path)
                    freed_space += size
                    self.logger.debug(f"Removed cache file {file_path} to free up space")
                    
                    if freed_space >= space_to_free:
                        break
                except Exception as e:
                    self.logger.error(f"Failed to remove cache file {file_path}: {str(e)}")
            
            self.logger.info(f"Cleaned disk cache, freed {freed_space} bytes")
        except Exception as e:
            self.logger.error(f"Failed to clean disk cache: {str(e)}")
    
    @lru_cache(maxsize=CACHE_MAX_SIZE)
    async def get_profile_picture_url(self, user_id: str) -> Optional[str]:
        """Get the URL for a user's profile picture - separate LRU cache to avoid full data fetch"""
        # This would typically call an API to get the URL
        # For now, we'll use a placeholder service
        return f"https://i.pravatar.cc/150?u={user_id}"
    
    async def get_profile_picture(self, user_id: str, url: Optional[str] = None) -> Optional[bytes]:
        """
        Get a user's profile picture, either from cache or remote
        
        Args:
            user_id: User ID
            url: Optional URL override for the profile picture
            
        Returns:
            bytes: The profile picture data or None if not available
        """
        # Update last accessed time if in memory cache
        if user_id in self.memory_cache:
            self.memory_cache[user_id].last_accessed = datetime.now()
            return self.memory_cache[user_id].data
        
        # Try to load from disk if not in memory
        disk_data = await self._load_from_disk(user_id)
        if disk_data:
            # Add to memory cache
            profile_url = url or await self.get_profile_picture_url(user_id)
            profile = ProfilePicture(
                user_id=user_id,
                url=profile_url,
                data=disk_data,
                file_path=self._get_file_path(user_id),
                last_accessed=datetime.now(),
                last_updated=datetime.fromtimestamp(os.path.getmtime(self._get_file_path(user_id))),
                size_bytes=len(disk_data)
            )
            
            # Evict if needed before adding new item
            self._evict_if_needed()
            
            # Add to memory cache
            self.memory_cache[user_id] = profile
            return disk_data
        
        # If not in disk cache, fetch from remote
        if not url:
            url = await self.get_profile_picture_url(user_id)
            
        try:
            # Fetch from remote
            data, headers = await self._fetch_profile_picture(url)
            
            # Create profile object
            profile = ProfilePicture(
                user_id=user_id,
                url=url,
                data=data,
                size_bytes=len(data),
                last_accessed=datetime.now(),
                last_updated=datetime.now(),
                etag=headers.get('ETag'),
                content_type=headers.get('Content-Type', 'image/jpeg')
            )
            
            # Evict if needed before adding new item
            self._evict_if_needed()
            
            # Add to memory cache
            self.memory_cache[user_id] = profile
            
            # Save to disk asynchronously
            asyncio.create_task(self._save_to_disk(profile))
            
            # Periodically clean disk cache
            if random.random() < 0.1:  # 10% chance on each fetch
                asyncio.create_task(self._clean_disk_cache())
                
            return data
        except Exception as e:
            self.logger.error(f"Failed to get profile picture for user {user_id}: {str(e)}")
            return None
    
    async def invalidate(self, user_id: str) -> None:
        """Invalidate cache for a specific user"""
        if user_id in self.memory_cache:
            del self.memory_cache[user_id]
            
        # Clear LRU cache for URL
        self.get_profile_picture_url.cache_clear()
        
        # Remove from disk if exists
        file_path = self._get_file_path(user_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.logger.info(f"Invalidated profile picture cache for user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to delete profile picture from disk: {str(e)}")

# Singleton instance
_profile_cache: Optional[ProfileCache] = None

def get_profile_cache() -> ProfileCache:
    """Get singleton instance of ProfileCache"""
    global _profile_cache
    if _profile_cache is None:
        _profile_cache = ProfileCache()
    return _profile_cache

# Cleanup on application exit
async def close_profile_cache() -> None:
    """Close profile cache resources"""
    global _profile_cache
    if _profile_cache is not None:
        await _profile_cache.close()
        _profile_cache = None

# Missing import
import random 
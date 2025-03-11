import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.sql import func
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger("database")

# Get database configuration from environment
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "")
DB_NAME = os.getenv("DB_NAME", "price_of_war.db")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Create base class for declarative models
Base = declarative_base()

class UserStatsModel(Base):
    """SQLAlchemy model for user statistics"""
    __tablename__ = "user_stats"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    lifetime_votes = Column(Integer, default=0)
    show_votes = Column(Integer, default=0)
    erroneous_votes = Column(Integer, default=0)
    show_erroneous = Column(Integer, default=0)
    last_vote_time = Column(DateTime, nullable=True)
    naughty_status = Column(JSON, default={"lifetime": False, "show": False})
    nice_status = Column(JSON, default={"lifetime": False, "show": False})
    profile_picture_url = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserStats user_id={self.user_id}>"

class DatabaseManager:
    """Database connection and session manager"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.session = None
        
        # Connect to database
        self._connect()
        
    def _connect(self):
        """Connect to the database"""
        try:
            # Construct database URL based on environment variables
            if DB_TYPE == "sqlite":
                db_url = f"sqlite:///{DB_NAME}"
            elif DB_TYPE == "postgresql":
                db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            elif DB_TYPE == "mysql":
                db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            else:
                raise ValueError(f"Unsupported database type: {DB_TYPE}")
            
            # Create engine and session factory
            self.engine = create_engine(db_url, echo=False)
            self.session_factory = sessionmaker(bind=self.engine)
            self.session = scoped_session(self.session_factory)
            
            logger.info(f"Connected to {DB_TYPE} database")
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a session for database operations"""
        session = self.session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def close(self):
        """Close database connections"""
        if self.session:
            self.session.remove()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connections closed")

class UserStatsRepository:
    """Repository for user statistics database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logger
    
    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user statistics from database"""
        with self.db_manager.get_session() as session:
            user_stats = session.query(UserStatsModel).filter_by(user_id=user_id).first()
            
            if user_stats:
                return {
                    "user_id": user_stats.user_id,
                    "lifetime_votes": user_stats.lifetime_votes,
                    "show_votes": user_stats.show_votes,
                    "erroneous_votes": user_stats.erroneous_votes,
                    "show_erroneous": user_stats.show_erroneous,
                    "last_vote_time": user_stats.last_vote_time,
                    "naughty_status": user_stats.naughty_status,
                    "nice_status": user_stats.nice_status,
                    "profile_picture_url": user_stats.profile_picture_url
                }
            
            return None
    
    def save_user_stats(self, user_stats: Dict[str, Any]) -> bool:
        """Save user statistics to database"""
        with self.db_manager.get_session() as session:
            try:
                existing_user = session.query(UserStatsModel).filter_by(user_id=user_stats["user_id"]).first()
                
                if existing_user:
                    # Update existing user
                    existing_user.lifetime_votes = user_stats.get("lifetime_votes", existing_user.lifetime_votes)
                    existing_user.show_votes = user_stats.get("show_votes", existing_user.show_votes)
                    existing_user.erroneous_votes = user_stats.get("erroneous_votes", existing_user.erroneous_votes)
                    existing_user.show_erroneous = user_stats.get("show_erroneous", existing_user.show_erroneous)
                    existing_user.last_vote_time = user_stats.get("last_vote_time", existing_user.last_vote_time)
                    existing_user.naughty_status = user_stats.get("naughty_status", existing_user.naughty_status)
                    existing_user.nice_status = user_stats.get("nice_status", existing_user.nice_status)
                    existing_user.profile_picture_url = user_stats.get("profile_picture_url", existing_user.profile_picture_url)
                    existing_user.updated_at = datetime.now()
                else:
                    # Create new user
                    new_user = UserStatsModel(
                        user_id=user_stats["user_id"],
                        lifetime_votes=user_stats.get("lifetime_votes", 0),
                        show_votes=user_stats.get("show_votes", 0),
                        erroneous_votes=user_stats.get("erroneous_votes", 0),
                        show_erroneous=user_stats.get("show_erroneous", 0),
                        last_vote_time=user_stats.get("last_vote_time"),
                        naughty_status=user_stats.get("naughty_status", {"lifetime": False, "show": False}),
                        nice_status=user_stats.get("nice_status", {"lifetime": False, "show": False}),
                        profile_picture_url=user_stats.get("profile_picture_url"),
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(new_user)
                
                return True
            except Exception as e:
                self.logger.error(f"Error saving user stats: {str(e)}")
                return False
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all user statistics from database"""
        with self.db_manager.get_session() as session:
            users = session.query(UserStatsModel).all()
            
            return [{
                "user_id": user.user_id,
                "lifetime_votes": user.lifetime_votes,
                "show_votes": user.show_votes,
                "erroneous_votes": user.erroneous_votes,
                "show_erroneous": user.show_erroneous,
                "last_vote_time": user.last_vote_time,
                "naughty_status": user.naughty_status,
                "nice_status": user.nice_status,
                "profile_picture_url": user.profile_picture_url
            } for user in users]
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user statistics from database"""
        with self.db_manager.get_session() as session:
            try:
                user = session.query(UserStatsModel).filter_by(user_id=user_id).first()
                if user:
                    session.delete(user)
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Error deleting user: {str(e)}")
                return False
    
    def get_recent_active_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently active users based on last vote time"""
        with self.db_manager.get_session() as session:
            users = session.query(UserStatsModel).order_by(
                UserStatsModel.last_vote_time.desc()
            ).limit(limit).all()
            
            return [{
                "user_id": user.user_id,
                "lifetime_votes": user.lifetime_votes,
                "show_votes": user.show_votes,
                "erroneous_votes": user.erroneous_votes,
                "show_erroneous": user.show_erroneous,
                "last_vote_time": user.last_vote_time,
                "naughty_status": user.naughty_status,
                "nice_status": user.nice_status,
                "profile_picture_url": user.profile_picture_url
            } for user in users]
    
    def get_top_voters(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get users with the most lifetime votes"""
        with self.db_manager.get_session() as session:
            users = session.query(UserStatsModel).order_by(
                UserStatsModel.lifetime_votes.desc()
            ).limit(limit).all()
            
            return [{
                "user_id": user.user_id,
                "lifetime_votes": user.lifetime_votes,
                "show_votes": user.show_votes,
                "erroneous_votes": user.erroneous_votes,
                "show_erroneous": user.show_erroneous,
                "last_vote_time": user.last_vote_time,
                "naughty_status": user.naughty_status,
                "nice_status": user.nice_status,
                "profile_picture_url": user.profile_picture_url
            } for user in users]

# Singleton instance
_db_manager = None
_user_stats_repo = None

def get_db_manager() -> DatabaseManager:
    """Get singleton instance of DatabaseManager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize_database()
    return _db_manager

def get_user_stats_repository() -> UserStatsRepository:
    """Get singleton instance of UserStatsRepository"""
    global _user_stats_repo, _db_manager
    if _user_stats_repo is None:
        _user_stats_repo = UserStatsRepository(get_db_manager())
    return _user_stats_repo

def close_database():
    """Close database connections"""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None 
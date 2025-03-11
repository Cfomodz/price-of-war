import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database import Base, UserStatsRepository, get_db_manager
from user_rep import UserStats
from settings import get_settings

# Test fixtures
@pytest.fixture
async def engine():
    """Create a test database engine"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        yield engine
    finally:
        await engine.dispose()

@pytest.fixture
async def session_factory(engine):
    """Create a test session factory"""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session

@pytest.fixture
async def repository(session_factory):
    """Create a test repository"""
    async with session_factory() as session:
        repo = UserStatsRepository(session)
        yield repo

@pytest.fixture
def user_stats():
    """Create sample user stats"""
    return UserStats(
        user_id="test_user",
        lifetime_votes=100,
        show_votes=50,
        lifetime_errors=5,
        show_errors=2,
        last_vote_time=datetime.now(),
        profile_url="https://i.pravatar.cc/300"
    )

# Database Tests
@pytest.mark.asyncio
class TestDatabase:
    async def test_create_user_stats(self, repository, user_stats):
        """Test creating user stats in database"""
        # Create user stats
        await repository.create_user_stats(user_stats)
        
        # Retrieve and verify
        saved_stats = await repository.get_user_stats(user_stats.user_id)
        assert saved_stats is not None
        assert saved_stats.user_id == user_stats.user_id
        assert saved_stats.lifetime_votes == user_stats.lifetime_votes
        assert saved_stats.show_votes == user_stats.show_votes
        assert saved_stats.lifetime_errors == user_stats.lifetime_errors
        assert saved_stats.show_errors == user_stats.show_errors
        assert saved_stats.profile_url == user_stats.profile_url

    async def test_update_user_stats(self, repository, user_stats):
        """Test updating user stats"""
        # Create initial stats
        await repository.create_user_stats(user_stats)
        
        # Update stats
        user_stats.lifetime_votes += 1
        user_stats.show_votes += 1
        await repository.update_user_stats(user_stats)
        
        # Verify updates
        updated_stats = await repository.get_user_stats(user_stats.user_id)
        assert updated_stats.lifetime_votes == user_stats.lifetime_votes
        assert updated_stats.show_votes == user_stats.show_votes

    async def test_get_nonexistent_user(self, repository):
        """Test retrieving non-existent user"""
        stats = await repository.get_user_stats("nonexistent")
        assert stats is None

    async def test_get_top_voters(self, repository):
        """Test retrieving top voters"""
        # Create multiple users with different vote counts
        users = [
            UserStats(user_id=f"user_{i}", 
                     lifetime_votes=i*100,
                     show_votes=i*50,
                     last_vote_time=datetime.now()) 
            for i in range(5)
        ]
        
        for user in users:
            await repository.create_user_stats(user)
        
        # Get top 3 voters
        top_voters = await repository.get_top_voters(limit=3)
        assert len(top_voters) == 3
        assert top_voters[0].lifetime_votes > top_voters[1].lifetime_votes
        assert top_voters[1].lifetime_votes > top_voters[2].lifetime_votes

    async def test_bulk_operations(self, repository):
        """Test bulk database operations"""
        # Create multiple users
        users = [
            UserStats(user_id=f"bulk_user_{i}", 
                     lifetime_votes=i,
                     show_votes=i,
                     last_vote_time=datetime.now()) 
            for i in range(100)
        ]
        
        # Bulk create
        for user in users:
            await repository.create_user_stats(user)
        
        # Bulk update
        for user in users:
            user.lifetime_votes += 1
            await repository.update_user_stats(user)
        
        # Verify updates
        for i, user in enumerate(users):
            stats = await repository.get_user_stats(f"bulk_user_{i}")
            assert stats.lifetime_votes == i + 1

    @pytest.mark.benchmark
    async def test_database_performance(self, repository, benchmark):
        """Test database operation performance"""
        async def benchmark_operation():
            user = UserStats(
                user_id="perf_test_user",
                lifetime_votes=100,
                show_votes=50,
                last_vote_time=datetime.now()
            )
            await repository.create_user_stats(user)
            await repository.get_user_stats(user.user_id)
            user.lifetime_votes += 1
            await repository.update_user_stats(user)
        
        # Run benchmark
        await benchmark(benchmark_operation)

    async def test_concurrent_operations(self, repository):
        """Test concurrent database operations"""
        async def update_user(user_id: str, updates: int):
            for _ in range(updates):
                stats = await repository.get_user_stats(user_id)
                if stats is None:
                    stats = UserStats(
                        user_id=user_id,
                        lifetime_votes=0,
                        show_votes=0,
                        last_vote_time=datetime.now()
                    )
                    await repository.create_user_stats(stats)
                stats.lifetime_votes += 1
                await repository.update_user_stats(stats)
        
        # Run concurrent updates
        user_id = "concurrent_test_user"
        tasks = [
            update_user(user_id, 10)
            for _ in range(5)
        ]
        await asyncio.gather(*tasks)
        
        # Verify final state
        final_stats = await repository.get_user_stats(user_id)
        assert final_stats.lifetime_votes == 50  # 5 tasks * 10 updates

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov", "-n", "auto"]) 
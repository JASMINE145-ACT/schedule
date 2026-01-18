"""Database models and operations"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, Integer


Base = declarative_base()


class TravelPlan(Base):
    """Travel plan database model"""
    __tablename__ = "travel_plans"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    city: Mapped[str] = mapped_column(String(200))
    total_days: Mapped[int] = mapped_column(Integer)
    request_data: Mapped[str] = mapped_column(Text)  # JSON string
    plan_data: Mapped[str] = mapped_column(Text)  # JSON string
    itinerary_markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "plan_id": self.plan_id,
            "city": self.city,
            "total_days": self.total_days,
            "request_data": json.loads(self.request_data) if self.request_data else {},
            "plan_data": json.loads(self.plan_data) if self.plan_data else {},
            "itinerary_markdown": self.itinerary_markdown,
            "created_at": self.created_at.isoformat()
        }


class Database:
    """Database operations"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database
        
        Args:
            database_url: SQLite database URL (e.g., "sqlite+aiosqlite:///./travel_planner.db")
                         If None, uses default: "sqlite+aiosqlite:///./travel_planner.db"
        """
        if database_url is None:
            database_url = "sqlite+aiosqlite:///./travel_planner.db"
        self.engine = create_async_engine(
            database_url,
            echo=False,
            future=True
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init_db(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def save_plan(
        self,
        plan_id: str,
        city: str,
        total_days: int,
        request_data: Dict[str, Any],
        plan_data: Dict[str, Any],
        itinerary_markdown: str
    ) -> TravelPlan:
        """
        Save travel plan to database
        
        Args:
            plan_id: Unique plan ID
            city: City name
            total_days: Number of days
            request_data: Request data dictionary
            plan_data: Plan data dictionary
            itinerary_markdown: Markdown itinerary
            
        Returns:
            Saved TravelPlan object
        """
        async with self.async_session() as session:
            plan = TravelPlan(
                plan_id=plan_id,
                city=city,
                total_days=total_days,
                request_data=json.dumps(request_data, ensure_ascii=False),
                plan_data=json.dumps(plan_data, ensure_ascii=False),
                itinerary_markdown=itinerary_markdown
            )
            session.add(plan)
            await session.commit()
            await session.refresh(plan)
            return plan
    
    async def get_plan(self, plan_id: str) -> Optional[TravelPlan]:
        """
        Get plan by ID
        
        Args:
            plan_id: Plan ID
            
        Returns:
            TravelPlan object or None
        """
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TravelPlan).where(TravelPlan.plan_id == plan_id)
            )
            return result.scalar_one_or_none()
    
    async def list_plans(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[TravelPlan]:
        """
        List recent plans
        
        Args:
            limit: Maximum number of plans to return
            offset: Offset for pagination
            
        Returns:
            List of TravelPlan objects
        """
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TravelPlan)
                .order_by(TravelPlan.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
    
    async def delete_plan(self, plan_id: str) -> bool:
        """
        Delete plan by ID
        
        Args:
            plan_id: Plan ID
            
        Returns:
            True if deleted, False if not found
        """
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TravelPlan).where(TravelPlan.plan_id == plan_id)
            )
            plan = result.scalar_one_or_none()
            if plan:
                await session.delete(plan)
                await session.commit()
                return True
            return False


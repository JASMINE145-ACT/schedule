"""History router - handles history queries"""

from typing import List
from fastapi import APIRouter, HTTPException, Query
from app.models import PlanningHistoryEntry
from app.database import Database
import os

router = APIRouter(prefix="/api/history", tags=["history"])

# Get database instance (will be injected)
database: Database = None


def set_database(db: Database):
    """Set database instance"""
    global database
    database = db


@router.get("", response_model=List[PlanningHistoryEntry])
async def list_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List planning history"""
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        plans = await database.list_plans(limit=limit, offset=offset)
        result = []
        for plan in plans:
            summary = {
                "total_days": plan.total_days,
                "city": plan.city
            }
            result.append(PlanningHistoryEntry(
                plan_id=plan.plan_id,
                city=plan.city,
                total_days=plan.total_days,
                created_at=plan.created_at,
                summary=summary
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}")
async def get_plan(plan_id: str):
    """Get plan by ID"""
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        plan = await database.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        return plan.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str):
    """Delete plan by ID"""
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        deleted = await database.delete_plan(plan_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        return {"status": "deleted", "plan_id": plan_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


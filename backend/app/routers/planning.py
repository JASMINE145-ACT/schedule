"""Planning router - handles planning requests"""

from typing import List
from fastapi import APIRouter, HTTPException
from app.models import PlanningResponse, TravelRequest

router = APIRouter(prefix="/api/planning", tags=["planning"])


@router.get("/history")
async def get_planning_history():
    """Get planning history (placeholder)"""
    return {"message": "History endpoint - to be implemented"}


@router.get("/{plan_id}")
async def get_plan(plan_id: str):
    """Get plan by ID (placeholder)"""
    return {"message": f"Get plan {plan_id} - to be implemented"}


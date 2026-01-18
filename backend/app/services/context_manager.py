"""Context Manager - Manages planning context and state (inspired by SQL_LLM)

This module provides context management utilities for the business trip planner,
similar to SQL_LLM's context extraction and state management patterns.

Key Features:
- Context Extraction: Prepare structured context for LLM processing
- State Management: Track planning state and execution log
- Token Optimization: Minimize context size while maintaining accuracy
- Source of Truth: Single source of truth for planning data
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models_v2 import Conversation, TravelRequirement, TravelPlan, Message


class PlanningContext:
    """Planning context - tracks current planning state"""
    
    def __init__(self, conversation: Conversation):
        self.conversation = conversation
        self.planning_log: List[Dict[str, Any]] = []  # Source of truth
        self.geocode_cache: Dict[str, Dict[str, Any]] = {}  # Cache geocoding results
        self.directions_cache: Dict[str, Dict[str, Any]] = {}  # Cache directions
        self.places_cache: Dict[str, List[Dict[str, Any]]] = {}  # Cache place searches
    
    def add_planning_log_entry(self, entry: Dict[str, Any]):
        """Add entry to planning log (source of truth)"""
        entry["timestamp"] = datetime.now().isoformat()
        entry["log_id"] = f"log_{len(self.planning_log) + 1}"
        self.planning_log.append(entry)
    
    def get_latest_requirement(self) -> Optional[TravelRequirement]:
        """Get latest travel requirement from conversation"""
        return self.conversation.current_requirement
    
    def get_latest_plan(self) -> Optional[TravelPlan]:
        """Get latest travel plan from conversation"""
        return self.conversation.current_plan
    
    def get_planning_stage(self) -> str:
        """Get current planning stage"""
        return self.conversation.stage.value if self.conversation.stage else "understanding"


class ContextExtractor:
    """Context extractor - prepares structured context for LLM (inspired by SQL_LLM)"""
    
    @staticmethod
    def extract_user_requirements(context: PlanningContext) -> Dict[str, Any]:
        """
        Extract user requirements for planning context
        
        Args:
            context: Planning context
            
        Returns:
            Structured requirement data
        """
        requirement = context.get_latest_requirement()
        if not requirement:
            return {}
        
        return {
            "destination": requirement.destination,
            "duration_days": requirement.duration_days,
            "group_size": requirement.group_size,
            "transportation_mode": requirement.transportation_mode,
            "preferences": requirement.preferences,
            "constraints": requirement.constraints,
            "special_notes": requirement.special_notes
        }
    
    @staticmethod
    def prepare_planning_context(context: PlanningContext) -> Dict[str, Any]:
        """
        Prepare planning context for LLM (minimizes token usage)
        
        Args:
            context: Planning context
            
        Returns:
            Structured context data (optimized for token usage)
        """
        requirement = context.get_latest_requirement()
        plan = context.get_latest_plan()
        
        # Extract key information (not full objects)
        context_data = {
            "stage": context.get_planning_stage(),
            "requirement": ContextExtractor.extract_user_requirements(context),
            "planning_log_summary": ContextExtractor._summarize_planning_log(context.planning_log)
        }
        
        # Add plan summary if available
        if plan:
            context_data["plan_summary"] = {
                "id": plan.id,
                "title": plan.title,
                "days_count": len(plan.days),
                "version": plan.version
            }
        
        return context_data
    
    @staticmethod
    def _summarize_planning_log(log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize planning log (token optimization)
        
        Only includes key statistics, not full log entries
        """
        if not log:
            return {}
        
        successful_ops = [entry for entry in log if entry.get("status") == "success"]
        failed_ops = [entry for entry in log if entry.get("status") == "failed"]
        
        return {
            "total_operations": len(log),
            "successful_operations": len(successful_ops),
            "failed_operations": len(failed_ops),
            "recent_operations": [
                {
                    "type": entry.get("type"),
                    "status": entry.get("status"),
                    "timestamp": entry.get("timestamp")
                }
                for entry in log[-5:]  # Only last 5 entries
            ]
        }
    
    @staticmethod
    def prepare_traffic_risk_context(
        route_segments: List[Dict[str, Any]],
        planning_context: PlanningContext
    ) -> Dict[str, Any]:
        """
        Prepare traffic risk assessment context
        
        Args:
            route_segments: List of route segments
            planning_context: Planning context
            
        Returns:
            Traffic risk context
        """
        high_risk_segments = []
        medium_risk_segments = []
        
        for segment in route_segments:
            risk_level = segment.get("risk_level", "low")
            if risk_level == "high":
                high_risk_segments.append({
                    "from": segment.get("from_location"),
                    "to": segment.get("to_location"),
                    "time": segment.get("departure_time"),
                    "risk_cause": segment.get("risk_cause"),
                    "duration_in_traffic": segment.get("duration_in_traffic_text")
                })
            elif risk_level == "medium":
                medium_risk_segments.append({
                    "from": segment.get("from_location"),
                    "to": segment.get("to_location"),
                    "time": segment.get("departure_time"),
                    "risk_cause": segment.get("risk_cause")
                })
        
        return {
            "high_risk_segments": high_risk_segments,
            "medium_risk_segments": medium_risk_segments,
            "total_segments": len(route_segments),
            "risk_summary": {
                "high_risk_count": len(high_risk_segments),
                "medium_risk_count": len(medium_risk_segments),
                "low_risk_count": len(route_segments) - len(high_risk_segments) - len(medium_risk_segments)
            }
        }


class PlanningState:
    """Planning state - tracks execution state (similar to SQL_LLM's state management)"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.status: str = "pending"  # pending, running, completed, failed
        self.stage: str = "understanding"  # understanding, initial_planning, optimization, confirmation
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.planning_log: List[Dict[str, Any]] = []
        self.geocode_operations: List[Dict[str, Any]] = []
        self.directions_operations: List[Dict[str, Any]] = []
        self.place_search_operations: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.progress: Dict[str, Any] = {}
    
    def update_status(self, status: str, stage: Optional[str] = None):
        """Update state status"""
        self.status = status
        self.updated_at = datetime.now()
        if stage:
            self.stage = stage
    
    def add_geocode_operation(self, address: str, result: Dict[str, Any], status: str = "success"):
        """Add geocode operation to log"""
        self.geocode_operations.append({
            "address": address,
            "result": result,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_directions_operation(
        self,
        origin: str,
        destination: str,
        result: Dict[str, Any],
        status: str = "success"
    ):
        """Add directions operation to log"""
        self.directions_operations.append({
            "origin": origin,
            "destination": destination,
            "result": result,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_place_search_operation(
        self,
        query: str,
        results: List[Dict[str, Any]],
        status: str = "success"
    ):
        """Add place search operation to log"""
        self.place_search_operations.append({
            "query": query,
            "results_count": len(results),
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None):
        """Add error to error log"""
        self.errors.append({
            "type": error_type,
            "message": error_message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            "conversation_id": self.conversation_id,
            "status": self.status,
            "stage": self.stage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "statistics": {
                "geocode_operations": len(self.geocode_operations),
                "directions_operations": len(self.directions_operations),
                "place_search_operations": len(self.place_search_operations),
                "errors": len(self.errors)
            }
        }


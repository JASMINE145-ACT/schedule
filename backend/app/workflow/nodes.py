"""Workflow Nodes - Business trip planning workflow nodes (inspired by SQL_LLM)

This module defines individual workflow nodes for the business trip planner,
similar to SQL_LLM's node-based workflow architecture.

Each node:
- Takes planning state as input
- Performs a specific planning operation
- Updates planning state
- Returns updated state or error

Key Features:
- State Management: Each node updates planning state
- Error Handling: Nodes catch and log errors
- Progress Tracking: Track progress through workflow
- Context Preparation: Prepare context for next nodes
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from app.services.context_manager import PlanningContext, ContextExtractor, PlanningState
from app.services.maps_service import MapsService
from app.services.route_optimizer import RouteOptimizer
from app.services.report_generator import ReportGenerator


async def understand_requirements_node(
    state: PlanningState,
    context: PlanningContext,
    user_input: str
) -> Dict[str, Any]:
    """
    Understand business trip requirements node
    
    Args:
        state: Planning state
        context: Planning context
        user_input: User natural language input
        
    Returns:
        Updated state with requirements
    """
    try:
        state.update_status("running", "understanding")
        state.progress["stage"] = "understanding"
        state.progress["completed"] = False
        
        # This would call LLM service to extract requirements
        # For now, return basic structure
        planning_log_entry = {
            "type": "understand_requirements",
            "input": user_input,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
        
        context.add_planning_log_entry(planning_log_entry)
        state.progress["completed"] = True
        
        return {"status": "success", "state": state.to_dict()}
    except Exception as e:
        state.add_error("understand_requirements", str(e))
        return {"status": "error", "error": str(e), "state": state.to_dict()}


async def geocode_locations_node(
    state: PlanningState,
    context: PlanningContext,
    maps_service: MapsService,
    locations: List[str]
) -> Dict[str, Any]:
    """
    Geocode locations node
    
    Args:
        state: Planning state
        context: Planning context
        maps_service: Maps service instance
        locations: List of location addresses
        
    Returns:
        Updated state with geocoded locations
    """
    try:
        state.update_status("running", "geocoding")
        state.progress["stage"] = "geocoding"
        state.progress["total_locations"] = len(locations)
        state.progress["geocoded_count"] = 0
        
        geocoded_locations = {}
        
        for location in locations:
            try:
                # Check cache first
                if location in context.geocode_cache:
                    result = context.geocode_cache[location]
                else:
                    result = maps_service.geocode(location)
                    context.geocode_cache[location] = result
                
                geocoded_locations[location] = result
                state.add_geocode_operation(location, result, "success")
                state.progress["geocoded_count"] += 1
                
            except Exception as e:
                state.add_geocode_operation(location, {}, "failed")
                state.add_error("geocode", f"Failed to geocode {location}: {str(e)}")
        
        planning_log_entry = {
            "type": "geocode_locations",
            "locations_count": len(locations),
            "success_count": state.progress["geocoded_count"],
            "status": "success",
            "results": geocoded_locations
        }
        
        context.add_planning_log_entry(planning_log_entry)
        
        return {
            "status": "success",
            "geocoded_locations": geocoded_locations,
            "state": state.to_dict()
        }
        
    except Exception as e:
        state.add_error("geocode_locations", str(e))
        return {"status": "error", "error": str(e), "state": state.to_dict()}


async def calculate_distances_node(
    state: PlanningState,
    context: PlanningContext,
    maps_service: MapsService,
    origins: List[str],
    destinations: List[str],
    departure_time: Optional[datetime] = None,
    traffic_model: str = "pessimistic"
) -> Dict[str, Any]:
    """
    Calculate distance matrix node (with traffic awareness)
    
    Args:
        state: Planning state
        context: Planning context
        maps_service: Maps service instance
        origins: List of origin addresses
        destinations: List of destination addresses
        departure_time: Optional departure time for traffic-aware routing
        traffic_model: Traffic model (best_guess, pessimistic, optimistic)
        
    Returns:
        Updated state with distance matrix
    """
    try:
        state.update_status("running", "calculating_distances")
        state.progress["stage"] = "calculating_distances"
        
        # Calculate distance matrix with traffic
        distance_matrix = maps_service.get_distance_matrix(
            origins=origins,
            destinations=destinations,
            mode="driving",
            departure_time=departure_time,
            traffic_model=traffic_model
        )
        
        # Log distance matrix operation
        for entry in distance_matrix:
            if "distance_meters" in entry:
                state.add_directions_operation(
                    entry["origin"],
                    entry["destination"],
                    entry,
                    "success"
                )
        
        planning_log_entry = {
            "type": "calculate_distances",
            "origins_count": len(origins),
            "destinations_count": len(destinations),
            "entries_count": len(distance_matrix),
            "departure_time": departure_time.isoformat() if departure_time else None,
            "traffic_model": traffic_model,
            "status": "success"
        }
        
        context.add_planning_log_entry(planning_log_entry)
        
        return {
            "status": "success",
            "distance_matrix": distance_matrix,
            "state": state.to_dict()
        }
        
    except Exception as e:
        state.add_error("calculate_distances", str(e))
        return {"status": "error", "error": str(e), "state": state.to_dict()}


async def search_business_places_node(
    state: PlanningState,
    context: PlanningContext,
    maps_service: MapsService,
    location: str,
    place_type: str = "restaurant",
    radius: int = 1000,
    keyword: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search business places node (restaurants/hotels)
    
    Args:
        state: Planning state
        context: Planning context
        maps_service: Maps service instance
        location: Search location
        place_type: Place type (restaurant, lodging)
        radius: Search radius in meters
        keyword: Search keyword (e.g., 'business lunch')
        
    Returns:
        Updated state with place search results
    """
    try:
        state.update_status("running", "searching_places")
        state.progress["stage"] = "searching_places"
        
        # Search places
        if place_type == "restaurant":
            results = maps_service.search_business_restaurants(
                location=location,
                radius=radius,
                keyword=keyword or "business lunch"
            )
        elif place_type == "lodging":
            results = maps_service.search_business_hotels(
                location=location,
                radius=radius
            )
        else:
            results = maps_service.search_places(
                query=f"{place_type} {location}",
                location=location,
                radius=radius,
                place_type=place_type,
                keyword=keyword
            )
        
        # Cache results
        cache_key = f"{place_type}_{location}_{radius}"
        context.places_cache[cache_key] = results
        
        # Log place search operation
        state.add_place_search_operation(
            f"{place_type} near {location}",
            results,
            "success"
        )
        
        planning_log_entry = {
            "type": "search_business_places",
            "location": location,
            "place_type": place_type,
            "results_count": len(results),
            "status": "success"
        }
        
        context.add_planning_log_entry(planning_log_entry)
        
        return {
            "status": "success",
            "places": results,
            "state": state.to_dict()
        }
        
    except Exception as e:
        state.add_error("search_business_places", str(e))
        return {"status": "error", "error": str(e), "state": state.to_dict()}


async def optimize_route_node(
    state: PlanningState,
    context: PlanningContext,
    route_optimizer: RouteOptimizer,
    locations: List[str],
    start_location: str,
    end_location: Optional[str],
    distance_matrix: List[Dict[str, Any]],
    constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Optimize route order node
    
    Args:
        state: Planning state
        context: Planning context
        route_optimizer: Route optimizer instance
        locations: List of locations to visit
        start_location: Starting location
        end_location: Ending location (optional)
        distance_matrix: Distance matrix data
        constraints: Route constraints
        
    Returns:
        Updated state with optimized route
    """
    try:
        state.update_status("running", "optimizing_route")
        state.progress["stage"] = "optimizing_route"
        
        # Optimize route order
        optimized_order = route_optimizer.optimize_route_order(
            locations=locations,
            start_location=start_location,
            end_location=end_location,
            distance_matrix=distance_matrix
        )
        
        # Calculate schedule
        route_segments = []
        for i in range(len(optimized_order) - 1):
            from_loc = optimized_order[i]
            to_loc = optimized_order[i + 1]
            
            # Find distance matrix entry
            segment_data = next(
                (entry for entry in distance_matrix 
                 if entry.get("origin") == from_loc and entry.get("destination") == to_loc),
                {}
            )
            
            if segment_data:
                route_segments.append({
                    "from_location": from_loc,
                    "to_location": to_loc,
                    "distance_meters": segment_data.get("distance_meters", 0),
                    "distance_text": segment_data.get("distance_text", ""),
                    "duration_seconds": segment_data.get("duration_seconds", 0),
                    "duration_text": segment_data.get("duration_text", ""),
                    "duration_in_traffic_seconds": segment_data.get("duration_in_traffic_seconds"),
                    "duration_in_traffic_text": segment_data.get("duration_in_traffic_text", ""),
                    "traffic_delay_minutes": segment_data.get("traffic_delay_minutes", 0)
                })
        
        # Calculate schedule with traffic awareness
        scheduled_segments = route_optimizer.calculate_schedule(
            route_segments=route_segments,
            start_time=constraints.get("start_time", "08:00"),
            constraints=constraints
        )
        
        planning_log_entry = {
            "type": "optimize_route",
            "locations_count": len(locations),
            "optimized_order": optimized_order,
            "segments_count": len(scheduled_segments),
            "status": "success"
        }
        
        context.add_planning_log_entry(planning_log_entry)
        
        return {
            "status": "success",
            "optimized_order": optimized_order,
            "route_segments": scheduled_segments,
            "state": state.to_dict()
        }
        
    except Exception as e:
        state.add_error("optimize_route", str(e))
        return {"status": "error", "error": str(e), "state": state.to_dict()}


async def assess_traffic_risks_node(
    state: PlanningState,
    context: PlanningContext,
    route_segments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Assess traffic risks node
    
    Args:
        state: Planning state
        context: Planning context
        route_segments: List of route segments with traffic data
        
    Returns:
        Updated state with traffic risk assessment
    """
    try:
        state.update_status("running", "assessing_risks")
        state.progress["stage"] = "assessing_risks"
        
        # Group risks by level
        high_risks = []
        medium_risks = []
        low_risks = []
        
        for i, segment in enumerate(route_segments):
            risk_level = segment.get("risk_level", "low")
            risk_data = {
                "segment_index": i,
                "from": segment.get("from_location"),
                "to": segment.get("to_location"),
                "time": segment.get("departure_time"),
                "level": risk_level,
                "cause": segment.get("risk_cause"),
                "mitigation": segment.get("risk_mitigation"),
                "duration_in_traffic": segment.get("duration_in_traffic_text")
            }
            
            if risk_level == "high":
                high_risks.append(risk_data)
            elif risk_level == "medium":
                medium_risks.append(risk_data)
            else:
                low_risks.append(risk_data)
        
        traffic_risk_context = ContextExtractor.prepare_traffic_risk_context(
            route_segments=route_segments,
            planning_context=context
        )
        
        planning_log_entry = {
            "type": "assess_traffic_risks",
            "high_risk_count": len(high_risks),
            "medium_risk_count": len(medium_risks),
            "low_risk_count": len(low_risks),
            "status": "success"
        }
        
        context.add_planning_log_entry(planning_log_entry)
        
        return {
            "status": "success",
            "traffic_risks": {
                "high": high_risks,
                "medium": medium_risks,
                "low": low_risks
            },
            "risk_summary": traffic_risk_context["risk_summary"],
            "state": state.to_dict()
        }
        
    except Exception as e:
        state.add_error("assess_traffic_risks", str(e))
        return {"status": "error", "error": str(e), "state": state.to_dict()}


async def generate_alternatives_node(
    state: PlanningState,
    context: PlanningContext,
    maps_service: MapsService,
    origin: str,
    destination: str,
    departure_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Generate alternative routes node
    
    Args:
        state: Planning state
        context: Planning context
        maps_service: Maps service instance
        origin: Origin address
        destination: Destination address
        departure_time: Optional departure time
        
    Returns:
        Updated state with alternative routes
    """
    try:
        state.update_status("running", "generating_alternatives")
        state.progress["stage"] = "generating_alternatives"
        
        # Get directions with alternatives
        directions_result = maps_service.get_directions(
            origin=origin,
            destination=destination,
            mode="driving",
            departure_time=departure_time,
            traffic_model="pessimistic",
            alternatives=True
        )
        
        alternatives = []
        if "routes" in directions_result:
            for i, route in enumerate(directions_result["routes"]):
                alternatives.append({
                    "route_number": i + 1,
                    "distance": route.get("distance_text"),
                    "duration": route.get("duration_text"),
                    "duration_in_traffic": route.get("duration_in_traffic_text"),
                    "summary": route.get("summary", ""),
                    "is_primary": i == 0
                })
        
        planning_log_entry = {
            "type": "generate_alternatives",
            "origin": origin,
            "destination": destination,
            "alternatives_count": len(alternatives),
            "status": "success"
        }
        
        context.add_planning_log_entry(planning_log_entry)
        
        return {
            "status": "success",
            "alternatives": alternatives,
            "primary_route": alternatives[0] if alternatives else None,
            "state": state.to_dict()
        }
        
    except Exception as e:
        state.add_error("generate_alternatives", str(e))
        return {"status": "error", "error": str(e), "state": state.to_dict()}


async def generate_report_node(
    state: PlanningState,
    context: PlanningContext,
    report_generator: ReportGenerator,
    plan_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate final report node
    
    Args:
        state: Planning state
        context: Planning context
        report_generator: Report generator instance
        plan_data: Complete plan data
        
    Returns:
        Updated state with generated report
    """
    try:
        state.update_status("running", "generating_report")
        state.progress["stage"] = "generating_report"
        
        # Generate markdown report
        report = report_generator.generate_markdown(
            plan_data=plan_data,
            include_details=True
        )
        
        planning_log_entry = {
            "type": "generate_report",
            "report_length": len(report),
            "status": "success"
        }
        
        context.add_planning_log_entry(planning_log_entry)
        state.update_status("completed", "completed")
        
        return {
            "status": "success",
            "report": report,
            "state": state.to_dict()
        }
        
    except Exception as e:
        state.add_error("generate_report", str(e))
        return {"status": "error", "error": str(e), "state": state.to_dict()}


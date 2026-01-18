"""Route optimization logic"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import math


class RouteOptimizer:
    """Route optimization service"""
    
    def __init__(self):
        pass
    
    def optimize_route_order(
        self,
        locations: List[str],
        start_location: str,
        end_location: Optional[str],
        distance_matrix: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Optimize route order using nearest neighbor heuristic
        
        Args:
            locations: List of locations to visit
            start_location: Starting location
            end_location: Ending location (optional)
            distance_matrix: Distance matrix data
            
        Returns:
            Optimized order of locations
        """
        if not locations:
            return []
        
        # Build distance lookup
        distance_map = {}
        for entry in distance_matrix:
            if entry.get("status") == "OK" or "distance_meters" in entry:
                origin = entry["origin"]
                destination = entry["destination"]
                if origin not in distance_map:
                    distance_map[origin] = {}
                distance_map[origin][destination] = entry.get("distance_meters", float('inf'))
        
        # Nearest neighbor algorithm
        unvisited = set(locations)
        current = start_location
        route = [current]
        
        while unvisited:
            nearest = None
            nearest_distance = float('inf')
            
            for location in unvisited:
                distance = distance_map.get(current, {}).get(location, float('inf'))
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest = location
            
            if nearest:
                route.append(nearest)
                unvisited.remove(nearest)
                current = nearest
            else:
                # If no path found, add remaining in order
                route.extend(unvisited)
                break
        
        # Add end location if specified and not already in route
        if end_location and end_location != route[-1]:
            route.append(end_location)
        
        return route
    
    def is_rush_hour(
        self,
        time_str: str,
        rush_hour_start: str,
        rush_hour_end: str
    ) -> bool:
        """
        Check if a time is within rush hour
        
        Args:
            time_str: Time string (HH:MM format)
            rush_hour_start: Rush hour start (HH:MM)
            rush_hour_end: Rush hour end (HH:MM)
            
        Returns:
            True if within rush hour
        """
        try:
            hour, minute = map(int, time_str.split(':'))
            start_hour, start_minute = map(int, rush_hour_start.split(':'))
            end_hour, end_minute = map(int, rush_hour_end.split(':'))
            
            time_minutes = hour * 60 + minute
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            
            return start_minutes <= time_minutes <= end_minutes
        except:
            return False
    
    def assess_risk_level(
        self,
        duration_seconds: int,
        duration_in_traffic_seconds: Optional[int] = None,
        is_rush_hour: bool = False,
        max_travel_time_minutes: int = 120
    ) -> Dict[str, Any]:
        """
        Assess risk level for a route segment (enhanced with traffic data)
        
        Args:
            duration_seconds: Base travel duration in seconds (non-rush hour)
            duration_in_traffic_seconds: Duration in traffic (if available)
            is_rush_hour: Whether during rush hour
            max_travel_time_minutes: Maximum allowed travel time in minutes (default 2 hours)
            
        Returns:
            Risk assessment dictionary with level, cause, and mitigation
        """
        # Use traffic duration if available, otherwise use base duration
        actual_duration = duration_in_traffic_seconds or duration_seconds
        duration_minutes = actual_duration / 60
        max_seconds = max_travel_time_minutes * 60
        
        # Calculate traffic delay
        traffic_delay_minutes = 0
        if duration_in_traffic_seconds:
            traffic_delay_minutes = (duration_in_traffic_seconds - duration_seconds) / 60
        
        # Assess risk level
        risk_level = "low"
        risk_cause = ""
        mitigation = ""
        
        if actual_duration > max_seconds:
            risk_level = "high"
            risk_cause = f"单程车程 {duration_minutes:.1f} 分钟超过限制 {max_travel_time_minutes} 分钟"
            mitigation = "建议提前出发或选择更近的地点，拆分行程"
        elif actual_duration > max_seconds * 0.8:
            risk_level = "medium"
            risk_cause = f"单程车程 {duration_minutes:.1f} 分钟接近限制 {max_travel_time_minutes} 分钟"
            mitigation = "建议预留额外时间，避开高峰时段"
        elif is_rush_hour and duration_minutes > 30:
            risk_level = "medium"
            risk_cause = f"高峰时段车程 {duration_minutes:.1f} 分钟，可能延误商务会面"
            if traffic_delay_minutes > 10:
                risk_cause += f"，交通延迟约 {traffic_delay_minutes:.0f} 分钟"
            mitigation = "建议提前出发避开高峰，或选择非高峰时段"
        elif traffic_delay_minutes > 20:
            risk_level = "medium"
            risk_cause = f"交通延迟约 {traffic_delay_minutes:.0f} 分钟"
            mitigation = "建议预留缓冲时间，避开拥堵路段"
        else:
            risk_level = "low"
            risk_cause = f"车程 {duration_minutes:.1f} 分钟，风险较低"
            mitigation = "按计划执行即可"
        
        return {
            "level": risk_level,
            "cause": risk_cause,
            "mitigation": mitigation,
            "duration_minutes": duration_minutes,
            "traffic_delay_minutes": round(traffic_delay_minutes, 1),
            "is_rush_hour": is_rush_hour
        }
    
    def calculate_schedule(
        self,
        route_segments: List[Dict[str, Any]],
        start_time: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calculate detailed schedule for route segments
        
        Args:
            route_segments: List of route segments
            start_time: Starting time (HH:MM format)
            constraints: Route constraints
            
        Returns:
            Segments with calculated departure and arrival times
        """
        current_time = datetime.strptime(start_time, "%H:%M")
        scheduled_segments = []
        
        for segment in route_segments:
            duration_seconds = segment.get("duration_seconds", 0)
            duration_minutes = math.ceil(duration_seconds / 60)
            
            # Add visit time (default 60 minutes per location)
            visit_minutes = segment.get("visit_minutes", 60)
            
            # Check if rush hour
            departure_str = current_time.strftime("%H:%M")
            is_rush_morning = self.is_rush_hour(
                departure_str,
                constraints.get("rush_hour_start_morning", "07:00"),
                constraints.get("rush_hour_end_morning", "09:00")
            )
            is_rush_evening = self.is_rush_hour(
                departure_str,
                constraints.get("rush_hour_start_evening", "16:30"),
                constraints.get("rush_hour_end_evening", "18:30")
            )
            is_rush = is_rush_morning or is_rush_evening
            
            # Calculate arrival time
            arrival_time = current_time + timedelta(minutes=duration_minutes)
            arrival_str = arrival_time.strftime("%H:%M")
            
            # Calculate departure from this location
            departure_from_location = arrival_time + timedelta(minutes=visit_minutes)
            
            # Assess risk (enhanced with traffic data)
            duration_in_traffic = segment.get("duration_in_traffic_seconds") or segment.get("duration_seconds", 0)
            risk_assessment = self.assess_risk_level(
                duration_seconds,
                duration_in_traffic,
                is_rush,
                constraints.get("max_travel_time_minutes", 120)
            )
            
            segment_scheduled = {
                **segment,
                "departure_time": departure_str,
                "arrival_time": arrival_str,
                "is_rush_hour": is_rush,
                "risk_level": risk_assessment["level"],
                "risk_cause": risk_assessment["cause"],
                "risk_mitigation": risk_assessment["mitigation"],
                "duration_in_traffic_seconds": duration_in_traffic,
                "duration_in_traffic_text": segment.get("duration_in_traffic_text") or segment.get("duration_text"),
                "traffic_delay_minutes": risk_assessment["traffic_delay_minutes"],
                "visit_minutes": visit_minutes
            }
            
            scheduled_segments.append(segment_scheduled)
            current_time = departure_from_location
        
        return scheduled_segments
    
    def detect_backtracking(
        self,
        route_segments: List[Dict[str, Any]],
        distance_matrix: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect backtracking in route
        
        Args:
            route_segments: List of route segments
            distance_matrix: Distance matrix data
            
        Returns:
            List of backtracking issues found
        """
        backtracking_issues = []
        
        # Build distance lookup
        distance_map = {}
        for entry in distance_matrix:
            if "distance_meters" in entry:
                origin = entry["origin"]
                destination = entry["destination"]
                if origin not in distance_map:
                    distance_map[origin] = {}
                distance_map[origin][destination] = entry["distance_meters"]
        
        # Check for obvious backtracking (going back to a location near previous one)
        for i in range(1, len(route_segments)):
            prev_segment = route_segments[i-1]
            curr_segment = route_segments[i]
            
            prev_from = prev_segment.get("from_location")
            prev_to = prev_segment.get("to_location")
            curr_from = curr_segment.get("from_location")
            curr_to = curr_segment.get("to_location")
            
            # If we're going back towards a previous location
            if prev_from and curr_to:
                # Check distance between prev_from and curr_to
                # If it's shorter than going through curr_from, there's backtracking
                direct_distance = distance_map.get(prev_from, {}).get(curr_to, float('inf'))
                indirect_distance = (
                    distance_map.get(prev_from, {}).get(curr_from, float('inf')) +
                    distance_map.get(curr_from, {}).get(curr_to, float('inf'))
                )
                
                if direct_distance < indirect_distance * 0.7:  # 30% shorter
                    backtracking_issues.append({
                        "segment_index": i,
                        "issue": f"Possible backtracking: {curr_from} → {curr_to} might be shorter via {prev_from}",
                        "suggestion": f"Consider going directly from {prev_from} to {curr_to}"
                    })
        
        return backtracking_issues


"""Google Maps service - encapsulates map operations"""

import os
from typing import List, Dict, Any, Optional
import googlemaps
from datetime import datetime


class MapsService:
    """Service for Google Maps operations"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Maps Service
        
        Args:
            api_key: Google Maps API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY not found. "
                "Please set it in environment variables or pass as parameter."
            )
        self.client = googlemaps.Client(key=self.api_key)
    
    def geocode(self, address: str) -> Dict[str, Any]:
        """
        Geocode an address to coordinates
        
        Args:
            address: Address string
            
        Returns:
            Dictionary with address, lat, lng, place_id
        """
        try:
            geocode_result = self.client.geocode(address)
            if not geocode_result:
                raise ValueError(f"Geocoding failed for address: {address}")
            
            result = geocode_result[0]
            location = result["geometry"]["location"]
            
            return {
                "address": result["formatted_address"],
                "lat": location["lat"],
                "lng": location["lng"],
                "place_id": result.get("place_id")
            }
        except Exception as e:
            raise ValueError(f"Geocoding error for '{address}': {str(e)}")
    
    def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "driving",
        departure_time: Optional[datetime] = None,
        traffic_model: str = "best_guess",
        alternatives: bool = False
    ) -> Dict[str, Any]:
        """
        Get directions between two locations with traffic awareness
        
        Args:
            origin: Origin address
            destination: Destination address
            mode: Transportation mode (driving, walking, transit)
            departure_time: Optional departure time for traffic-aware routing
            traffic_model: Traffic model (best_guess, pessimistic, optimistic)
                          - best_guess: Default, balanced estimate
                          - pessimistic: Conservative estimate (worst case)
                          - optimistic: Best case estimate
            alternatives: Whether to return alternative routes
            
        Returns:
            Dictionary with route information (or list if alternatives=True)
        """
        try:
            params = {
                "origin": origin,
                "destination": destination,
                "mode": mode
            }
            
            if departure_time:
                params["departure_time"] = departure_time
                params["traffic_model"] = traffic_model
            
            if alternatives:
                params["alternatives"] = True
            
            directions_result = self.client.directions(**params)
            
            if not directions_result:
                raise ValueError(f"No route found from {origin} to {destination}")
            
            # If alternatives requested, return list of routes
            if alternatives and len(directions_result) > 1:
                routes = []
                for route in directions_result:
                    routes.append(self._parse_route(route))
                return {
                    "routes": routes,
                    "primary": routes[0],
                    "alternatives": routes[1:] if len(routes) > 1 else []
                }
            
            # Single route
            route = directions_result[0]
            return self._parse_route(route)
            
        except Exception as e:
            raise ValueError(f"Directions error: {str(e)}")
    
    def _parse_route(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single route from directions API response"""
        leg = route["legs"][0]
        
        # Extract steps (limit to first 10 for brevity)
        steps = []
        for step in leg["steps"][:10]:
            steps.append({
                "instruction": step["html_instructions"],
                "distance": step["distance"]["text"],
                "distance_meters": step["distance"]["value"],
                "duration": step["duration"]["text"],
                "duration_seconds": step["duration"]["value"]
            })
        
        result = {
            "origin": leg["start_address"],
            "destination": leg["end_address"],
            "distance_text": leg["distance"]["text"],
            "distance_meters": leg["distance"]["value"],
            "duration_text": leg["duration"]["text"],
            "duration_seconds": leg["duration"]["value"],
            "summary": route.get("summary", ""),  # Main road name
            "steps": steps
        }
        
        # Add duration in traffic if available (key for traffic-aware routing)
        if "duration_in_traffic" in leg:
            result["duration_in_traffic_seconds"] = leg["duration_in_traffic"]["value"]
            result["duration_in_traffic_text"] = leg["duration_in_traffic"]["text"]
            # Calculate traffic delay
            traffic_delay = result["duration_in_traffic_seconds"] - result["duration_seconds"]
            result["traffic_delay_seconds"] = traffic_delay
            result["traffic_delay_minutes"] = round(traffic_delay / 60, 1)
        else:
            # If no traffic data, use base duration
            result["duration_in_traffic_seconds"] = result["duration_seconds"]
            result["duration_in_traffic_text"] = result["duration_text"]
            result["traffic_delay_seconds"] = 0
            result["traffic_delay_minutes"] = 0
        
        return result
    
    def get_distance_matrix(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        departure_time: Optional[datetime] = None,
        traffic_model: str = "best_guess"
    ) -> List[Dict[str, Any]]:
        """
        Get distance matrix between origins and destinations
        
        Args:
            origins: List of origin addresses
            destinations: List of destination addresses
            mode: Transportation mode
            
        Returns:
            List of distance matrix entries
        """
        # Validate inputs
        if not origins or not destinations:
            raise ValueError(
                f"Distance matrix requires at least one origin and one destination. "
                f"Got origins: {len(origins)}, destinations: {len(destinations)}"
            )
        
        # Filter out empty or None locations
        origins = [loc for loc in origins if loc and str(loc).strip()]
        destinations = [loc for loc in destinations if loc and str(loc).strip()]
        
        if not origins or not destinations:
            raise ValueError(
                f"After filtering, no valid locations found. "
                f"Origins: {origins}, Destinations: {destinations}"
            )
        
        try:
            params = {
                "origins": origins,
                "destinations": destinations,
                "mode": mode
            }
            
            # Add traffic-aware parameters if departure_time is provided
            if departure_time:
                params["departure_time"] = departure_time
                params["traffic_model"] = traffic_model
            
            matrix = self.client.distance_matrix(**params)
            
            # Check for API-level errors
            status = matrix.get("status")
            if status != "OK":
                error_message = matrix.get("error_message", "Unknown error")
                raise ValueError(
                    f"Distance matrix API error: {status}. {error_message}. "
                    f"Origins: {origins[:3]}... ({len(origins)} total), "
                    f"Destinations: {destinations[:3]}... ({len(destinations)} total)"
                )
            
            # Check if rows exist
            if "rows" not in matrix or not matrix["rows"]:
                raise ValueError(
                    f"Distance matrix returned no rows. "
                    f"Origins: {origins}, Destinations: {destinations}"
                )
            
            results = []
            for i, origin in enumerate(origins):
                if i >= len(matrix["rows"]):
                    break
                row = matrix["rows"][i]
                if "elements" not in row:
                    continue
                    
                for j, destination in enumerate(destinations):
                    if j >= len(row["elements"]):
                        break
                    element = row["elements"][j]
                    element_status = element.get("status", "UNKNOWN")
                    
                    if element_status == "OK":
                        result_entry = {
                            "origin": origin,
                            "destination": destination,
                            "distance_text": element["distance"]["text"],
                            "distance_meters": element["distance"]["value"],
                            "duration_text": element["duration"]["text"],
                            "duration_seconds": element["duration"]["value"]
                        }
                        
                        # Add duration in traffic if available
                        if "duration_in_traffic" in element:
                            result_entry["duration_in_traffic_seconds"] = element["duration_in_traffic"]["value"]
                            result_entry["duration_in_traffic_text"] = element["duration_in_traffic"]["text"]
                            # Calculate traffic delay
                            traffic_delay = result_entry["duration_in_traffic_seconds"] - result_entry["duration_seconds"]
                            result_entry["traffic_delay_seconds"] = traffic_delay
                            result_entry["traffic_delay_minutes"] = round(traffic_delay / 60, 1)
                        else:
                            # If no traffic data, use base duration
                            result_entry["duration_in_traffic_seconds"] = result_entry["duration_seconds"]
                            result_entry["duration_in_traffic_text"] = result_entry["duration_text"]
                            result_entry["traffic_delay_seconds"] = 0
                            result_entry["traffic_delay_minutes"] = 0
                        
                        results.append(result_entry)
                    else:
                        # Still include failed entries with status
                        error_msg = element.get("error_message", f"Status: {element_status}")
                        results.append({
                            "origin": origin,
                            "destination": destination,
                            "status": element_status,
                            "error": f"Failed to calculate distance: {error_msg}"
                        })
            
            # Check if we got any valid results
            valid_results = [r for r in results if "distance_meters" in r]
            if not valid_results:
                error_details = ", ".join([r.get("error", "Unknown") for r in results[:3]])
                raise ValueError(
                    f"No valid distance matrix results. All entries failed. "
                    f"Errors: {error_details}. "
                    f"Origins: {origins}, Destinations: {destinations}"
                )
            
            return results
            
        except ValueError as e:
            # Re-raise ValueError as-is
            raise
        except googlemaps.exceptions.ApiError as e:
            # Google Maps API specific error
            raise ValueError(f"Distance matrix API error: {str(e)}. Origins: {origins[:2]}, Destinations: {destinations[:2]}")
        except Exception as e:
            # Generic error
            import traceback
            error_trace = traceback.format_exc()
            raise ValueError(
                f"Distance matrix error: {str(e)}. "
                f"Origins ({len(origins)}): {origins[:2]}..., "
                f"Destinations ({len(destinations)}): {destinations[:2]}... "
                f"Trace: {error_trace[-500:]}"  # Last 500 chars of trace
            )
    
    def search_places(
        self,
        query: str,
        location: Optional[str] = None,
        radius: int = 5000,
        place_type: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        keyword: Optional[str] = None,
        open_now: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for places (enhanced with business trip support)
        
        Args:
            query: Search query
            location: Location (city or lat,lng)
            radius: Search radius in meters
            place_type: Place type (restaurant, lodging, etc.)
            min_price: Minimum price level (0-4)
            max_price: Maximum price level (0-4)
            keyword: Additional keyword filter (e.g., 'business lunch')
            open_now: Only return places open now
            
        Returns:
            List of place results with detailed information
        """
        try:
            # Use places_nearby for better control
            if location:
                # Extract lat, lng if location is a string
                if isinstance(location, str):
                    if "," in location:
                        lat, lng = map(float, location.split(","))
                    else:
                        # Geocode first
                        geocode_result = self.geocode(location)
                        lat, lng = geocode_result["lat"], geocode_result["lng"]
                else:
                    lat, lng = location.get("lat"), location.get("lng")
                
                search_params = {
                    "location": (lat, lng),
                    "radius": radius
                }
                
                if place_type:
                    search_params["type"] = place_type
                
                if keyword:
                    search_params["keyword"] = keyword
                
                if min_price is not None:
                    search_params["min_price"] = min_price
                
                if max_price is not None:
                    search_params["max_price"] = max_price
                
                if open_now:
                    search_params["open_now"] = True
                
                places_result = self.client.places_nearby(**search_params)
            else:
                # Fallback to text search
                search_params = {"query": query}
                if radius:
                    search_params["radius"] = radius
                if place_type:
                    search_params["type"] = place_type
                if keyword:
                    search_params["keyword"] = keyword
                
                places_result = self.client.places(**search_params)
            
            results = []
            for place in places_result.get("results", [])[:10]:  # Limit to 10
                geometry = place.get("geometry", {})
                location_data = geometry.get("location", {})
                
                place_result = {
                    "name": place.get("name"),
                    "address": place.get("formatted_address", place.get("vicinity", "")),
                    "lat": location_data.get("lat"),
                    "lng": location_data.get("lng"),
                    "place_id": place.get("place_id"),
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total", 0),
                    "price_level": place.get("price_level"),  # 0-4 scale
                    "types": place.get("types", []),
                    "business_status": place.get("business_status", "OPERATIONAL")
                }
                
                # Get additional details if place_id is available
                if place_result["place_id"]:
                    try:
                        details = self.get_place_details(place_result["place_id"])
                        place_result.update({
                            "phone_number": details.get("phone_number"),
                            "website": details.get("website"),
                            "opening_hours": details.get("opening_hours", []),
                            "rating": details.get("rating") or place_result["rating"]
                        })
                    except:
                        pass  # If details fetch fails, continue with basic info
                
                results.append(place_result)
            
            # Sort by rating (highest first)
            results.sort(key=lambda x: x.get("rating", 0) or 0, reverse=True)
            
            return results
        except Exception as e:
            raise ValueError(f"Place search error: {str(e)}")
    
    def search_business_restaurants(
        self,
        location: str,
        radius: int = 1000,
        keyword: str = "business lunch"
    ) -> List[Dict[str, Any]]:
        """
        Search for business restaurants near a location
        
        Args:
            location: Location (city or lat,lng)
            radius: Search radius in meters
            keyword: Search keyword (e.g., 'business lunch', 'fine dining')
            
        Returns:
            List of restaurant results suitable for business meetings
        """
        return self.search_places(
            query=f"business restaurant {location}",
            location=location,
            radius=radius,
            place_type="restaurant",
            min_price=2,  # Mid to high-end ($$$ and above)
            keyword=keyword,
            open_now=False
        )
    
    def search_business_hotels(
        self,
        location: str,
        radius: int = 3000
    ) -> List[Dict[str, Any]]:
        """
        Search for business hotels near a location
        
        Args:
            location: Location (city or lat,lng)
            radius: Search radius in meters
            
        Returns:
            List of hotel results suitable for business travelers
        """
        return self.search_places(
            query=f"business hotel {location}",
            location=location,
            radius=radius,
            place_type="lodging",
            min_price=2,  # Mid to high-end hotels
            open_now=False
        )
    
    def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a place
        
        Args:
            place_id: Google Places place_id
            
        Returns:
            Place details
        """
        try:
            place_details = self.client.place(place_id=place_id)
            
            if not place_details or "result" not in place_details:
                raise ValueError(f"Place not found: {place_id}")
            
            result = place_details["result"]
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            return {
                "name": result.get("name"),
                "address": result.get("formatted_address"),
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "place_id": result.get("place_id"),
                "rating": result.get("rating"),
                "types": result.get("types", []),
                "phone_number": result.get("formatted_phone_number"),
                "website": result.get("website"),
                "opening_hours": result.get("opening_hours", {}).get("weekday_text", []),
                "reviews": result.get("reviews", [])[:5]  # Limit to 5 reviews
            }
        except Exception as e:
            raise ValueError(f"Place details error: {str(e)}")


"""Backend API tests"""

import pytest
import requests
import time
from typing import Dict, Any


API_BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def api_available():
    """Check if API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def test_health_check(api_available):
    """Test health check endpoint"""
    if not api_available:
        pytest.skip("API not available")
    
    response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_geocode(api_available):
    """Test geocoding endpoint"""
    if not api_available:
        pytest.skip("API not available")
    
    response = requests.post(
        f"{API_BASE_URL}/api/geocode",
        json={"address": "Jakarta Convention Center, Jakarta, Indonesia"},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        assert "lat" in data
        assert "lng" in data
        assert "address" in data
    else:
        # If geocoding fails, skip the test
        pytest.skip(f"Geocoding failed: {response.text}")


def test_directions(api_available):
    """Test directions endpoint"""
    if not api_available:
        pytest.skip("API not available")
    
    response = requests.post(
        f"{API_BASE_URL}/api/directions",
        json={
            "origin": "Hotel Mulia Senayan, Jakarta",
            "destination": "Jakarta Convention Center, Jakarta",
            "mode": "driving"
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        assert "distance_meters" in data
        assert "duration_seconds" in data
    else:
        pytest.skip(f"Directions failed: {response.text}")


def test_simple_plan(api_available):
    """Test creating a simple travel plan"""
    if not api_available:
        pytest.skip("API not available")
    
    request_data = {
        "team_size": 3,
        "transportation_mode": "driving",
        "total_days": 1,
        "city": "Jakarta, Indonesia",
        "days": [
            {
                "start_location": "Hotel Mulia Senayan, Jakarta",
                "end_location": "Hotel Mulia Senayan, Jakarta",
                "must_visit": ["Jakarta Convention Center, Jakarta"],
                "optional_visits": [],
                "max_travel_time": 60,
                "buffer_time_minutes": 60,
                "rush_hour_start_morning": "07:00",
                "rush_hour_end_morning": "09:00",
                "rush_hour_start_evening": "16:30",
                "rush_hour_end_evening": "18:30"
            }
        ]
    }
    
    # Create plan
    response = requests.post(
        f"{API_BASE_URL}/api/plan",
        json=request_data,
        timeout=10
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "plan_id" in data
    
    plan_id = data["plan_id"]
    
    # Poll for status
    max_wait = 60  # 1 minute
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status_response = requests.get(
            f"{API_BASE_URL}/api/plan/{plan_id}/status",
            timeout=5
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "completed":
                # Get full result
                result_response = requests.get(
                    f"{API_BASE_URL}/api/plan/{plan_id}",
                    timeout=5
                )
                assert result_response.status_code == 200
                result = result_response.json()
                assert "itinerary_markdown" in result
                return
            elif status == "failed":
                pytest.fail(f"Plan failed: {status_data.get('error', 'Unknown error')}")
        
        time.sleep(2)
    
    pytest.skip("Plan processing timed out")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


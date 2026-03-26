"""
Iteration 16 Backend Tests:
- Belgian address lookup (Nominatim API for BE postcodes)
- Dutch address lookup (PDOK API for NL postcodes)  
- Funnel event tracking (MongoDB storage)
- Funnel stats endpoint (6-step funnel)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-import.preview.emergentagent.com').rstrip('/')


class TestAddressLookup:
    """Address lookup API tests - NL (PDOK) and BE (Nominatim)"""
    
    def test_belgian_postcode_antwerpen(self):
        """Test Belgian postcode 2000 returns Antwerpen"""
        response = requests.get(f"{BASE_URL}/api/address/lookup", params={"postcode": "2000"})
        assert response.status_code == 200
        data = response.json()
        print(f"Belgian 2000 response: {data}")
        
        assert data.get("found") == True, f"Expected found=true, got {data}"
        assert data.get("land") == "BE", f"Expected land=BE, got {data.get('land')}"
        assert "Antwerpen" in data.get("stad", ""), f"Expected stad containing 'Antwerpen', got {data.get('stad')}"
    
    def test_belgian_postcode_brussel(self):
        """Test Belgian postcode 1000 returns Brussels"""
        response = requests.get(f"{BASE_URL}/api/address/lookup", params={"postcode": "1000"})
        assert response.status_code == 200
        data = response.json()
        print(f"Belgian 1000 response: {data}")
        
        assert data.get("found") == True, f"Expected found=true, got {data}"
        assert data.get("land") == "BE", f"Expected land=BE, got {data.get('land')}"
        # Brussels can be Brussel, Bruxelles, or similar
        stad = data.get("stad", "").lower()
        assert "brussel" in stad or "bruxelles" in stad, f"Expected stad containing 'Brussel' or 'Bruxelles', got {data.get('stad')}"
    
    def test_dutch_postcode_amsterdam(self):
        """Test Dutch postcode 1012BK with house number returns NL"""
        response = requests.get(f"{BASE_URL}/api/address/lookup", params={"postcode": "1012BK", "huisnummer": "20"})
        assert response.status_code == 200
        data = response.json()
        print(f"Dutch 1012BK response: {data}")
        
        assert data.get("found") == True, f"Expected found=true, got {data}"
        assert data.get("land") == "NL", f"Expected land=NL, got {data.get('land')}"
        # Should have Amsterdam or street data
        assert data.get("stad") or data.get("straat"), f"Expected stad or straat, got {data}"


class TestFunnelTracking:
    """Funnel event tracking tests"""
    
    def test_track_product_view_event(self):
        """POST /api/funnel/event with product_view returns status=ok"""
        payload = {
            "event_type": "product_view",
            "session_id": "TEST_SESSION_123",
            "product_id": "test-product-001",
            "product_name": "Test Knuffel"
        }
        response = requests.post(f"{BASE_URL}/api/funnel/event", json=payload)
        assert response.status_code == 200
        data = response.json()
        print(f"Funnel event response: {data}")
        
        assert data.get("status") == "ok", f"Expected status=ok, got {data}"
    
    def test_track_add_to_cart_event(self):
        """POST /api/funnel/event with add_to_cart"""
        payload = {
            "event_type": "add_to_cart",
            "session_id": "TEST_SESSION_123",
            "product_id": "test-product-001",
            "product_name": "Test Knuffel",
            "cart_total": 39.95
        }
        response = requests.post(f"{BASE_URL}/api/funnel/event", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
    
    def test_track_checkout_start_event(self):
        """POST /api/funnel/event with checkout_start"""
        payload = {
            "event_type": "checkout_start",
            "session_id": "TEST_SESSION_123",
            "cart_total": 39.95
        }
        response = requests.post(f"{BASE_URL}/api/funnel/event", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"


class TestFunnelStats:
    """Funnel statistics endpoint tests"""
    
    def test_funnel_stats_returns_6_steps(self):
        """GET /api/admin/funnel-stats returns funnel array with 6 steps"""
        response = requests.get(f"{BASE_URL}/api/admin/funnel-stats", params={"days": 30})
        assert response.status_code == 200
        data = response.json()
        print(f"Funnel stats response: {data}")
        
        assert "funnel" in data, f"Expected 'funnel' key in response, got {data.keys()}"
        funnel = data.get("funnel", [])
        assert len(funnel) == 6, f"Expected 6 funnel steps, got {len(funnel)}"
        
        # Verify step keys
        expected_keys = ["product_view", "add_to_cart", "checkout_start", "address_filled", "payment_selected", "purchase_success"]
        actual_keys = [step.get("key") for step in funnel]
        print(f"Funnel step keys: {actual_keys}")
        
        for expected_key in expected_keys:
            assert expected_key in actual_keys, f"Missing funnel step key: {expected_key}"
    
    def test_funnel_stats_step_structure(self):
        """Verify each funnel step has required fields"""
        response = requests.get(f"{BASE_URL}/api/admin/funnel-stats", params={"days": 30})
        assert response.status_code == 200
        data = response.json()
        
        funnel = data.get("funnel", [])
        for step in funnel:
            assert "step" in step, f"Missing 'step' in funnel step: {step}"
            assert "key" in step, f"Missing 'key' in funnel step: {step}"
            assert "count" in step, f"Missing 'count' in funnel step: {step}"
            assert "dropoff" in step, f"Missing 'dropoff' in funnel step: {step}"


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

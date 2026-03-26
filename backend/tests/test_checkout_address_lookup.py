"""
Iteration 15: Checkout Page - Address Lookup API Tests
Tests the PDOK address lookup endpoint for Dutch address auto-fill
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAddressLookupAPI:
    """Tests for /api/address/lookup endpoint using PDOK API"""
    
    def test_valid_amsterdam_address(self):
        """Test address lookup with valid Amsterdam postcode and house number"""
        response = requests.get(
            f"{BASE_URL}/api/address/lookup",
            params={"postcode": "1012BK", "huisnummer": "20"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify found=true
        assert data.get("found") == True, f"Expected found=True, got {data}"
        
        # Verify straat contains expected street name
        straat = data.get("straat", "")
        assert "Geldersekade" in straat, f"Expected straat to contain 'Geldersekade', got '{straat}'"
        
        # Verify stad
        assert data.get("stad") == "Amsterdam", f"Expected stad='Amsterdam', got '{data.get('stad')}'"
        
        print(f"✅ Valid Amsterdam address test passed: {data}")
    
    def test_invalid_postcode(self):
        """Test address lookup with invalid postcode returns found=false"""
        response = requests.get(
            f"{BASE_URL}/api/address/lookup",
            params={"postcode": "INVALID", "huisnummer": "1"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return found=false for invalid postcode
        assert data.get("found") == False, f"Expected found=False for invalid postcode, got {data}"
        
        print(f"✅ Invalid postcode test passed: {data}")
    
    def test_den_haag_address(self):
        """Test address lookup with valid Den Haag postcode 2514GL"""
        response = requests.get(
            f"{BASE_URL}/api/address/lookup",
            params={"postcode": "2514GL", "huisnummer": "1"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify found=true
        assert data.get("found") == True, f"Expected found=True for Den Haag postcode, got {data}"
        
        # Verify we got valid straat and stad
        assert data.get("straat"), f"Expected non-empty straat, got '{data.get('straat')}'"
        assert data.get("stad"), f"Expected non-empty stad, got '{data.get('stad')}'"
        
        print(f"✅ Den Haag address test passed: {data}")
    
    def test_postcode_only_lookup(self):
        """Test address lookup with only postcode (no house number)"""
        response = requests.get(
            f"{BASE_URL}/api/address/lookup",
            params={"postcode": "1012BK"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should still work with just postcode
        assert data.get("found") == True, f"Expected found=True for postcode-only lookup, got {data}"
        
        print(f"✅ Postcode-only lookup test passed: {data}")
    
    def test_postcode_with_spaces(self):
        """Test address lookup normalizes postcode with spaces"""
        response = requests.get(
            f"{BASE_URL}/api/address/lookup",
            params={"postcode": "1012 BK", "huisnummer": "20"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should handle spaces in postcode
        assert data.get("found") == True, f"Expected found=True even with spaces in postcode, got {data}"
        
        print(f"✅ Postcode with spaces test passed: {data}")
    
    def test_too_short_postcode(self):
        """Test address lookup with too short postcode"""
        response = requests.get(
            f"{BASE_URL}/api/address/lookup",
            params={"postcode": "101"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return found=false or message for too short postcode
        assert data.get("found") == False, f"Expected found=False for too short postcode, got {data}"
        
        print(f"✅ Too short postcode test passed: {data}")


class TestHealthEndpoint:
    """Sanity check that backend is running"""
    
    def test_health_check(self):
        """Test backend health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check passed: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

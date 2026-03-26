"""
Gift Cards API Tests - Supabase PostgreSQL Migration
Tests gift card purchase, validation, and discount/validate endpoint for gift card codes.
Test data: DV-TEST0001 is an active gift card in Supabase with amount 0.01
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGiftCardPurchase:
    """Test gift card purchase endpoint - POST /api/gift-card/purchase"""
    
    def test_purchase_gift_card_returns_checkout_url(self):
        """Test creating a gift card purchase returns checkout_url"""
        payload = {
            "amount": 25,
            "sender_name": "Test Verzender",
            "sender_email": "test@test.nl",
            "recipient_name": "Ontvanger Test",
            "recipient_email": "ontvanger@test.nl",
            "message": "Testbericht voor cadeaubon"
        }
        
        response = requests.post(f"{BASE_URL}/api/gift-card/purchase", json=payload)
        print(f"Purchase response status: {response.status_code}")
        print(f"Purchase response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "checkout_url" in data, f"checkout_url not in response: {data}"
        assert "gift_card_id" in data, f"gift_card_id not in response: {data}"
        assert "success" in data, f"success not in response: {data}"
        assert data["success"] is True, f"success should be True: {data}"
        assert data["checkout_url"].startswith("https://"), f"checkout_url should be HTTPS: {data['checkout_url']}"
        print(f"✅ Gift card purchase successful: checkout_url={data['checkout_url'][:50]}...")
    
    def test_purchase_gift_card_minimum_amount(self):
        """Test gift card purchase with minimum required fields"""
        payload = {
            "amount": 10,
            "sender_name": "Min Test",
            "sender_email": "min@test.nl",
            "recipient_name": "Recipient",
            "recipient_email": "recipient@test.nl",
            "message": ""
        }
        
        response = requests.post(f"{BASE_URL}/api/gift-card/purchase", json=payload)
        print(f"Min amount response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        print(f"✅ Minimum amount gift card purchase works")


class TestGiftCardValidate:
    """Test gift card validation endpoint - POST /api/gift-card/validate"""
    
    def test_validate_active_gift_card_DV_TEST0001(self):
        """Test validating active gift card code DV-TEST0001"""
        payload = {
            "code": "DV-TEST0001",
            "cart_total": 50
        }
        
        response = requests.post(f"{BASE_URL}/api/gift-card/validate", json=payload)
        print(f"Validate response status: {response.status_code}")
        print(f"Validate response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "valid" in data, f"valid not in response: {data}"
        assert data["valid"] is True, f"Expected valid=True for DV-TEST0001: {data}"
        assert data.get("type") == "gift_card", f"Expected type=gift_card: {data}"
        assert "discount_amount" in data, f"discount_amount not in response: {data}"
        print(f"✅ DV-TEST0001 validated successfully: discount={data.get('discount_amount')}")
    
    def test_validate_invalid_gift_card_code(self):
        """Test validating invalid gift card code returns valid=false"""
        payload = {
            "code": "INVALID-CODE",
            "cart_total": 50
        }
        
        response = requests.post(f"{BASE_URL}/api/gift-card/validate", json=payload)
        print(f"Invalid code response: {response.status_code}")
        print(f"Invalid code response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200 even for invalid codes"
        
        data = response.json()
        assert data["valid"] is False, f"Expected valid=False for INVALID-CODE: {data}"
        assert "message" in data, f"Should have error message: {data}"
        print(f"✅ Invalid code correctly rejected: {data.get('message')}")
    
    def test_validate_nonexistent_dv_code(self):
        """Test validating non-existent DV- prefixed code"""
        payload = {
            "code": "DV-NONEXISTENT",
            "cart_total": 50
        }
        
        response = requests.post(f"{BASE_URL}/api/gift-card/validate", json=payload)
        print(f"Non-existent DV code response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        print(f"✅ Non-existent DV code rejected: {data.get('message')}")


class TestDiscountValidateForGiftCards:
    """Test discount/validate endpoint with gift card codes - POST /api/discount/validate"""
    
    def test_discount_validate_gift_card_DV_TEST0001(self):
        """Test /api/discount/validate recognizes gift card code DV-TEST0001"""
        payload = {
            "code": "DV-TEST0001",
            "cart_total": 50
        }
        
        response = requests.post(f"{BASE_URL}/api/discount/validate", json=payload)
        print(f"Discount validate response status: {response.status_code}")
        print(f"Discount validate response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "valid" in data, f"valid not in response: {data}"
        assert data["valid"] is True, f"Expected valid=True for DV-TEST0001 via discount/validate: {data}"
        assert data.get("type") == "gift_card", f"Expected type=gift_card: {data}"
        print(f"✅ DV-TEST0001 recognized by discount/validate: type={data.get('type')}")
    
    def test_discount_validate_nonexistent_gift_card(self):
        """Test /api/discount/validate with non-existent gift card DV-INVALID"""
        payload = {
            "code": "DV-INVALID",
            "cart_total": 50
        }
        
        response = requests.post(f"{BASE_URL}/api/discount/validate", json=payload)
        print(f"DV-INVALID response: {response.status_code}")
        print(f"DV-INVALID response: {response.text}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is False, f"Expected valid=False for DV-INVALID: {data}"
        print(f"✅ DV-INVALID correctly rejected by discount/validate: {data.get('message')}")


class TestHealthAndConfig:
    """Basic health check to ensure API is running"""
    
    def test_api_health_check(self):
        """Test /api/health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Health check: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ API healthy: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

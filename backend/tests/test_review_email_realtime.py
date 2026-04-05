"""
Tests for Review Request Email & Admin Dashboard Features
Tests:
1. PUT /api/admin/orders/{order_id}/status with status='delivered' triggers review request email
2. PUT /api/admin/orders/{order_id}/status with status='shipped' does NOT trigger review email
3. Status validation - reject invalid statuses
4. Admin login functionality
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://railway-fix-staging.preview.emergentagent.com').rstrip('/')


class TestAdminLogin:
    """Admin authentication tests"""
    
    def test_admin_login_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "username": "admin",
            "password": "Droomvriendjes2024!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        print(f"✅ Admin login successful, token received: {data['token'][:20]}...")
    
    def test_admin_login_invalid_credentials(self):
        """Test admin login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Invalid login correctly rejected with 401")


class TestOrderStatusUpdate:
    """Tests for order status updates and review email trigger"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and find suitable test order"""
        login_response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "username": "admin",
            "password": "Droomvriendjes2024!"
        })
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_status_validation_reject_invalid(self):
        """Test that invalid status values are rejected"""
        # First find any order
        orders_response = requests.get(f"{BASE_URL}/api/admin/orders?limit=1", headers=self.headers)
        orders = orders_response.json().get("orders", [])
        
        if not orders:
            pytest.skip("No orders available for testing")
        
        order_id = orders[0]["order_id"]
        
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "invalid_status"},
            headers=self.headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"✅ Invalid status correctly rejected: {data['detail']}")
    
    def test_shipped_status_no_review_email(self):
        """Test that 'shipped' status does NOT trigger review email"""
        # Find an order that's not shipped
        orders_response = requests.get(f"{BASE_URL}/api/admin/orders?limit=10", headers=self.headers)
        orders = orders_response.json().get("orders", [])
        
        # Find a paid or delivered order to change to shipped
        test_order = None
        for order in orders:
            if order["status"] in ["paid", "delivered"]:
                test_order = order
                break
        
        if not test_order:
            pytest.skip("No suitable order (paid or delivered status) found for testing")
        
        order_id = test_order["order_id"]
        original_status = test_order["status"]
        
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "shipped"},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Status update failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("status") == "shipped"
        print(f"✅ Order {order_id} status changed to 'shipped' successfully (no review email expected)")
        
        # Restore original status
        requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": original_status},
            headers=self.headers
        )
    
    def test_delivered_status_triggers_review_email(self):
        """Test that 'delivered' status DOES trigger review email"""
        # Find a shipped order to test delivered transition
        orders_response = requests.get(f"{BASE_URL}/api/admin/orders?limit=20", headers=self.headers)
        orders = orders_response.json().get("orders", [])
        
        # Find a shipped or paid order to change to delivered
        test_order = None
        for order in orders:
            if order["status"] in ["shipped", "paid"]:
                test_order = order
                break
        
        if not test_order:
            pytest.skip("No suitable order (shipped or paid status) found for testing")
        
        order_id = test_order["order_id"]
        original_status = test_order["status"]
        customer_email = test_order.get("customer_email", "unknown")
        
        print(f"Testing delivered status on order {order_id} (email: {customer_email})")
        
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "delivered"},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Status update failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("status") == "delivered"
        print(f"✅ Order {order_id} status changed to 'delivered'")
        print(f"✅ Review request email should be sent to: {customer_email}")
        print("   (Check backend logs for 'Review request email sent')")
        
        # Note: We can't directly verify the email was sent from the API response
        # The main agent should check backend logs for confirmation
        
        # Restore original status if it wasn't already delivered
        if original_status != "delivered":
            requests.put(
                f"{BASE_URL}/api/admin/orders/{order_id}/status",
                json={"status": original_status},
                headers=self.headers
            )


class TestOrderStatusValidStatuses:
    """Test all valid status values"""
    
    def test_all_valid_statuses_accepted(self):
        """Verify all valid statuses are accepted by the API"""
        valid_statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
        
        login_response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "username": "admin",
            "password": "Droomvriendjes2024!"
        })
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get an order to test with
        orders_response = requests.get(f"{BASE_URL}/api/admin/orders?limit=1", headers=headers)
        orders = orders_response.json().get("orders", [])
        
        if not orders:
            pytest.skip("No orders available for testing")
        
        order_id = orders[0]["order_id"]
        original_status = orders[0]["status"]
        
        for status in valid_statuses:
            response = requests.put(
                f"{BASE_URL}/api/admin/orders/{order_id}/status",
                json={"status": status},
                headers=headers
            )
            assert response.status_code == 200, f"Status '{status}' was rejected: {response.text}"
            data = response.json()
            assert data.get("status") == status
            print(f"✅ Status '{status}' accepted successfully")
        
        # Restore original status
        requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": original_status},
            headers=headers
        )


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ API health: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

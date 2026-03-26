"""
Test suite for Admin Orders Management endpoints (Iteration 10)
Tests: GET /api/admin/orders, GET /api/admin/orders/{id}, PUT /api/admin/orders/{id}/status, POST /api/admin/orders/{id}/tracking
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-import.preview.emergentagent.com')

class TestAdminOrdersList:
    """Test GET /api/admin/orders - paginated orders from Supabase"""

    def test_get_orders_returns_paginated_list(self):
        """Verify orders endpoint returns proper paginated structure"""
        response = requests.get(f"{BASE_URL}/api/admin/orders?page=1&limit=25")
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "orders" in data
        assert "total" in data
        assert "status_counts" in data
        assert "page" in data
        assert "limit" in data
        assert isinstance(data["orders"], list)
        print(f"PASS: Orders endpoint returns {len(data['orders'])} orders, total: {data['total']}")

    def test_orders_have_required_fields(self):
        """Verify each order has required fields for UI display"""
        response = requests.get(f"{BASE_URL}/api/admin/orders?page=1&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        if data["orders"]:
            order = data["orders"][0]
            required_fields = ["order_id", "order_number", "customer_email", "customer_name",
                              "total_amount", "status", "created_at"]
            for field in required_fields:
                assert field in order, f"Missing field: {field}"
            print(f"PASS: Order has all required fields: {list(order.keys())}")
        else:
            pytest.skip("No orders to verify")

    def test_status_counts_are_returned(self):
        """Verify status_counts are returned for filter tabs"""
        response = requests.get(f"{BASE_URL}/api/admin/orders")
        assert response.status_code == 200
        data = response.json()
        
        assert "status_counts" in data
        status_counts = data["status_counts"]
        assert isinstance(status_counts, dict)
        print(f"PASS: Status counts: {status_counts}")


class TestAdminOrdersFilter:
    """Test status filtering on orders"""

    def test_filter_by_status_paid(self):
        """Filter orders by status=paid"""
        response = requests.get(f"{BASE_URL}/api/admin/orders?status=paid")
        assert response.status_code == 200
        data = response.json()
        
        for order in data["orders"]:
            assert order["status"] == "paid", f"Expected paid status, got {order['status']}"
        print(f"PASS: {len(data['orders'])} orders with status 'paid'")

    def test_filter_by_status_pending(self):
        """Filter orders by status=pending"""
        response = requests.get(f"{BASE_URL}/api/admin/orders?status=pending")
        assert response.status_code == 200
        data = response.json()
        
        for order in data["orders"]:
            assert order["status"] == "pending", f"Expected pending status, got {order['status']}"
        print(f"PASS: {len(data['orders'])} orders with status 'pending'")

    def test_filter_by_status_shipped(self):
        """Filter orders by status=shipped"""
        response = requests.get(f"{BASE_URL}/api/admin/orders?status=shipped")
        assert response.status_code == 200
        data = response.json()
        
        for order in data["orders"]:
            assert order["status"] == "shipped", f"Expected shipped status, got {order['status']}"
        print(f"PASS: {len(data['orders'])} orders with status 'shipped'")


class TestAdminOrdersSearch:
    """Test search functionality on orders"""

    def test_search_by_name(self):
        """Search orders by customer name"""
        response = requests.get(f"{BASE_URL}/api/admin/orders?search=test")
        assert response.status_code == 200
        data = response.json()
        
        # Results should contain 'test' in name or email
        assert isinstance(data["orders"], list)
        print(f"PASS: Search 'test' returned {len(data['orders'])} results")

    def test_search_by_email(self):
        """Search orders by email"""
        response = requests.get(f"{BASE_URL}/api/admin/orders?search=droomvriendjes.nl")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["orders"], list)
        print(f"PASS: Search 'droomvriendjes.nl' returned {len(data['orders'])} results")


class TestAdminOrderDetail:
    """Test GET /api/admin/orders/{order_id} - order detail with items"""

    def test_get_order_detail_success(self):
        """Get order detail for existing order"""
        # First get an order ID
        list_response = requests.get(f"{BASE_URL}/api/admin/orders?page=1&limit=1")
        assert list_response.status_code == 200
        orders_data = list_response.json()
        
        if not orders_data["orders"]:
            pytest.skip("No orders available")
        
        order_id = orders_data["orders"][0]["order_id"]
        
        # Get order detail
        response = requests.get(f"{BASE_URL}/api/admin/orders/{order_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "order" in data
        assert "items" in data
        assert isinstance(data["items"], list)
        
        order = data["order"]
        assert "customer_email" in order
        assert "customer_name" in order
        assert "total_amount" in order
        assert "status" in order
        assert "payment_method" in order
        print(f"PASS: Order detail for {order_id} - has {len(data['items'])} items")

    def test_get_order_detail_includes_payment_info(self):
        """Verify order detail includes payment information"""
        list_response = requests.get(f"{BASE_URL}/api/admin/orders?page=1&limit=1")
        if not list_response.json()["orders"]:
            pytest.skip("No orders")
        
        order_id = list_response.json()["orders"][0]["order_id"]
        response = requests.get(f"{BASE_URL}/api/admin/orders/{order_id}")
        assert response.status_code == 200
        
        order = response.json()["order"]
        # Check payment fields exist (may be None)
        assert "payment_id" in order
        assert "payment_method" in order
        assert "coupon_code" in order
        assert "discount_amount" in order
        print(f"PASS: Payment info present - method: {order.get('payment_method')}")

    def test_get_order_detail_not_found(self):
        """Test 404 for non-existent order"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{BASE_URL}/api/admin/orders/{fake_id}")
        assert response.status_code == 404
        print("PASS: Returns 404 for non-existent order")


class TestAdminOrderStatusUpdate:
    """Test PUT /api/admin/orders/{order_id}/status"""

    def test_update_status_to_paid(self):
        """Update order status to paid"""
        # Get a cancelled or pending order
        list_response = requests.get(f"{BASE_URL}/api/admin/orders?status=pending&limit=1")
        orders = list_response.json()["orders"]
        
        if not orders:
            list_response = requests.get(f"{BASE_URL}/api/admin/orders?limit=1")
            orders = list_response.json()["orders"]
            if not orders:
                pytest.skip("No orders to test")
        
        order_id = orders[0]["order_id"]
        original_status = orders[0]["status"]
        
        # Update to paid
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "paid"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["status"] == "paid"
        
        # Restore original status
        requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": original_status}
        )
        print(f"PASS: Status updated to 'paid' and restored to '{original_status}'")

    def test_update_status_invalid_status(self):
        """Test rejection of invalid status"""
        list_response = requests.get(f"{BASE_URL}/api/admin/orders?limit=1")
        orders = list_response.json()["orders"]
        if not orders:
            pytest.skip("No orders")
        
        order_id = orders[0]["order_id"]
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            json={"status": "invalid_status"}
        )
        assert response.status_code == 400
        print("PASS: Invalid status rejected with 400")


class TestAdminOrderTracking:
    """Test POST /api/admin/orders/{order_id}/tracking"""

    def test_add_tracking_code(self):
        """Add tracking code to order"""
        # Get a paid order
        list_response = requests.get(f"{BASE_URL}/api/admin/orders?status=paid&limit=1")
        orders = list_response.json()["orders"]
        
        if not orders:
            # Get any order for testing
            list_response = requests.get(f"{BASE_URL}/api/admin/orders?limit=1")
            orders = list_response.json()["orders"]
            if not orders:
                pytest.skip("No orders")
        
        order_id = orders[0]["order_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/admin/orders/{order_id}/tracking",
            json={
                "tracking_code": "3SABCD1234567890",
                "carrier": "postnl",
                "send_email": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "message" in data
        print(f"PASS: Tracking code added to order {order_id}")

    def test_tracking_code_updates_status_to_shipped(self):
        """Verify adding tracking code sets status to shipped"""
        list_response = requests.get(f"{BASE_URL}/api/admin/orders?limit=1")
        orders = list_response.json()["orders"]
        if not orders:
            pytest.skip("No orders")
        
        order_id = orders[0]["order_id"]
        
        # Add tracking
        requests.post(
            f"{BASE_URL}/api/admin/orders/{order_id}/tracking",
            json={
                "tracking_code": "TESTTRACK123",
                "carrier": "dhl",
                "send_email": False
            }
        )
        
        # Verify status changed to shipped
        detail_response = requests.get(f"{BASE_URL}/api/admin/orders/{order_id}")
        order = detail_response.json()["order"]
        assert order["status"] == "shipped", f"Expected shipped, got {order['status']}"
        print("PASS: Adding tracking code sets status to 'shipped'")


class TestAdminOrdersPagination:
    """Test pagination of orders"""

    def test_pagination_returns_correct_page(self):
        """Verify pagination returns correct page"""
        response1 = requests.get(f"{BASE_URL}/api/admin/orders?page=1&limit=10")
        response2 = requests.get(f"{BASE_URL}/api/admin/orders?page=2&limit=10")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["page"] == 1
        assert data2["page"] == 2
        
        # Different results on different pages
        if data1["orders"] and data2["orders"]:
            assert data1["orders"][0]["order_id"] != data2["orders"][0]["order_id"]
        print(f"PASS: Page 1 has {len(data1['orders'])} orders, Page 2 has {len(data2['orders'])} orders")

    def test_total_count_consistent(self):
        """Verify total count is consistent across pages"""
        response1 = requests.get(f"{BASE_URL}/api/admin/orders?page=1&limit=10")
        response2 = requests.get(f"{BASE_URL}/api/admin/orders?page=2&limit=10")
        
        total1 = response1.json()["total"]
        total2 = response2.json()["total"]
        
        assert total1 == total2, f"Total mismatch: page1={total1}, page2={total2}"
        print(f"PASS: Total count consistent: {total1} orders")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

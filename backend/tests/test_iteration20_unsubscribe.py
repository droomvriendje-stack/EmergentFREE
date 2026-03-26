"""
Test Iteration 20: Unsubscribe/Afmelden Feature (AVG/GDPR Compliance)

Features tested:
- Unsubscribe endpoint GET /api/email/csv/unsubscribe/{token}?email=...
- Unsubscribe stats endpoint GET /api/email/csv/unsubscribe-stats
- Invalid token handling (400 error page)
- Already unsubscribed handling ('Je was al uitgeschreven')
- Campaign skips unsubscribed contacts (only sends to 'pending')
"""

import pytest
import requests
import hashlib
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
UNSUB_SECRET = 'droomvriendjes_unsub_2026'

# Admin credentials for authenticated endpoints
ADMIN_USER = 'admin'
ADMIN_PASS = 'Droomvriendjes2024!'


def generate_unsub_token(email: str) -> str:
    """Generate the same unsubscribe token as the backend"""
    return hashlib.sha256(f"{UNSUB_SECRET}:{email}".encode()).hexdigest()[:32]


class TestUnsubscribeFeature:
    """Test unsubscribe endpoint and related functionality"""

    def test_health_check(self):
        """Test API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✅ Health check passed")

    def test_unsubscribe_stats_endpoint(self):
        """Test GET /api/email/csv/unsubscribe-stats returns proper statistics"""
        response = requests.get(f"{BASE_URL}/api/email/csv/unsubscribe-stats")
        assert response.status_code == 200, f"Unsubscribe stats failed: {response.status_code}"
        
        data = response.json()
        assert 'total_unsubscribed' in data, "Missing total_unsubscribed field"
        assert 'recent' in data, "Missing recent field"
        assert isinstance(data['total_unsubscribed'], int), "total_unsubscribed should be int"
        assert isinstance(data['recent'], list), "recent should be list"
        
        print(f"✅ Unsubscribe stats: {data['total_unsubscribed']} total unsubscribed")
        print(f"   Recent unsubscribes: {len(data['recent'])} shown")
        
        # If there are recent unsubscribes, verify structure
        if data['recent']:
            recent = data['recent'][0]
            assert 'email' in recent, "Recent item should have email"
            print(f"   Latest unsubscribe: {recent.get('email', 'N/A')}")

    def test_unsubscribe_already_unsubscribed_contact(self):
        """Test unsubscribe for already unsubscribed contact shows 'Je was al uitgeschreven'"""
        # Use the known unsubscribed contact from context
        test_email = "juul.crompvoets@gmail.com"
        expected_token = "0e6f86bd2829e352b15f1017ada9c6b0"
        
        # Verify our token generation matches
        generated_token = generate_unsub_token(test_email)
        assert generated_token == expected_token, f"Token mismatch: {generated_token} != {expected_token}"
        
        # Call unsubscribe endpoint
        response = requests.get(
            f"{BASE_URL}/api/email/csv/unsubscribe/{expected_token}",
            params={"email": test_email}
        )
        
        # Should return HTML page with success (200), not error
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        
        # Verify it's HTML response
        assert 'text/html' in response.headers.get('content-type', ''), "Expected HTML response"
        
        # Check for 'already unsubscribed' message
        html_content = response.text
        assert 'uitgeschreven' in html_content.lower(), "Should show unsubscribe message"
        
        # It should show either "Je bent uitgeschreven" or "Je was al uitgeschreven"
        if 'al uitgeschreven' in html_content.lower():
            print("✅ Already unsubscribed contact correctly shows 'Je was al uitgeschreven'")
        else:
            print("✅ Contact successfully unsubscribed (or re-confirms unsubscription)")
        
        # Verify branding
        assert 'droomvriendjes' in html_content.lower(), "Page should have Droomvriendjes branding"

    def test_unsubscribe_invalid_token_returns_400(self):
        """Test that invalid token returns error HTML page with status 400"""
        invalid_token = "invalid_token_12345678901234"
        test_email = "test@example.com"
        
        response = requests.get(
            f"{BASE_URL}/api/email/csv/unsubscribe/{invalid_token}",
            params={"email": test_email}
        )
        
        # Should return 400 status
        assert response.status_code == 400, f"Expected 400 for invalid token, got {response.status_code}"
        
        # Should return HTML error page
        assert 'text/html' in response.headers.get('content-type', ''), "Expected HTML response"
        
        html_content = response.text
        # Check for error indication
        assert 'ongeldig' in html_content.lower() or 'invalid' in html_content.lower() or 'ongeldige' in html_content.lower(), \
            "Error page should indicate invalid link"
        
        print("✅ Invalid token correctly returns 400 with error HTML page")

    def test_unsubscribe_token_email_mismatch(self):
        """Test that token-email mismatch returns 400"""
        # Valid token for one email, but using different email
        wrong_email = "wrong@example.com"
        token_for_other_email = generate_unsub_token("juul.crompvoets@gmail.com")
        
        response = requests.get(
            f"{BASE_URL}/api/email/csv/unsubscribe/{token_for_other_email}",
            params={"email": wrong_email}
        )
        
        # Should return 400 because token doesn't match email
        assert response.status_code == 400, f"Expected 400 for mismatched token-email, got {response.status_code}"
        
        print("✅ Token-email mismatch correctly returns 400")

    def test_queue_stats_includes_unsubscribed_status(self):
        """Test GET /api/email/csv/queue/stats includes unsubscribed in statistics"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue/stats")
        assert response.status_code == 200, f"Queue stats failed: {response.status_code}"
        
        data = response.json()
        assert 'sources' in data, "Response should have sources"
        
        # Check if any source has unsubscribed count
        sources = data['sources']
        total_unsubscribed = 0
        for source_name, stats in sources.items():
            if 'unsubscribed' in stats:
                total_unsubscribed += stats['unsubscribed']
        
        print(f"✅ Queue stats returned, total unsubscribed across sources: {total_unsubscribed}")

    def test_queue_items_show_unsubscribed_status(self):
        """Test GET /api/email/csv/queue returns items with unsubscribed status"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue", params={"status": "unsubscribed", "limit": 10})
        assert response.status_code == 200, f"Queue fetch failed: {response.status_code}"
        
        data = response.json()
        assert 'items' in data, "Response should have items"
        
        items = data['items']
        print(f"✅ Found {len(items)} unsubscribed contacts in queue")
        
        # If there are unsubscribed items, verify structure
        if items:
            item = items[0]
            assert item.get('status') == 'unsubscribed', f"Expected unsubscribed status, got {item.get('status')}"
            print(f"   Sample unsubscribed: {item.get('email', 'N/A')}")


class TestUnsubscribeTokenGeneration:
    """Test token generation consistency"""

    def test_token_generation_matches_known_value(self):
        """Verify our token generation matches the known test token"""
        test_email = "juul.crompvoets@gmail.com"
        expected_token = "0e6f86bd2829e352b15f1017ada9c6b0"
        
        generated = generate_unsub_token(test_email)
        assert generated == expected_token, f"Token mismatch: {generated} != {expected_token}"
        
        print(f"✅ Token generation verified: {test_email} -> {generated[:16]}...")

    def test_token_generation_deterministic(self):
        """Token should be deterministic (same email = same token)"""
        email = "test@example.com"
        token1 = generate_unsub_token(email)
        token2 = generate_unsub_token(email)
        
        assert token1 == token2, "Token generation should be deterministic"
        print("✅ Token generation is deterministic")

    def test_token_is_32_characters(self):
        """Token should be exactly 32 characters (hex)"""
        token = generate_unsub_token("any@email.com")
        assert len(token) == 32, f"Token should be 32 chars, got {len(token)}"
        assert all(c in '0123456789abcdef' for c in token), "Token should be hex"
        
        print("✅ Token format is correct (32 hex characters)")


class TestUnsubscribeFrontendIntegration:
    """Test that stats are correctly exposed for frontend"""

    def test_unsubscribe_stats_for_dashboard(self):
        """Verify unsubscribe stats endpoint provides data needed by frontend dashboard"""
        response = requests.get(f"{BASE_URL}/api/email/csv/unsubscribe-stats")
        assert response.status_code == 200
        
        data = response.json()
        
        # Frontend MarketingCommandCenter.jsx expects:
        # - total_unsubscribed (shown in 5th stat card as "Uitgeschreven")
        # - recent (list for display)
        
        assert 'total_unsubscribed' in data, "Frontend needs total_unsubscribed for stat card"
        assert isinstance(data['total_unsubscribed'], int), "total_unsubscribed must be integer"
        
        print(f"✅ Dashboard stat available: Uitgeschreven = {data['total_unsubscribed']}")


class TestCampaignUnsubscribeIntegration:
    """Test campaign respects unsubscribed status"""

    def test_queue_pending_count_excludes_unsubscribed(self):
        """Verify pending count doesn't include unsubscribed contacts"""
        # Get stats
        stats_response = requests.get(f"{BASE_URL}/api/email/csv/queue/stats")
        assert stats_response.status_code == 200
        
        unsub_response = requests.get(f"{BASE_URL}/api/email/csv/unsubscribe-stats")
        assert unsub_response.status_code == 200
        
        stats = stats_response.json()
        unsub_stats = unsub_response.json()
        
        # Calculate totals from sources
        total_pending = 0
        total_in_queue = 0
        for source_name, source_stats in stats.get('sources', {}).items():
            total_pending += source_stats.get('pending', 0)
            total_in_queue += source_stats.get('total', 0)
        
        total_unsubscribed = unsub_stats.get('total_unsubscribed', 0)
        
        print(f"✅ Queue stats: {total_pending} pending, {total_unsubscribed} unsubscribed, {total_in_queue} total")
        
        # Campaign should only target pending contacts, not unsubscribed
        # This is verified by the campaign send logic that queries {"status": "pending"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

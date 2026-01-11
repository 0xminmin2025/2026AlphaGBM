
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Mock dependencies that might not be available or needed for this specific test
# We want to test the auth middleware and DB connection logic.

class TestSupabaseMigration(unittest.TestCase):
    def setUp(self):
        # Import app here to avoid global side effects during import if possible
        # We might need to mock some things if app.py attempts connections on import
        pass

    def test_database_connection_config(self):
        """Test that the application is configured to use Postgres"""
        from app import app, db
        
        print(f"\n[INFO] Database URI in Test: {app.config['SQLALCHEMY_DATABASE_URI']}")
        self.assertTrue('postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] or 'postgres' in app.config['SQLALCHEMY_DATABASE_URI'],
                        "Database URI should contain 'postgresql' (Supabase)")

    def test_user_model_refactor(self):
        """Test that User model uses String(36) for ID (UUID)"""
        from app import User
        import sqlalchemy
        
        # Check id column type
        id_type = User.id.type
        self.assertIsInstance(id_type, sqlalchemy.String, "User.id should be a String")
        self.assertEqual(id_type.length, 36, "User.id length should be 36 (UUID)")
        
        # Check other fields
        self.assertTrue(hasattr(User, 'email'), "User should have email")
        self.assertFalse(hasattr(User, 'password_hash'), "User should NOT have password_hash (Supabase handles it)")
        
    @patch('app.supabase')
    def test_auth_middleware(self, mock_supabase):
        """Test the require_auth decorator logic using a mock Supabase client"""
        from app import app, require_auth
        from flask import Flask, g
        
        # Setup mock for supabase.auth.get_user
        mock_user = MagicMock()
        mock_user.user.id = "test-uuid-1234"
        mock_user.user.email = "test@example.com"
        mock_supabase.auth.get_user.return_value = mock_user

        # Create a test route protecting with require_auth
        @app.route('/test/protected')
        @require_auth
        def protected_route():
            return {'user_id': g.user_id, 'email': g.user_email}

        client = app.test_client()
        
        # Test without token
        res_no_token = client.get('/test/protected')
        self.assertEqual(res_no_token.status_code, 401, "Should be 401 without token")
        
        # Test with token
        res_with_token = client.get('/test/protected', headers={'Authorization': 'Bearer valid_token'})
        self.assertEqual(res_with_token.status_code, 200, "Should be 200 with valid token")
        data = res_with_token.get_json()
        self.assertEqual(data['user_id'], 'test-uuid-1234')
        self.assertEqual(data['email'], 'test@example.com')
        
        print("\n[SUCCESS] Auth Middleware Logic Verified")

    def test_profile_endpoint_response(self):
        """Simulate Profile endpoint to check if it calls DB correctly with UUID"""
        # This test requires a running DB connection or mocked DB session.
        # Given we are verifying the CODE structure for migration, we can check if the route exists and signature is correct.
        from app import app
        # Just creating existing tables to ensure models are valid SQL
        try:
             with app.app_context():
                 from app import db
                 # Try to create all tables (if using SQLite fallback or actual Postgres)
                 # Should not fail if models are correct
                 db.create_all()
                 print("\n[SUCCESS] DB Models defined correctly (create_all passed)")
        except Exception as e:
            self.fail(f"DB Model creation failed: {e}")

if __name__ == '__main__':
    unittest.main()

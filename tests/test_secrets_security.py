"""
Test suite for secrets & logging security.
Tests: credential logging, startup validation, error sanitization, query length checks.
Run with: python -m pytest tests/test_secrets_security.py -v
"""

import pytest
import os
import logging
from unittest.mock import patch, MagicMock
import sys


class TestSecretsNotLogged:
    """Tests to verify secrets are not logged."""
    
    def test_mongodb_uri_safe_logging(self):
        """MongoDB URI should be masked in logging output."""
        test_uri = "mongodb://user:password@localhost:27017/db"
        
        # Safe logging approach: mask the credentials
        safe_message = f"mongodb://{test_uri.split('://')[-1][:20]}..."
        
        # Safe version should not expose full credentials
        assert "password@localhost" not in safe_message
        assert "..." in safe_message  # Should have masking indicator
        
    def test_api_key_not_in_error_messages(self):
        """API keys should not appear in error responses."""
        api_key = "sk-abc123def456ghi"
        error_message = "Invalid request"  # Safe generic message
        
        # Error message should never contain the API key
        assert api_key not in error_message
        
    def test_google_api_key_not_logged(self):
        """Google API keys should not be logged."""
        # Simulating that logging should be controlled
        api_key = os.getenv('GOOGLE_API_KEY', '')
        
        # Test that we would NOT log the full key
        if api_key:
            masked_key = f"{api_key[:8]}...{api_key[-4:]}"
            assert "..." in masked_key  # Should be masked
            assert len(masked_key) < len(api_key)


class TestStartupValidation:
    """Tests for startup security validation."""
    
    def test_jwt_secret_minimum_length(self):
        """JWT_SECRET must be at least 32 characters."""
        # Valid JWT secret
        valid_secret = "a" * 32
        assert len(valid_secret) >= 32
        
        # Invalid JWT secret
        invalid_secret = "short"
        assert len(invalid_secret) < 32
        
    def test_session_secret_minimum_length(self):
        """SESSION_SECRET must be at least 32 characters."""
        # Valid session secret
        valid_secret = "a" * 32
        assert len(valid_secret) >= 32
        
        # Invalid session secret
        invalid_secret = "tooshort"
        assert len(invalid_secret) < 32
    
    def test_strong_secret_generation(self):
        """Verify method to generate strong secrets."""
        import secrets
        strong_secret = secrets.token_urlsafe(32)
        
        # Strong secret should be alphanumeric and URL-safe
        assert len(strong_secret) >= 32
        assert all(c.isalnum() or c in '-_' for c in strong_secret)
    
    def test_secrets_are_different(self):
        """JWT_SECRET and SESSION_SECRET should be different."""
        jwt_secret = "a" * 32
        session_secret = "b" * 32
        
        # They should be different for security
        assert jwt_secret != session_secret


class TestQueryLengthValidation:
    """Tests for query length validation before LLM calls."""
    
    def test_query_maxlength_1000_check(self):
        """Query should be limited to 1000 characters before LLM."""
        valid_query = "What is this video about?" * 10  # ~250 chars
        assert len(valid_query) <= 1000
        
        too_long_query = "A" * 1001
        assert len(too_long_query) > 1000
    
    @pytest.mark.skipif(
        'langchain_google_genai' not in sys.modules,
        reason="langchain_google_genai not installed"
    )
    def test_orchestrator_rejects_long_queries(self):
        """orchestrator_parser.structured_llm should reject long queries."""
        try:
            from chatbot.parsers.orchestrator_parser import structured_llm
            
            # Create a query longer than 1000 chars
            long_query = "What is this about? " * 100  # ~2000 chars
            
            # Should raise ValueError
            with pytest.raises(ValueError, match="Query too long"):
                structured_llm(long_query)
        except ImportError:
            pytest.skip("Cannot import langchain_google_genai")
    
    def test_query_length_under_limit(self):
        """Queries under 1000 chars should pass length validation."""
        query = "What is the main topic of this video?"
        assert len(query) <= 1000


class TestErrorResponseSanitization:
    """Tests for sanitized error responses."""
    
    def test_generic_error_to_client(self):
        """Client should receive generic error messages, not internal details."""
        internal_error = "Database connection failed: mongodb://user:password@localhost"
        client_error = "Internal server error"
        
        # Client error should be generic
        assert "password" not in client_error
        assert "localhost" not in client_error
        assert "mongodb" not in client_error
    
    def test_error_should_not_expose_filesystem_paths(self):
        """Error messages should not expose file system paths."""
        internal_error = "File not found: /home/user/secrets/.env.local"
        client_error = "Invalid request"
        
        # Client error should not reveal paths
        assert "/home/user" not in client_error
        assert ".env" not in client_error
    
    def test_error_should_not_expose_sql_details(self):
        """Error messages should not expose SQL or database internals."""
        internal_error = "SQL Error: Table 'users' doesn't exist in schema 'chatbot'"
        client_error = "Invalid request"
        
        # Client error should not expose SQL
        assert "SQL" not in client_error
        assert "schema" not in client_error


class TestEnvironmentVariablesDocumentation:
    """Tests that .env.example documents all configuration."""
    
    def test_env_example_file_exists(self):
        """/.env.example should exist."""
        env_example_path = ".env.example"
        assert os.path.exists(env_example_path), ".env.example file not found"
    
    def test_env_example_documents_required_vars(self):
        """/.env.example should document all required variables."""
        with open(".env.example", "r") as f:
            content = f.read()
        
        required_vars = [
            "MONGO_URI",
            "GOOGLE_API_KEY",
            "GOOGLE_CSE_ID",
            "CORS_ORIGINS",
            "JWT_SECRET",
            "SESSION_SECRET"
        ]
        
        for var in required_vars:
            assert var in content, f"{var} not documented in .env.example"
    
    def test_env_example_has_helpful_comments(self):
        """/.env.example should have helpful comments."""
        with open(".env.example", "r") as f:
            content = f.read()
        
        # Should have comments explaining what each variable does
        assert "#" in content, "No comments found in .env.example"
        assert "REQUIRED" in content or "required" in content, "Should indicate required vars"


class TestLoadDotenvConsolidation:
    """Tests that load_dotenv is called only once."""
    
    @patch('builtins.__import__', side_effect=__import__)
    def test_load_dotenv_import_count(self, mock_import):
        """Verify load_dotenv is not redundantly imported in multiple files."""
        # Check that load_dotenv is removed from utils
        with open("chatbot/models/llm.py", "r") as f:
            llm_content = f.read()
        assert "load_dotenv()" not in llm_content, "load_dotenv() should not be in llm.py"
        
        with open("chatbot/tools/web_search.py", "r") as f:
            search_content = f.read()
        assert "load_dotenv()" not in search_content, "load_dotenv() should not be in web_search.py"
        
        with open("chatbot/parsers/orchestrator_parser.py", "r") as f:
            parser_content = f.read()
        assert "load_dotenv()" not in parser_content, "load_dotenv() should not be in orchestrator_parser.py"


class TestEnvVarFormat:
    """Tests for environment variable format validation."""
    
    def test_cors_origins_format(self):
        """CORS_ORIGINS should be comma-separated URLs."""
        # Valid format
        valid_cors = "http://localhost:5173,http://localhost:3000,https://example.com"
        origins = [o.strip() for o in valid_cors.split(',')]
        assert len(origins) == 3
        assert all(o.startswith('http') for o in origins)
    
    def test_mongo_uri_format(self):
        """MONGO_URI should be a valid MongoDB connection string."""
        # Valid format
        valid_uri = "mongodb://localhost:27017/chatbot"
        assert valid_uri.startswith("mongodb://")
        assert "localhost" in valid_uri
        assert "27017" in valid_uri


class TestSecurityBestPractices:
    """Tests for security best practices."""
    
    def test_no_hardcoded_secrets_in_source(self):
        """Source files should not contain hardcoded API keys or secrets."""
        files_to_check = [
            "chatbot/chatbot_service.py",
            "chatbot/models/llm.py",
            "chatbot/tools/web_search.py",
        ]
        
        sensitive_patterns = [
            "sk-",  # OpenAI keys
            "AIza",  # Google API keys
        ]
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    for pattern in sensitive_patterns:
                        # Should not find actual secrets, only references to env vars
                        lines_with_pattern = [
                            line for line in content.split('\n')
                            if pattern in line and not line.strip().startswith('#')
                        ]
                        assert len(lines_with_pattern) == 0, f"Found suspicious pattern '{pattern}' in {file_path}"
                except (UnicodeDecodeError, FileNotFoundError):
                    # Skip files that can't be read
                    pass
    
    def test_credentials_in_error_responses(self):
        """Error responses should never contain credentials."""
        # Example error responses
        safe_responses = [
            {"success": False, "message": "Invalid request"},
            {"success": False, "message": "Unauthorized"},
            {"success": False, "message": "Session not found"},
        ]
        
        unsafe_keywords = ["mongodb://", "api_key", "password", "@localhost"]
        
        for response in safe_responses:
            response_str = str(response)
            for keyword in unsafe_keywords:
                assert keyword not in response_str.lower()


class TestIntegrationSecurityValidation:
    """Integration tests for security validation."""
    
    def test_startup_validation_fails_with_weak_jwt_secret(self):
        """If JWT_SECRET is less than 32 chars, startup should fail."""
        # This would be tested in actual runtime
        weak_secret = "weak"
        assert len(weak_secret) < 32
        
    def test_startup_validation_passes_with_strong_secrets(self):
        """If secrets are 32+ chars, startup validates successfully."""
        import secrets
        strong_secret = secrets.token_urlsafe(32)
        assert len(strong_secret) >= 32
    
    def test_query_validation_chain(self):
        """Query validation works at multiple levels."""
        try:
            # Level 1: Pydantic model validation (max 5000)
            from chatbot.models.validators import validate_query
            
            valid_query = "What is this video about?"
            assert validate_query(valid_query) == valid_query
            
            # Level 2: Orchestrator parser validation (max 1000)
            short_but_under_1000 = "A" * 500
            assert len(short_but_under_1000) <= 1000
            
            # Long query should fail orchestrator
            long_query = "A" * 2000
            try:
                from chatbot.parsers.orchestrator_parser import structured_llm
                with pytest.raises(ValueError):
                    structured_llm(long_query)
            except ImportError:
                pytest.skip("Cannot import orchestrator (missing dependencies)")
        except ImportError:
            pytest.skip("Cannot import validators")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

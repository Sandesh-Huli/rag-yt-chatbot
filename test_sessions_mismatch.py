"""
Test script to verify the ObjectId ↔ UUID mismatch hypothesis.

Run this after:
1. Starting MongoDB
2. Starting Express backend (port 4000)
3. Starting FastAPI backend (port 8000)
4. Creating a test user (see instructions below)

Usage:
    python test_sessions_mismatch.py
"""

import requests
import json
import re
import uuid as uuid_module
from typing import Optional, Tuple

# Configuration
EXPRESS_URL = "http://localhost:4000"
FASTAPI_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def is_mongodb_objectid(value: str) -> bool:
    """Check if string is MongoDB ObjectId format (24 hex chars)"""
    pattern = r'^[a-f0-9]{24}$'
    return bool(re.match(pattern, value.lower()))

def is_uuid(value: str) -> bool:
    """Check if string is UUID format"""
    try:
        uuid_module.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False

def extract_user_id_from_token(token: str) -> Optional[str]:
    """Decode JWT token (without verification) to extract user_id"""
    import base64
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # Add padding if necessary
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        
        decoded = base64.urlsafe_b64decode(payload)
        payload_dict = json.loads(decoded)
        return payload_dict.get('id')
    except Exception as e:
        print_error(f"Failed to decode token: {e}")
        return None

def test_1_register_new_user() -> Tuple[str, str, str]:
    """Test 1: Register a new user and extract credentials"""
    print_header("TEST 1: Register New User")
    
    user_data = {
        "username": f"testuser_{uuid_module.uuid4().hex[:8]}",
        "email": f"test_{uuid_module.uuid4().hex[:8]}@example.com",
        "password": "TestPass123!@#"
    }
    
    print(f"Registering user: {user_data['email']}")
    
    try:
        response = requests.post(f"{EXPRESS_URL}/user/register", json=user_data)
        
        if response.status_code != 200:
            print_error(f"Registration failed with status {response.status_code}")
            print(json.dumps(response.json(), indent=2))
            return None, None, None
        
        result = response.json()
        if not result.get('success'):
            print_error(f"Registration returned success=false: {result}")
            return None, None, None
        
        token = result.get('token')
        username = result.get('user', {}).get('username')
        
        print_success(f"Registration successful!")
        print(f"  Username: {username}")
        print(f"  Token: {token[:50]}...")
        
        # Extract user_id from token
        user_id = extract_user_id_from_token(token)
        if not user_id:
            print_error("Could not extract user_id from token")
            return None, None, None
        
        print(f"  Extracted user_id from JWT: {user_id}")
        
        # Check format
        if is_mongodb_objectid(user_id):
            print_success(f"  ✓ user_id is MongoDB ObjectId format (24 hex chars)")
        else:
            print_warning(f"  ? user_id is NOT MongoDB ObjectId format")
        
        if is_uuid(user_id):
            print_warning(f"  ? user_id is also valid UUID format (unlikely for ObjectId)")
        
        return token, user_id, username
        
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None, None, None

def test_2_call_express_sessions_endpoint(token: str, user_id: str):
    """Test 2: Call Express sessions endpoint"""
    print_header("TEST 2: Call Express GET /chats/sessions (Should return sessions)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Calling: GET {EXPRESS_URL}/chats/sessions")
    print(f"  Header: Authorization: Bearer {token[:50]}...")
    
    try:
        response = requests.get(f"{EXPRESS_URL}/chats/sessions", headers=headers)
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Got 200 response")
            print(f"  Sessions returned: {len(data) if isinstance(data, list) else 'N/A'}")
            if isinstance(data, list):
                print(f"  Data: {json.dumps(data, indent=2)[:200]}...")
            return True
        else:
            error_data = response.json()
            print_error(f"Got {response.status_code} response")
            print(f"  Error: {json.dumps(error_data, indent=2)}")
            
            # Check if it's the UUID validation error
            if 'detail' in error_data:
                detail = error_data['detail']
                if 'UUID' in detail or 'uuid' in detail:
                    print_error("  → This is the UUID validation error!")
                    print_error("  → Express is sending ObjectId, FastAPI expects UUID")
            return False
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False

def test_3_call_fastapi_with_objectid(user_id: str):
    """Test 3: Call FastAPI directly with ObjectId (should fail)"""
    print_header("TEST 3: Call FastAPI with ObjectId (Expected to fail)")
    
    url = f"{FASTAPI_URL}/chats/sessions"
    params = {"user_id": user_id}
    
    print(f"Calling: GET {url}")
    print(f"  Params: user_id={user_id} (MongoDB ObjectId format)")
    print(f"  Format check: is_objectid={is_mongodb_objectid(user_id)}, is_uuid={is_uuid(user_id)}")
    
    try:
        response = requests.get(url, params=params)
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 422:
            error_data = response.json()
            print_error(f"Got 422 Unprocessable Entity (EXPECTED)")
            print(f"  Error: {json.dumps(error_data, indent=2)}")
            print_error("  → This confirms the UUID validation error!")
            return False
        elif response.status_code == 200:
            data = response.json()
            print_success(f"Got 200 response (unexpected - validation seems to pass?)")
            print(f"  Data: {json.dumps(data, indent=2)}")
            return True
        else:
            print_warning(f"Got unexpected {response.status_code} response")
            print(json.dumps(response.json(), indent=2))
            return False
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False

def test_4_call_fastapi_with_uuid(user_id: str):
    """Test 4: Call FastAPI with a valid UUID (should pass validation)"""
    print_header("TEST 4: Call FastAPI with Valid UUID (Should pass validation)")
    
    # Convert ObjectId to UUID using namespace
    # (Note: This won't match actual sessions since DB stores ObjectId)
    test_uuid = str(uuid_module.uuid5(
        uuid_module.NAMESPACE_DNS,
        user_id
    ))
    
    url = f"{FASTAPI_URL}/chats/sessions"
    params = {"user_id": test_uuid}
    
    print(f"Calling: GET {url}")
    print(f"  Params: user_id={test_uuid} (Valid UUID format)")
    print(f"  Format check: is_objectid={is_mongodb_objectid(test_uuid)}, is_uuid={is_uuid(test_uuid)}")
    
    try:
        response = requests.get(url, params=params)
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Got 200 response (validation passed)")
            print(f"  Sessions returned: {len(data) if isinstance(data, list) else 'N/A'}")
            if len(data) == 0:
                print_warning("  → 0 sessions found (expected - DB stores ObjectId, not UUID)")
            print(f"  Data: {json.dumps(data, indent=2)[:300]}...")
            return True
        elif response.status_code == 422:
            error_data = response.json()
            print_error(f"Got 422 error (unexpected - UUID should pass validation)")
            print(f"  Error: {json.dumps(error_data, indent=2)}")
            return False
        else:
            print_warning(f"Got unexpected {response.status_code} response")
            print(json.dumps(response.json(), indent=2))
            return False
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False

def test_5_explain_mismatch():
    """Test 5: Summary explanation"""
    print_header("TEST 5: Summary & Root Cause")
    
    print("""
The Root Cause Analysis:

1. USER REGISTRATION:
   - Express/MongoDB creates user with ObjectId: "507f1f77bcf86cd799439011"
   - JWT encodes this ObjectId as string
   
2. EXPRESS SENDS TO FASTAPI:
   - axios.get(/chats/sessions?user_id=507f1f77bcf86cd799439011)
   
3. FASTAPI RECEIVES:
   - Runs: uuid.UUID("507f1f77bcf86cd799439011")
   - ❌ FAILS - Not valid UUID format
   
4. RESULT:
   - FastAPI returns: 422 Unprocessable Entity
   - Error message: "user_id must be a valid UUID (got: 507f1f77bcf86cd799439011)"
   - Database is never queried (validation fails first)

THE FIX:
   Update chatbot/models/validators.py to accept BOTH:
   - MongoDB ObjectId format (24 hex chars)
   - UUID format (standard with dashes)
   
   Or migrate to UUID-only in Express/MongoDB layer.
""")

def main():
    print_header("Chat Sessions Mismatch Test Suite")
    
    print("""
This test suite will:
1. Register a new test user
2. Call Express endpoint to fetch sessions (currently fails)
3. Call FastAPI directly with ObjectId (confirm failure)
4. Call FastAPI with UUID (confirm it passes validation)
5. Explain the root cause

Expected Outcome:
- Test 1: ✅ Registration succeeds, extracts ObjectId
- Test 2: ❌ Express call fails with 422 (UUID validation error)
- Test 3: ❌ FastAPI call fails with 422 (UUID validation error)
- Test 4: ✅ FastAPI call succeeds with validation, but gets 0 sessions
- Test 5: Explanation of the mismatch
    """)
    
    input("\nPress Enter to start tests...")
    
    # Test 1: Register user
    token, user_id, username = test_1_register_new_user()
    if not token or not user_id:
        print_error("Test 1 failed - cannot proceed")
        return
    
    # Test 2: Call Express sessions endpoint
    test_2_call_express_sessions_endpoint(token, user_id)
    
    # Test 3: Call FastAPI with ObjectId
    test_3_call_fastapi_with_objectid(user_id)
    
    # Test 4: Call FastAPI with UUID
    test_4_call_fastapi_with_uuid(user_id)
    
    # Test 5: Summary
    test_5_explain_mismatch()
    
    print_header("All Tests Complete")
    print("""
RECOMMENDATION:
Deploy the fix to chatbot/models/validators.py to accept ObjectId format.
See CHAT_SESSIONS_ANALYSIS.md for detailed solution.
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

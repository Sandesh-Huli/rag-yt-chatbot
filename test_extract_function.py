#!/usr/bin/env python
"""Quick test for extract_response_content utility function"""

try:
    from chatbot.services.yt_agent_graph import extract_response_content
    print("✅ Function imported successfully")
    
    # Test 1: String input
    result1 = extract_response_content("test string")
    assert result1 == "test string"
    print("✅ Test 1 PASSED: String extraction")
    
    # Test 2: Object with content attribute
    class MockResponse:
        def __init__(self):
            self.content = "object content"
    
    result2 = extract_response_content(MockResponse())
    assert result2 == "object content"
    print("✅ Test 2 PASSED: Object with .content attribute")
    
    # Test 3: Integer converted to string
    result3 = extract_response_content(123)
    assert result3 == "123"
    print("✅ Test 3 PASSED: Non-string to string conversion")
    
    print("\n✅✅✅ All tests PASSED! extract_response_content is working correctly.")
    
except Exception as e:
    print(f"❌ Test FAILED: {e}")
    import traceback
    traceback.print_exc()

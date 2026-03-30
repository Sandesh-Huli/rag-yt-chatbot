#!/usr/bin/env python
"""Test error handling in critical paths"""

import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.DEBUG)

try:
    # Test 1: Web search error handling
    print("Test 1: Web search error handling")
    from chatbot.tools.web_search import web_search
    
    # Empty query should still return something (not crash)
    result = web_search("")
    assert isinstance(result, str), "Web search should return string"
    print("✅ Test 1 PASSED: Web search returns string even on issues")
    
    # Test 2: RAG error handling for retrieve_transcript
    print("\nTest 2: RAG retrieve_transcript error handling")
    from chatbot.services.rag_service import RAG
    
    rag = RAG()
    # Should not crash even with empty index
    results = rag.retrieve_transcript("test query")
    assert isinstance(results, list), "retrieve_transcript should return list"
    print("✅ Test 2 PASSED: RAG retrieve_transcript handles empty index gracefully")
    
    # Test 3: Verify error paths don't crash
    print("\nTest 3: Error handling in nodes")
    from chatbot.services.yt_agent_graph import extract_response_content
    
    # Test extract_response_content with various inputs
    assert extract_response_content("test") == "test"
    assert extract_response_content(123) == "123"
    
    class MockObj:
        content = "mock"
    
    assert extract_response_content(MockObj()) == "mock"
    print("✅ Test 3 PASSED: Response content extraction handles all types")
    
    print("\n✅✅✅ All error handling tests PASSED!")
    
except Exception as e:
    print(f"❌ Test FAILED: {e}")
    import traceback
    traceback.print_exc()

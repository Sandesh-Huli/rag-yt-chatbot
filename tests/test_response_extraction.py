"""Test script for extract_response_content utility function"""
from chatbot.services.yt_agent_graph import extract_response_content
from langchain_core.messages import HumanMessage

# Test 1: Extract from LLM message object
msg = HumanMessage(content='test content')
result1 = extract_response_content(msg)
print(f"Test 1 - Extract from object: {result1}")
assert result1 == "test content", f"Expected 'test content', got {result1}"

# Test 2: Extract from string
result2 = extract_response_content("string test")
print(f"Test 2 - Extract from string: {result2}")
assert result2 == "string test", f"Expected 'string test', got {result2}"

# Test 3: Extract from custom object with content attribute
class MockResponse:
    content = "mock content"

result3 = extract_response_content(MockResponse())
print(f"Test 3 - Extract from custom object: {result3}")
assert result3 == "mock content", f"Expected 'mock content', got {result3}"

print("✅ All utility function tests passed!")

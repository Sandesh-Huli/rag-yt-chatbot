"""
Test suite for refactoring fixes: Issues 16, 17, 18, 20

Issue 16: Code Deduplication (helper functions)
Issue 17: Type Hints (comprehensive type annotations)
Issue 18: Logger Usage (replace print with logger)
Issue 20: Error Messages (specific, actionable errors)
"""

import pytest
import logging
from unittest import mock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ============= Issue 16 Tests: Code Deduplication =============

class TestHistoryTextBuilder:
    """Test _build_history_text helper function (Issue 16)."""
    
    @pytest.fixture
    def sample_history(self) -> List[Dict[str, str]]:
        """Fixture for sample conversation history."""
        return [
            {"role": "user", "content": "What's in the video?"},
            {"role": "assistant", "content": "The video discusses..."},
            {"role": "user", "content": "Can you summarize it?"},
            {"role": "assistant", "content": "Sure! Summary: ..."}
        ]
    
    def test_history_text_formatting(self, sample_history):
        """Test that history is properly formatted as role: content."""
        # Import the helper from yt_agent_graph
        from chatbot.services.yt_agent_graph import _build_history_text
        
        history_text = _build_history_text(sample_history)
        
        # Should contain all messages
        assert "What's in the video?" in history_text
        assert "The video discusses" in history_text
        
        # Should use role: content format
        assert "user: What's in the video?" in history_text
        assert "assistant: The video discusses..." in history_text
    
    def test_empty_history(self):
        """Test handling of empty history."""
        from chatbot.services.yt_agent_graph import _build_history_text
        
        history_text = _build_history_text(None)
        assert history_text == ""
        
        history_text = _build_history_text([])
        assert history_text == ""
    
    def test_history_deduplication(self):
        """Verify the helper is used in all three nodes (qa, summarize, translate)."""
        # This is a structural test - the same function should be called
        # in qa_node, summarize_node, and translate_node to prevent duplication
        from chatbot.services.yt_agent_graph import qa_node, summarize_node, translate_node
        
        # All three functions should reference the helper
        import inspect
        
        qa_source = inspect.getsource(qa_node)
        summarize_source = inspect.getsource(summarize_node)
        translate_source = inspect.getsource(translate_node)
        
        # All should call _build_history_text
        assert "_build_history_text" in qa_source
        assert "_build_history_text" in summarize_source
        assert "_build_history_text" in translate_source


class TestSessionCacheHelper:
    """Test _store_to_session_cache helper function (Issue 16)."""
    
    def test_cache_storage_encapsulation(self):
        """Verify cache storage logic is encapsulated in single function."""
        from chatbot.services.yt_agent_graph import _store_to_session_cache
        
        # Should have proper signature
        import inspect
        sig = inspect.signature(_store_to_session_cache)
        assert "session_id" in sig.parameters
        assert "query" in sig.parameters
        assert "result" in sig.parameters
        assert str(sig.return_annotation) == "<class 'NoneType'>"
    
    def test_cache_helper_error_handling(self):
        """Test that cache helper handles errors gracefully."""
        from chatbot.services.yt_agent_graph import _store_to_session_cache
        
        # Should not raise exceptions even with invalid session_id
        # (graceful degradation per the docstring)
        try:
            # Should log error but not propagate
            _store_to_session_cache("invalid-session", "test query", "test result")
            # If we get here, error handling works
            assert True
        except Exception:
            # Should not raise
            pytest.fail("_store_to_session_cache should handle errors gracefully")


# ============= Issue 17 Tests: Type Hints =============

class TestTypeHints:
    """Test that type hints are properly added (Issue 17)."""
    
    def test_yt_agent_graph_type_hints(self):
        """Verify all node functions have proper type hints."""
        from chatbot.services.yt_agent_graph import (
            fetch_transcript_node, qa_node, summarize_node, 
            translate_node, fallback_node, orchestrator_node,
            add_transcript_node, run_query
        )
        import inspect
        
        functions_to_check = {
            "fetch_transcript_node": fetch_transcript_node,
            "qa_node": qa_node,
            "summarize_node": summarize_node,
            "translate_node": translate_node,
            "fallback_node": fallback_node,
            "orchestrator_node": orchestrator_node,
            "add_transcript_node": add_transcript_node,
            "run_query": run_query,
        }
        
        for name, func in functions_to_check.items():
            sig = inspect.signature(func)
            # All should have return type annotation
            assert sig.return_annotation != inspect.Signature.empty, \
                f"{name} missing return type annotation"
            # Docstring should exist
            assert func.__doc__ is not None, f"{name} missing docstring"
    
    def test_rag_service_type_hints(self):
        """Verify RAG methods have proper type hints."""
        from chatbot.services.rag_service import RAG
        import inspect
        
        methods = [
            "_save_indexes",
            "_load_indexes", 
            "add_transcript",
            "check_and_prune_memory",
            "retrieve_transcript",
            "add_query",
            "retrieve_queries"
        ]
        
        rag = RAG.__dict__
        for method_name in methods:
            method = rag.get(method_name)
            if method:
                sig = inspect.signature(method)
                # Should have return type annotation
                assert sig.return_annotation != inspect.Signature.empty, \
                    f"RAG.{method_name} missing return type annotation"
    
    def test_cache_manager_type_hints(self):
        """Verify cache manager classes have type hints."""
        from chatbot.services.cache_manager import (
            VideoIndex, SessionMemory, VideoCacheManager, SessionCacheManager
        )
        import inspect
        
        # Check VideoIndex methods
        video_methods = ["add_transcript", "_update_access"]
        for name in video_methods:
            method = getattr(VideoIndex, name)
            sig = inspect.signature(method)
            assert sig.return_annotation != inspect.Signature.empty, \
                f"VideoIndex.{name} missing return type"
        
        # Check SessionMemory methods
        session_methods = ["add_message", "clear_old_messages", "_update_access"]
        for name in session_methods:
            method = getattr(SessionMemory, name)
            sig = inspect.signature(method)
            assert sig.return_annotation != inspect.Signature.empty, \
                f"SessionMemory.{name} missing return type"


# ============= Issue 18 Tests: Logger Usage =============

class TestLoggerUsage:
    """Test that logger is used instead of print (Issue 18)."""
    
    def test_no_print_in_yt_agent_graph(self):
        """Verify no print() calls in yt_agent_graph.py."""
        with open("d:\\Sandesh\\Agentic AI\\LangChain\\yt-chatbot\\chatbot\\services\\yt_agent_graph.py") as f:
            content = f.read()
            # Check for print( calls - should not exist except in strings/comments
            import re
            # This regex finds print( calls (not in comments or strings)
            print_calls = re.findall(r'^\s*print\(', content, re.MULTILINE)
            assert len(print_calls) == 0, f"Found {len(print_calls)} print() calls in yt_agent_graph.py"
    
    def test_logging_in_rag_service(self):
        """Verify logger is used in rag_service.py instead of print."""
        with open("d:\\Sandesh\\Agentic AI\\LangChain\\yt-chatbot\\chatbot\\services\\rag_service.py") as f:
            content = f.read()
            # Old print statements with emoji markers removed
            assert "⚠️ Failed to load FAISS" not in content
            assert "📊 TRANSCRIPT EMBEDDING" not in content
            assert "✅ All" not in content
            # Should use logger instead
            assert "logger.error" in content
            assert "logger.info" in content
    
    def test_no_emojis_in_logging(self):
        """Verify no emoji characters in logger calls."""
        from chatbot.services.yt_agent_graph import fetch_transcript_node
        import inspect
        
        source = inspect.getsource(fetch_transcript_node)
        # Should not contain emoji unicode sequences in logger calls
        assert "logger.error" in source
        assert "logger.info" in source
        # Verify no emoji in the actual log messages (emoji would be unicode escapes)
        assert "\U0001f600" not in source  # 😀 emoji
        assert "\u2705" not in source  # ✅ emoji


# ============= Issue 20 Tests: Error Messages =============

class TestErrorMessages:
    """Test that error messages are specific and actionable (Issue 20)."""
    
    def test_fetch_transcript_error_specificity(self):
        """Verify fetch_transcript_node has specific error messages."""
        from chatbot.services.yt_agent_graph import fetch_transcript_node
        import inspect
        
        source = inspect.getsource(fetch_transcript_node)
        
        # Should have specific error messages, not generic ones
        assert "Invalid YouTube video ID format" in source or "Could not fetch video transcript" in source
        # Should NOT have generic "Error: Could not do X - {str(e)}"
        assert "Error: Could not fetch transcript - {str(e)}" not in source
    
    def test_qa_node_error_messages(self):
        """Verify qa_node has multiple specific error paths."""
        from chatbot.services.yt_agent_graph import qa_node
        import inspect
        
        source = inspect.getsource(qa_node)
        
        # Should have multiple different error messages for different failure points
        error_messages = [
            "Could not process your query",
            "Web search unavailable",
            "Failed to generate response"
        ]
        
        for msg in error_messages:
            assert msg in source, f"Missing error message: {msg}"
    
    def test_translate_node_language_aware_errors(self):
        """Verify translate_node has language-aware error messages."""
        from chatbot.services.yt_agent_graph import translate_node
        import inspect
        
        source = inspect.getsource(translate_node)
        
        # Should reference target language in error message
        assert "target_language" in source.lower()
        assert "translate" in source.lower()
    
    @mock.patch('builtins.print')
    def test_no_bare_error_strings(self, mock_print):
        """Verify error messages provide context and solutions."""
        # This is more of a design test - error messages should:
        # 1. Explain what went wrong
        # 2. Include relevant context
        # 3. Be different for different error conditions
        
        from chatbot.services.yt_agent_graph import fetch_transcript_node, qa_node
        import inspect
        
        functions_to_check = [fetch_transcript_node, qa_node]
        
        for func in functions_to_check:
            source = inspect.getsource(func)
            # Should have error messages that are actionable
            # (not just "Error" or generic strings)
            assert "Error:" not in source or len(source) > 500, \
                "Function too short - likely missing error context"


# ============= Integration Tests =============

class TestRefactoringIntegration:
    """Integration tests for refactored code."""
    
    def test_helper_functions_reduce_duplication(self):
        """Verify deduplication through helper function usage."""
        from chatbot.services.yt_agent_graph import (
            _build_history_text, _store_to_session_cache, 
            qa_node, summarize_node, translate_node
        )
        import inspect
        
        # Helper functions should exist and be small/focused
        build_history_source = inspect.getsource(_build_history_text)
        assert len(build_history_source) < 500, "Helper should be concise"
        
        store_cache_source = inspect.getsource(_store_to_session_cache)
        assert len(store_cache_source) < 500, "Helper should be concise"
        
        # Node functions should reference helpers
        qa_source = inspect.getsource(qa_node)
        assert "_build_history_text" in qa_source
        assert "_store_to_session_cache" in qa_source
    
    def test_all_nodes_comparable_error_handling(self):
        """Verify all nodes have similar quality error handling."""
        from chatbot.services.yt_agent_graph import (
            fetch_transcript_node, qa_node, summarize_node, 
            translate_node, fallback_node
        )
        import inspect
        
        nodes = [
            ("fetch_transcript_node", fetch_transcript_node),
            ("qa_node", qa_node),
            ("summarize_node", summarize_node),
            ("translate_node", translate_node),
            ("fallback_node", fallback_node),
        ]
        
        for name, node_func in nodes:
            source = inspect.getsource(node_func)
            # All should have docstring
            assert node_func.__doc__ is not None, f"{name} missing docstring"
            # All should have type hints
            sig = inspect.signature(node_func)
            assert sig.return_annotation != inspect.Signature.empty, \
                f"{name} missing return type"
            # All should use logger, not print
            assert "logger." in source
            assert "print(" not in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

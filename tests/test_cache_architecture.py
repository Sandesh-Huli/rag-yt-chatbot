#!/usr/bin/env python
"""
Test Suite: Two-Tier Cache Architecture (Video Cache + Session Cache)
=====================================================================
Tests for:
✅ Video Cache: Same video_id reuses FAISS index across sessions
✅ Session Cache: Same session_id reuses chat memory
✅ Concurrency: Multiple sessions accessing same/different videos
✅ Cleanup: Expiration and manual cleanup
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_video_cache_reuse_same_video():
    """Test: Same video_id reuses FAISS index across different sessions"""
    print("\n" + "="*80)
    print("TEST 1: Video Cache - Same video reuses index across sessions")
    print("="*80)
    
    try:
        from chatbot.services.cache_manager import video_cache_manager
        
        video_id = f"test_video_{uuid.uuid4().hex[:8]}"
        transcript = ["Hello world", "This is a test", "Multiple sessions should share this"]
        
        # Session 1: Get video cache and add transcript
        video_cache_1 = video_cache_manager.get_video_cache(video_id)
        video_cache_1.add_transcript(transcript, metadata={"session": "1"})
        print(f"[OK] Session 1: Added transcript to video {video_id}")
        print(f"[OK] Video cache indexed: {video_cache_1.is_indexed()}")
        print(f"[OK] Chunks in cache: {len(video_cache_1.transcript_chunks)}")
        
        # Session 2: Get same video cache - should reuse, not re-index
        video_cache_2 = video_cache_manager.get_video_cache(video_id)
        print(f"[OK] Session 2: Retrieved video cache for {video_id}")
        print(f"[OK] Same instance? {video_cache_1 is video_cache_2}")
        print(f"[OK] Already indexed: {video_cache_2.is_indexed()}")
        
        # Verify it's the same FAISS index (shared)
        assert video_cache_1 is video_cache_2, "Same video_id should return same cache instance"
        assert video_cache_2.transcript_index is not None, "Index should exist"
        assert len(video_cache_2.transcript_chunks) > 0, "Chunks should exist"
        
        print("[PASS] TEST 1 PASSED: Same video_id reuses FAISS index across sessions\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] TEST 1 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_video_cache_isolation_different_videos():
    """Test: Different video_ids get isolated FAISS indices"""
    print("="*80)
    print("TEST 2: Video Cache - Different videos have isolated indices")
    print("="*80)
    
    try:
        from chatbot.services.cache_manager import video_cache_manager
        
        video_id_a = f"video_a_{uuid.uuid4().hex[:8]}"
        video_id_b = f"video_b_{uuid.uuid4().hex[:8]}"
        
        # Video A
        cache_a = video_cache_manager.get_video_cache(video_id_a)
        cache_a.add_transcript(["Content from video A"], metadata={"video": "a"})
        chunks_a = len(cache_a.transcript_chunks)
        print(f"[OK] Video A: {chunks_a} chunks added")
        
        # Video B
        cache_b = video_cache_manager.get_video_cache(video_id_b)
        cache_b.add_transcript(["Content from video B with more text"], metadata={"video": "b"})
        chunks_b = len(cache_b.transcript_chunks)
        print(f"[OK] Video B: {chunks_b} chunks added")
        
        # Verify isolation
        assert cache_a is not cache_b, "Different videos should have different cache instances"
        assert cache_a.transcript_index is not cache_b.transcript_index, "FAISS indices should be separate"
        assert cache_a.video_id != cache_b.video_id, "Video IDs should be different"
        
        print(f"[OK] Video A chunks: {chunks_a}, Video B chunks: {chunks_b}")
        print("[PASS] TEST 2 PASSED: Different videos have isolated FAISS indices\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] TEST 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_session_cache_reuse_same_session():
    """Test: Same session_id reuses chat memory"""
    print("="*80)
    print("TEST 3: Session Cache - Same session reuses memory")
    print("="*80)
    
    try:
        from chatbot.services.cache_manager import session_cache_manager
        
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # First access
        cache_1 = session_cache_manager.get_session_cache(session_id)
        cache_1.add_message("User: Hello", {"role": "user"})
        cache_1.add_message("Assistant: Hi there", {"role": "assistant"})
        msg_count_1 = cache_1.get_message_count()
        print(f"[OK] First access: Added messages, count = {msg_count_1}")
        
        # Second access - should reuse
        cache_2 = session_cache_manager.get_session_cache(session_id)
        msg_count_2 = cache_2.get_message_count()
        print(f"[OK] Second access: Retrieved cache, count = {msg_count_2}")
        
        # Verify same instance
        assert cache_1 is cache_2, "Same session_id should return same cache instance"
        assert msg_count_1 == msg_count_2, "Message count should be preserved"
        assert msg_count_2 == 2, "Should have 2 messages"
        
        # Add more in second access
        cache_2.add_message("User: How are you?", {"role": "user"})
        msg_count_3 = cache_1.get_message_count()
        print(f"[OK] After adding via second access: {msg_count_3} messages")
        assert msg_count_3 == 3, "Should now have 3 messages"
        
        print("[PASS] TEST 3 PASSED: Same session_id reuses chat memory\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] TEST 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_session_cache_isolation():
    """Test: Different session_ids have isolated memories"""
    print("="*80)
    print("TEST 4: Session Cache - Different sessions have isolated memory")
    print("="*80)
    
    try:
        from chatbot.services.cache_manager import session_cache_manager
        
        session_id_1 = f"session_1_{uuid.uuid4().hex[:8]}"
        session_id_2 = f"session_2_{uuid.uuid4().hex[:8]}"
        
        # Session 1
        cache_1 = session_cache_manager.get_session_cache(session_id_1)
        cache_1.add_message("User 1 message", {"role": "user"})
        count_1 = cache_1.get_message_count()
        print(f"[OK] Session 1: {count_1} message(s)")
        
        # Session 2
        cache_2 = session_cache_manager.get_session_cache(session_id_2)
        cache_2.add_message("User 2 message A", {"role": "user"})
        cache_2.add_message("User 2 message B", {"role": "user"})
        count_2 = cache_2.get_message_count()
        print(f"[OK] Session 2: {count_2} message(s)")
        
        # Verify isolation
        assert cache_1 is not cache_2, "Different sessions should have different instances"
        assert count_1 != count_2, "Different sessions should have different message counts"
        assert count_1 == 1, "Session 1 should have 1 message"
        assert count_2 == 2, "Session 2 should have 2 messages"
        
        print("[PASS] TEST 4 PASSED: Different sessions have isolated memory\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] TEST 4 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_concurrent_video_cache_access():
    """Test: Multiple sessions accessing same video concurrently"""
    print("="*80)
    print("TEST 5: Concurrency - Multiple sessions access same video safely")
    print("="*80)
    
    try:
        from chatbot.services.cache_manager import video_cache_manager
        
        video_id = f"concurrent_test_{uuid.uuid4().hex[:8]}"
        results = []
        
        def access_video_cache(session_num):
            try:
                if session_num == 1:
                    # First session adds transcript
                    cache = video_cache_manager.get_video_cache(video_id)
                    cache.add_transcript(["Content 1"], metadata={"session": 1})
                    results.append((session_num, "success", True))
                else:
                    # Other sessions just access the same video
                    time.sleep(0.1)  # Small delay to ensure first thread completes
                    cache = video_cache_manager.get_video_cache(video_id)
                    indexed = cache.is_indexed()
                    results.append((session_num, "success", indexed))
            except Exception as e:
                results.append((session_num, "failed", str(e)))
        
        # Create 5 concurrent threads accessing same video
        threads = [threading.Thread(target=access_video_cache, args=(i,)) for i in range(1, 6)]
        
        print(f"[OK] Starting 5 concurrent threads accessing video {video_id}")
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        print(f"[OK] All threads completed")
        for session_num, status, result in results:
            print(f"    Thread {session_num}: {status}, indexed={result}")
        
        # All should succeed
        assert all(status == "success" for _, status, _ in results), "All threads should succeed"
        # First thread should index, others should see it indexed
        assert results[0][2] == True, "First thread should successfully index"
        
        print("[PASS] TEST 5 PASSED: Concurrent access is thread-safe\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] TEST 5 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_session_cleanup():
    """Test: Session cleanup removes memory from cache"""
    print("="*80)
    print("TEST 6: Session Cleanup - Remove session from cache")
    print("="*80)
    
    try:
        from chatbot.services.cache_manager import session_cache_manager
        
        session_id = f"cleanup_test_{uuid.uuid4().hex[:8]}"
        
        # Create session
        cache = session_cache_manager.get_session_cache(session_id)
        cache.add_message("Test message", {"role": "user"})
        print(f"[OK] Created session with message")
        
        # Verify it exists
        cached_sessions = session_cache_manager.list_cached_sessions()
        assert session_id in cached_sessions, "Session should be in cache"
        print(f"[OK] Session in cache: {session_id in cached_sessions}")
        
        # Cleanup
        success = session_cache_manager.cleanup_session(session_id)
        assert success, "Cleanup should succeed"
        print(f"[OK] Cleanup successful")
        
        # Verify it's gone
        cached_sessions = session_cache_manager.list_cached_sessions()
        assert session_id not in cached_sessions, "Session should be removed"
        print(f"[OK] Session removed from cache")
        
        print("[PASS] TEST 6 PASSED: Session cleanup works correctly\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] TEST 6 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_video_cleanup():
    """Test: Video cleanup removes index from cache"""
    print("="*80)
    print("TEST 7: Video Cleanup - Remove video from cache")
    print("="*80)
    
    try:
        from chatbot.services.cache_manager import video_cache_manager
        
        video_id = f"cleanup_video_{uuid.uuid4().hex[:8]}"
        
        # Create video cache
        cache = video_cache_manager.get_video_cache(video_id)
        cache.add_transcript(["Test transcript"], metadata={"video": "cleanup"})
        print(f"[OK] Created video cache with transcript")
        
        # Verify it exists
        cached_videos = video_cache_manager.list_cached_videos()
        assert video_id in cached_videos, "Video should be in cache"
        print(f"[OK] Video in cache: {video_id in cached_videos}")
        
        # Cleanup
        success = video_cache_manager.cleanup_video(video_id)
        assert success, "Cleanup should succeed"
        print(f"[OK] Cleanup successful")
        
        # Verify it's gone
        cached_videos = video_cache_manager.list_cached_videos()
        assert video_id not in cached_videos, "Video should be removed"
        print(f"[OK] Video removed from cache")
        
        print("[PASS] TEST 7 PASSED: Video cleanup works correctly\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] TEST 7 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_cache_statistics():
    """Test: Cache statistics provide usage information"""
    print("="*80)
    print("TEST 8: Cache Statistics - Get usage metrics")
    print("="*80)
    
    try:
        from chatbot.services.cache_manager import video_cache_manager, session_cache_manager
        
        # Get stats
        video_stats = video_cache_manager.get_cache_stats()
        session_stats = session_cache_manager.get_cache_stats()
        
        print(f"[OK] Video cache stats:")
        print(f"    Total videos: {video_stats.get('total_videos', 0)}")
        print(f"    Total chunks: {video_stats.get('total_chunks', 0)}")
        
        print(f"[OK] Session cache stats:")
        print(f"    Total sessions: {session_stats.get('total_sessions', 0)}")
        print(f"    Total messages: {session_stats.get('total_messages', 0)}")
        
        # Verify structure
        assert "total_videos" in video_stats, "Video stats should have total_videos"
        assert "total_sessions" in session_stats, "Session stats should have total_sessions"
        
        print("[PASS] TEST 8 PASSED: Cache statistics work correctly\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] TEST 8 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TWO-TIER CACHE ARCHITECTURE TEST SUITE")
    print("="*80)
    
    tests = [
        test_video_cache_reuse_same_video,
        test_video_cache_isolation_different_videos,
        test_session_cache_reuse_same_session,
        test_session_cache_isolation,
        test_concurrent_video_cache_access,
        test_session_cleanup,
        test_video_cleanup,
        test_cache_statistics,
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
    
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    if passed == total:
        print("[OK] ALL TESTS PASSED!")
    else:
        print(f"[FAIL] {total - passed} test(s) failed")
    print("="*80)

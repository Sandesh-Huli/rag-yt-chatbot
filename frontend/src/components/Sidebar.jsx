import { useContext, useEffect, useState } from 'react'
import plus from '../assets/plus.png'
import PrevChat from './PrevChat'
import { AppContext } from '../context/AppContext'
import { ChatContext } from '../context/ChatContext'
import { apiService } from '../services/api'

export default function Sidebar() {
    const { newChat, setNewChat, user } = useContext(AppContext);
    const { startNewChat, chatSessions, setChatSessions, saveCurrentChat, chatHistory, video_id, setActiveChatId, resumeChat, shouldRefetchSessions, setShouldRefetchSessions } = useContext(ChatContext);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchSessions = async () => {
        // Only fetch if user is logged in
        if (!user || !user.token) {
            setChatSessions([]);
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const res = await apiService.getChatSessions();
            // Normalize IDs (backend returns session_id)
            const sessions = (res.data || []).map(s => ({
                id: s.session_id || s.id,
                session_id: s.session_id || s.id,
                video_id: s.video_id,
                last_updated: s.last_updated,
                created_at: s.created_at,
                title: s.title || `Video: ${s.video_id.substring(0, 8)}...`
            }));
            setChatSessions(sessions);
        } catch (err) {
            console.error('Error fetching sessions:', err);
            setError(err.response?.data?.message || err.response?.data?.detail || 'Failed to load previous chats');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();
    }, [user]);

    // Refetch sessions when triggered
    useEffect(() => {
        if (shouldRefetchSessions) {
            fetchSessions();
            setShouldRefetchSessions(false);
        }
    }, [shouldRefetchSessions]);

    const [resumingChatId, setResumingChatId] = useState(null);

    const handlePrevChatClick = async (chatSession) => {
        const sessionId = chatSession.session_id || chatSession.id;
        setResumingChatId(sessionId);
        setActiveChatId(sessionId);
        try {
            if (resumeChat) {
                await resumeChat(chatSession);
            }
            setNewChat(false);
        } catch (err) {
            console.error('Error resuming chat:', err);
            setError('Failed to resume chat');
        } finally {
            setResumingChatId(null);
        }
    };

    const handleNewChatClick = () => {
        // Save current chat if there are messages
        if (chatHistory.length > 0 && video_id) {
            const title = `Chat - ${new Date().toLocaleDateString()}`;
            saveCurrentChat(title);
        }
        
        startNewChat();
        setNewChat(true);
    };

    return (
        <div className="fixed left-0 h-full w-64 bg-white shadow-lg flex flex-col p-4 z-40 overflow-y-auto">
            <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg mb-6 hover:bg-blue-700 transition-colors" onClick={handleNewChatClick}
            >
                <img src={plus} alt="new chat" className='h-5' />
                <span className="font-semibold">New Chat</span>
            </button>
            <div className="flex-1 space-y-4 overflow-y-auto">
                <h4 className="text-sm font-semibold text-gray-600 mb-2">Previous Chats</h4>
                {!user ? (
                    <p className="text-sm text-gray-500">Please login to see your chats</p>
                ) : loading ? (
                    <p className="text-sm text-gray-500">Loading chats...</p>
                ) : error ? (
                    <p className="text-sm text-red-600">{error}</p>
                ) : chatSessions.length > 0 ? (
                    chatSessions.map((chatSession) => {
                        const sessionId = chatSession.session_id || chatSession.id;
                        const isResuming = resumingChatId === sessionId;
                        return (
                            <div 
                                key={sessionId} 
                                onClick={() => !isResuming && handlePrevChatClick(chatSession)}
                                className={isResuming ? 'opacity-50 cursor-wait' : ''}
                            >
                                {isResuming ? (
                                    <div className="bg-gray-100 rounded-lg p-4 shadow">
                                        <div className="flex items-center justify-center">
                                            <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                                            <span className="ml-2 text-sm text-gray-600">Loading...</span>
                                        </div>
                                    </div>
                                ) : (
                                    <PrevChat chat={chatSession} />
                                )}
                            </div>
                        );
                    })
                ) : (
                    <p className="text-sm text-gray-500">No previous chats</p>
                )}
            </div>
        </div>
    )
}
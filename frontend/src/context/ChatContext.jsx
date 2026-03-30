import { createContext, useState } from "react";
import { apiService } from "../services/api";
export const ChatContext = createContext();
const ChatContextProvider = (props)=>{
    const [video_id,setVideoId] = useState('');
    const [chatHistory,setChatHistory]=useState([]);
    const [activeChatId,setActiveChatId] = useState('');
    const [chatSessions,setChatSessions] = useState([]);
    const [shouldRefetchSessions, setShouldRefetchSessions] = useState(false);
    //function to add new message
    const addMessage = (content,sender)=>{
        const newMessage = {
            content,
            sender,
            timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev,newMessage]);
    }
    //function to save current chat session
    const saveCurrentChat = (title) => {
        if (chatHistory.length > 0) {
            const chatSession = {
                id: Date.now().toString(),
                title: title || `Chat ${Date.now()}`,
                video_id,
                chatHistory: [...chatHistory],
                last_updated: new Date().toISOString()
            };
            setChatSessions(prev => [...prev, chatSession]);
            return chatSession.id;
        }
    };
    // Function to resume a chat session (hydrate from backend if needed)
    const resumeChat = async (chatSession) => {
        const sessionId = chatSession.session_id || chatSession.id;
        setActiveChatId(sessionId);
        try {
            const res = await apiService.getSession(sessionId);
            const data = res.data || {};
            setVideoId(data.video_id ?? chatSession.video_id ?? "");
            
            // Normalize backend messages to frontend format
            const messages = data.messages || data.chatHistory || chatSession.chatHistory || [];
            const normalizedHistory = messages.map(msg => ({
                content: msg.message || msg.content,
                sender: msg.role === 'user' ? 'user' : 'assistant',
                timestamp: msg.timestamp
            }));
            
            setChatHistory(normalizedHistory);
        } catch (err) {
            // Fallback to local data if API fails
            setVideoId(chatSession.video_id ?? "");
            setChatHistory(chatSession.chatHistory ?? []);
        }
    };

    // Function to start new chat
    const startNewChat = () => {
        setActiveChatId(null);
        setVideoId('');
        setChatHistory([]);
    };
    const value = {
        video_id,setVideoId,
        chatHistory,setChatHistory,
        addMessage,
        activeChatId,setActiveChatId,
        chatSessions,setChatSessions,
        saveCurrentChat,
        resumeChat,
        startNewChat,
        shouldRefetchSessions,
        setShouldRefetchSessions
    };
    return (
            <ChatContext.Provider value={value}>
                {props.children}
            </ChatContext.Provider>
    );
}
export default ChatContextProvider;
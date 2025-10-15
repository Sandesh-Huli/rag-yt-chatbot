import { createContext, useState } from "react";
export const ChatContext = createContext();
const ChatContextProvider = (props)=>{
    const [video_id,setVideoId] = useState('');
    const [chatHistory,setChatHistory]=useState([]);
    const addMessage = (content,sender)=>{
        const newMessage = {
            content,
            sender,
            timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev,newMessage]);
    }
    const value={
        video_id,setVideoId,
        chatHistory,setChatHistory,addMessage,
        
    };
    return (
            <ChatContext.Provider value={value}>
                {props.children}
            </ChatContext.Provider>
    );
}
export default ChatContextProvider;
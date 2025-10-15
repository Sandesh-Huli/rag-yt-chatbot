import { createContext, useState } from "react";
export const ChatContext = createContext();
const ChatContextProvider = (props)=>{
    const [video_id,setVideoId] = useState('');
    const [chatHistory,setChatHistory]=useState('');
    const value={
        video_id,setVideoId,
        chatHistory,setChatHistory,
    };
    return (
            <ChatContext.Provider value={value}>
                {props.children}
            </ChatContext.Provider>
    );
}
export default ChatContextProvider;
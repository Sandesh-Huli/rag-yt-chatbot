import { useContext } from "react"
import { AppContext } from "../context/AppContext"
import { ChatContext } from "../context/ChatContext"
export default function PrevChat({chat}) {
    const {setNewChat} = useContext(AppContext);
    const {resumeChat} = useContext(ChatContext);
    
    const handleChatClick = () => {
        resumeChat(chat);
        setNewChat(false); // Switch to FPromptBar
    };

    return (
        <div 
            className="bg-gray-100 rounded-lg p-4 shadow hover:bg-blue-50 transition-colors cursor-pointer"
            onClick={handleChatClick}
        >
            <h3 className="text-lg font-semibold text-gray-800 mb-1">{chat.title}</h3>
            <p className="text-xs text-gray-500 mb-1">Video ID: {chat.video_id}</p>
            <p className="text-sm text-gray-700 mb-1">
                {chat.chatHistory && chat.chatHistory.length > 0 
                    ? chat.chatHistory[chat.chatHistory.length - 1].content.substring(0, 50) + '...'
                    : 'No messages yet'
                }
            </p>
            <p className="text-xs text-gray-400">
                {new Date(chat.last_updated).toLocaleDateString()}
            </p>
        </div>
    );
}
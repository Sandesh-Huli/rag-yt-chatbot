import { useContext } from "react"
import { AppContext } from "../context/AppContext.jsx"
import { IPromptBar,FPromptBar } from "./PromptBar.jsx"
import { ChatContext } from "../context/ChatContext.jsx";
import Chat from "./Chat.jsx";
export default function Body(){
    const {newChat} = useContext(AppContext);
    const {chatHistory} = useContext(ChatContext);
    // return(
    //     <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
    //         <h3 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
    //             Enter a Youtube video URL to begin the discussion with AI
    //         </h3>
    //         <div className="w-full max-w-2xl">
    //             {newChat === true ? <IPromptBar /> : <FPromptBar />}
    //         </div>
    //     </div>
    // )
    return (
        <div className="flex flex-col h-full px-4 py-6">
            {newChat ? (
                // Initial state - show welcome message
                <div className="flex flex-col items-center justify-center min-h-[60vh]">
                    <h3 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
                        Enter a Youtube video URL to begin the discussion with AI
                    </h3>
                    <div className="w-full max-w-2xl">
                        <IPromptBar />
                    </div>
                </div>
            ) : (
                // Chat state - show chat history and input
                <div className="flex flex-col h-full max-w-4xl mx-auto w-full">
                    <div className="flex-1 mb-4">
                        <Chat />
                    </div>
                    <div className="w-full">
                        <FPromptBar />
                    </div>
                </div>
            )}
        </div>
    )
}
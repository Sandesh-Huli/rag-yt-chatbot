import { useContext } from "react"
import { AppContext } from "../context/AppContext.jsx"
import { IPromptBar,FPromptBar } from "./PromptBar.jsx"
export default function Body(){
    const {newChat} = useContext(AppContext);
    return(
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
            <h3 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
                Enter a Youtube video URL to begin the discussion with AI
            </h3>
            <div className="w-full max-w-2xl">
                {newChat === true ? <IPromptBar /> : <FPromptBar />}
            </div>
        </div>
    )
}
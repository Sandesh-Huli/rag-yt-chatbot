import {apiService} from '../services/api.js'
import extractYoutubeVideoId from '../services/fetchVideoid.js';
import { useContext, useState } from 'react'
import send from '../assets/send.png'
import { AppContext } from '../context/AppContext.jsx';
export const IPromptBar = () =>{
    const [url,setUrl]=useState("");
    const [loading,setLoading]=useState(false);
    const {video_id,setVideoId,newChat,setNewChat} = useContext(AppContext);
    const handleUrlChange = (e)=>{
        setUrl(e.target.value);
    }
    const handleLoadTranscripts = ()=>{
        const id = extractYoutubeVideoId(url);
        setVideoId(id);
        setNewChat(false);
    }
    return(
        <div className='flex items-center gap-3 bg-white p-4 rounded-lg shadow'>
            <textarea name="prompt" className="flex-1 resize-none border border-gray-400 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 transition" placeholder='Paste youtube video URL here' rows={2} value={url} onChange={handleUrlChange}></textarea>
            <button className='bg-blue-600 text-white px-4 py-2 rounded-md font-semibold hover:bg-blue-700 transition-colors' onClick={handleLoadTranscripts}>Load transcripts</button>
        </div>
    )
}
export const FPromptBar =  ()=>{
    const {video_id} = useContext(AppContext);
    const [query,setQuery] = useState('');
    const [loading,setLoading]=useState(false);
    const handleQueryChange = (e)=>{
        setQuery(e.target.value);
    }
    const handleNewChat = async ()=>{
        console.log(video_id);
        console.log(query);
        const response = await apiService.newChat(video_id,query);
        console.log(response);
    }
    
    return(
        <div className='flex items-center gap-3 bg-white p-4 rounded-lg shadow'>
            <textarea name="prompt" className="flex-1 resize-none border border-gray-400 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 transition" placeholder='Enter your query here' rows={2} value={query} onChange={handleQueryChange}></textarea>
            <button className='bg-blue-600 p-2 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center' onClick={handleNewChat}><img src={send} alt="send" className='h-5 w-5'/ ></button>
        </div>

    );
}
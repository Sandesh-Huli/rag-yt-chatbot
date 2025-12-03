import { apiService } from '../services/api.js'
import extractYoutubeVideoId from '../services/fetchVideoId.js'
import { useContext, useState } from 'react'
import send from '../assets/send.png'
import { AppContext } from '../context/AppContext.jsx';
import { ChatContext } from '../context/ChatContext.jsx';
export const IPromptBar = () => {
    const [url, setUrl] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const { newChat, setNewChat } = useContext(AppContext);
    const { video_id, setVideoId, setActiveChatId } = useContext(ChatContext);
    
    const handleUrlChange = (e) => {
        setUrl(e.target.value);
        setError("");
    }
    
    const validateYouTubeUrl = (url) => {
        if (!url || url.trim() === "") {
            return { valid: false, error: "Please enter a YouTube URL" };
        }
        
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
        if (!youtubeRegex.test(url)) {
            return { valid: false, error: "Invalid YouTube URL format" };
        }
        
        return { valid: true, error: null };
    };
    
    const handleLoadTranscripts = () => {
        const validation = validateYouTubeUrl(url);
        
        if (!validation.valid) {
            setError(validation.error);
            return;
        }
        
        const id = extractYoutubeVideoId(url);
        
        if (!id) {
            setError("Could not extract video ID from URL. Please check the URL format.");
            return;
        }
        
        setVideoId(id);
        setActiveChatId(null);
        setNewChat(false);
        setError("");
    }
    return (
        <div className='flex flex-col gap-2'>
            <div className='flex items-center gap-3 bg-white p-4 rounded-lg shadow'>
                <textarea 
                    name="prompt" 
                    className={`flex-1 resize-none border ${error ? 'border-red-400' : 'border-gray-400'} rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 transition`} 
                    placeholder='Paste YouTube video URL here (e.g., https://www.youtube.com/watch?v=...)' 
                    rows={2} 
                    value={url} 
                    onChange={handleUrlChange}
                />
                <button 
                    className='bg-blue-600 text-white px-4 py-2 rounded-md font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed' 
                    onClick={handleLoadTranscripts}
                    disabled={loading}
                >
                    {loading ? 'Loading...' : 'Load transcripts'}
                </button>
            </div>
            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-md text-sm">
                    {error}
                </div>
            )}
        </div>
    )
}
export const FPromptBar = () => {
    const { video_id, addMessage, activeChatId } = useContext(ChatContext);
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    
    const handleQueryChange = (e) => {
        setQuery(e.target.value);
    }
    
    const handleChat = async () => {
        if(!query.trim()) return;
        
        setLoading(true);
        addMessage(query, 'user');
        
        try {
            const res = activeChatId
                ? await apiService.resumeChat(activeChatId, video_id, query)
                : await apiService.newChat(video_id, query);
            
            addMessage(res.data.response, 'ai');
            setQuery('');
        } catch(err) {
            console.error('Error details:', {
                message: err.message,
                response: err.response?.data,
                status: err.response?.status
            });
            
            const errorMessage = err.response?.data?.detail || 
                               err.response?.data?.message || 
                               'Sorry, something went wrong. Please try again.';
            addMessage(errorMessage, 'ai');
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className='flex items-center gap-3 bg-white p-4 rounded-lg shadow'>
            <textarea 
                name="prompt" 
                className="flex-1 resize-none border border-gray-400 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 transition" 
                placeholder='Enter your query here' 
                rows={2} 
                value={query} 
                onChange={handleQueryChange}
                disabled={loading}
            />
            <button 
                className='bg-blue-600 p-2 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center disabled:opacity-50' 
                onClick={handleChat} 
                type='button'
                disabled={loading}
            >
                {loading ? (
                    <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                ) : (
                    <img src={send} alt="send" className='h-5 w-5'/>
                )}
            </button>
        </div>
    );
}
import plus from '../assets/plus.png'
import PrevChat from './PrevChat'

export default function Sidebar() {
    const chat = {
        "title": "React tutorial",
        yt_id: "387465",
        query: "Summarize the video",
        last_updated: "2 hours ago"
    }
    // const chat = {
    //     //fetch from api and databse
    // }
    return (
        <div className="h-full w-64 bg-white shadow-lg flex flex-col p-4">
            <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg mb-6 hover:bg-blue-700 transition-colors">
                <img src={plus} alt="new chat" className='h-5' />
                <span className="font-semibold">New Chat</span>
            </button>
            <div className="flex-1 space-y-4 overflow-y-auto">
                <PrevChat chat={chat} />
                <PrevChat chat={chat} />
                <PrevChat chat={chat} />
                <PrevChat chat={chat} />
            </div>
        </div>
    )
}
export default function PrevChat({chat}) {
    return (
        <div className="bg-gray-100 rounded-lg p-4 shadow hover:bg-blue-50 transition-colors cursor-pointer">
            <h3 className="text-lg font-semibold text-gray-800 mb-1">{chat.title}</h3>
            <p className="text-xs text-gray-500 mb-1">Video ID: {chat.yt_id}</p>
            <p className="text-sm text-gray-700 mb-1">{chat.query}</p>
            <p className="text-xs text-gray-400">{chat.last_updated}</p>
        </div>
    )
}
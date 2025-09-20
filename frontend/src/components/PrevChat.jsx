export default function PrevChat({chat}) {
    return (
        <div>
            <h3>{chat.title}</h3>
            <p>{chat.yt_id}</p>
            <p>{chat.query}</p>
            <p>{chat.last_updated}</p>
        </div>
    )
}
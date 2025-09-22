import send from '../assets/send.png'
export const IPromptBar = () =>{
    return(
        <div className='flex items-center gap-3 bg-white p-4 rounded-lg shadow'>
            <textarea name="prompt" className="flex-1 resize-none border border-gray-400 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 transition" placeholder='Paste youtube video URL here' rows={2}></textarea>
            <button className='bg-blue-600 text-white px-4 py-2 rounded-md font-semibold hover:bg-blue-700 transition-colors'>Load transcripts</button>
        </div>
    )
}
export const FPromptBar = ()=>{
    return(
        <div className='flex items-center gap-3 bg-white p-4 rounded-lg shadow'>
            <textarea name="prompt" className="flex-1 resize-none border border-gray-400 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 transition" placeholder='Enter your query here' rows={2}></textarea>
            <button className='bg-blue-600 p-2 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center'><img src={send} alt="send" className='h-5 w-5'/></button>
        </div>

    )
}
export default function extractYoutubeVideoId(url) {
  // Regular expression pattern to match YouTube video URL and extract the video ID
   const pattern = /[?&]v=([a-zA-Z0-9_-]{11})(?=&|$)/;

  const match = url.match(pattern);
  
  if (match) {
    return match[1];  // Return the video ID (first captured group)
  } else {
    return null;  // Return null if no match is found
  }
}
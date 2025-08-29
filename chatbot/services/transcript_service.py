from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def fetch_youtube_transcript(video_id: str, lang: str = "en") -> list[str]:
    """
    Fetches the transcript for a given YouTube video ID.
    Tries the requested language, then auto-generated, then any available transcript.
    Returns the transcript as a list of strings (one per segment).
    Raises an exception if transcript is not available.
    """
    try:
        api = YouTubeTranscriptApi()
        transcripts = api.list(video_id)
        # Try requested language
        try:
            transcript_obj = transcripts.find_transcript([lang])
        except NoTranscriptFound:
            # Try auto-generated
            try:
                transcript_obj = transcripts.find_transcript([f'a.{lang}'])
            except NoTranscriptFound:
                # Fallback: use the first available transcript
                available_transcripts = list(transcripts._manually_created_transcripts.values()) + list(transcripts._generated_transcripts.values())
                if not available_transcripts:
                    raise NoTranscriptFound()
                transcript_obj = available_transcripts[0]
        transcript_list = transcript_obj.fetch()
        return [chunk.text for chunk in transcript_list]
    except TranscriptsDisabled:
        raise Exception("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise Exception("No transcript found for this video.")
    except Exception as e:
        raise Exception(f"Failed to fetch transcript: {str(e)}")

if __name__ == "__main__":
    vid = "jZyAB2KFDls"
    try:
        lines = fetch_youtube_transcript(vid)
        print(lines)
    except Exception as err:
        print(f"Error: {err}")
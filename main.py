import os
import sys
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# Constants
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

if not YOUTUBE_API_KEY:
    print("Error: YOUTUBE_API_KEY environment variable is not set.")
    sys.exit(1)

def get_video_metadata(channel_id):
    """
    Retrieve video metadata from a specific YouTube channel.
    """
    base_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'channelId': channel_id,
        'maxResults': 50,
        'key': YOUTUBE_API_KEY
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching video metadata: {e}")
        if response.status_code == 403:
            print("This may be due to an invalid or unauthorized YouTube API key.")
        sys.exit(1)

def extract_transcript(video_id):
    """
    Extract transcript from a YouTube video using the youtube-transcript-api.
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        raise Exception(f"Error extracting transcript: {e}")

if __name__ == "__main__":
    # Example usage
    channel_id = "UCcgaoWXUKFl-P3rdNXCuWjg"  # Replace with actual channel ID
    video_metadata = get_video_metadata(channel_id)
    print(video_metadata)
    if video_metadata.get('items'):
        video_id = video_metadata['items'][0]['id']['videoId']
        transcript = extract_transcript(video_id)
        print(transcript)

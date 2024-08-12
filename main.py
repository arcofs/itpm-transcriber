import os
import sys
import requests
import json
from youtube_transcript_api import YouTubeTranscriptApi
import anthropic
import couchdb
from urllib.parse import quote
import socket
from datetime import datetime
import uuid

# Constants
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
TRANSCRIBED_VIDEOS_FILE = 'transcribed_videos.json'

# CouchDB connection details
COUCHDB_URL = os.getenv('COUCHDB_URL')
COUCHDB_USERNAME = os.getenv('COUCHDB_USERNAME')
COUCHDB_PASSWORD = os.getenv('COUCHDB_PASSWORD')
COUCHDB_DATABASE = 'obsidiandb'

if not COUCHDB_URL or not COUCHDB_USERNAME or not COUCHDB_PASSWORD:
    print("Error: CouchDB environment variables are not set.")
    sys.exit(1)

if not YOUTUBE_API_KEY:
    print("Error: YOUTUBE_API_KEY environment variable is not set.")
    sys.exit(1)

if not ANTHROPIC_API_KEY:
    print("Error: ANTHROPIC_API_KEY environment variable is not set.")
    sys.exit(1)

# Initialize Anthropic client with the beta header
claude = anthropic.Anthropic(
    api_key=ANTHROPIC_API_KEY,
    default_headers={
        "anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"
    }
)

def get_video_metadata(channel_id, max_results=5):
    """
    Retrieve the latest video metadata from a specific YouTube channel.
    """
    base_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'channelId': channel_id,
        'maxResults': max_results,
        'order': 'date',
        'type': 'video',
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

def is_itpm_flash_video(title):
    """
    Check if the video title contains 'ITPM Flash'.
    """
    return 'ITPM Flash' in title

def extract_transcript(video_id):
    """
    Extract transcript from a YouTube video using the youtube-transcript-api.
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        raise Exception(f"Error extracting transcript: {e}")

def process_transcript(transcript):
    """
    Process the transcript to extract only the spoken text.
    """
    return ' '.join([entry['text'] for entry in transcript if entry['text'] not in ['[Music]', '[Applause]']])

def generate_insights(transcript):
    """
    Send processed transcript to Anthropic Claude for analysis and extract insights.
    """
    prompt = f"""
\n\nHuman: 
    You will be provided with a text transcript of discussions from financial industry professionals. 
    This transcript will include insights into the current macroeconomic landscape, stocks of interest, 
    market trends, potential investment opportunities, and all other topics relating around financial trading. 
    Your task is to analyze the content and produce the following outputs:

    - Summarized Key Points: Provide 5-10 bullet points summarizing the main takeaways from the discussion.
    - Identified Key Topics: Highlight the key topics discussed in the text.
    - Extracted Actionable Advice: Identify and extract any actionable advice or tips mentioned that could 
    guide investment decisions.
    - Sentiment Analysis: Perform a brief sentiment analysis of the content, noting whether the professionals 
    are optimistic, pessimistic, or neutral.
    - Research Recommendations: Advise the reader on where they should gather further information about the 
    mentioned stocks, commodities, or market trends. Prioritize sources that would provide a competitive edge 
    in making profitable investment decisions.
    Ensure that the analysis is focused on practical investment opportunities, as the end goal is to help 
    the reader make informed decisions to maximize their financial returns.

    Transcript:
    {transcript}

    Please format your response in Markdown.
\n\nAssistant:
    """

    try:
        response = claude.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=8192,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error generating insights: {e}")
        return None

def connect_to_couchdb():
    """
    Connect to the CouchDB server and return the database object.
    """
    full_url = f"https://{COUCHDB_USERNAME}:****@{COUCHDB_URL}"
    print(f"Attempting to connect to CouchDB at: {full_url}")
    
    try:
        server = couchdb.Server(f"https://{quote(COUCHDB_USERNAME)}:{quote(COUCHDB_PASSWORD)}@{COUCHDB_URL}")
        db = server[COUCHDB_DATABASE]
        return db
    except couchdb.http.Unauthorized:
        print("Error: Unauthorized access to CouchDB. Please check your username and password.")
    except couchdb.http.ResourceNotFound:
        print(f"Error: Database '{COUCHDB_DATABASE}' not found on the CouchDB server.")
    except socket.gaierror as e:
        print(f"Error: Unable to resolve CouchDB URL. Please check your internet connection and the COUCHDB_URL.")
        print(f"Detailed error: {e}")
    except requests.exceptions.ConnectionError:
        print("Error: Unable to connect to CouchDB. Please check if the server is running and accessible.")
    except Exception as e:
        print(f"Unexpected error connecting to CouchDB: {e}")
    
    sys.exit(1)

def save_insights(video_title, insights):
    """
    Save the generated insights to CouchDB in a format compatible with Obsidian.
    """
    db = connect_to_couchdb()
    file_name = f"{video_title.replace('/', '_').replace(' ', '_').lower()}.md"
    doc_id = f"Video Summaries/{file_name}"
    child_id = f"h:{uuid.uuid4().hex[:12]}"
    
    current_time = int(datetime.utcnow().timestamp() * 1000)  # milliseconds since epoch
    
    try:
        # Create or update the parent document
        parent_doc = db.get(doc_id, {})
        parent_doc.update({
            "_id": doc_id,
            "children": [child_id],
            "path": f"Video Summaries/{file_name}",
            "ctime": parent_doc.get("ctime", current_time),
            "mtime": current_time,
            "size": len(insights),
            "type": "markdown",
            "eden": {}
        })
        db.save(parent_doc)
        
        # Create or update the child document
        child_doc = {
            "_id": child_id,
            "data": insights,
            "type": "leaf"
        }
        db.save(child_doc)
        
        print(f"Insights saved to CouchDB with ID: {doc_id}")
        return True
    except couchdb.http.ResourceConflict:
        print(f"Document with ID {doc_id} already exists. Updating...")
        existing_parent = db[doc_id]
        existing_parent.update(parent_doc)
        db.save(existing_parent)
        
        existing_child = db[child_id]
        existing_child.update(child_doc)
        db.save(existing_child)
        
        print(f"Updated document with ID: {doc_id}")
        return True
    except Exception as e:
        print(f"Error saving insights to CouchDB: {e}")
        return False

# Load existing transcribed videos
def load_transcribed_videos():
    """
    Load the list of already transcribed videos from a JSON file.
    """
    if os.path.exists(TRANSCRIBED_VIDEOS_FILE):
        with open(TRANSCRIBED_VIDEOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Save transcribed video IDs to the JSON file
def save_transcribed_video(video_id):
    """
    Save the transcribed video ID to the JSON file.
    """
    transcribed_videos = load_transcribed_videos()
    if video_id not in transcribed_videos:
        transcribed_videos.append(video_id)
        with open(TRANSCRIBED_VIDEOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(transcribed_videos, f)

if __name__ == "__main__":
    channel_id = "UCcgaoWXUKFl-P3rdNXCuWjg"
    video_metadata = get_video_metadata(channel_id, max_results=10)
    
    transcribed_videos = load_transcribed_videos()  # Load existing transcribed videos

    try:
        db = connect_to_couchdb()
    except SystemExit:
        print("Exiting due to CouchDB connection error.")
        sys.exit(1)

    for item in video_metadata.get('items', []):
        video_id = item['id']['videoId']
        video_title = item['snippet']['title']
        
        if video_id in transcribed_videos:
            print(f"Video already transcribed: {video_title}")
            continue  # Skip already transcribed videos

        if is_itpm_flash_video(video_title):
            print(f"Processing ITPM Flash video: {video_title}")
            try:
                transcript = extract_transcript(video_id)
                processed_transcript = process_transcript(transcript)
                
                # Generate and save insights
                insights = generate_insights(processed_transcript)
                if insights:
                    save_insights(video_title, insights)
                    save_transcribed_video(video_id)  # Save the video ID after processing
                
                print(f"Successfully processed: {video_title}")
            except Exception as e:
                print(f"Failed to process {video_title}: {str(e)}")
        else:
            print(f"Skipping non-ITPM Flash video: {video_title}")

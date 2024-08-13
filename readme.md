# YouTube Transcript Insights Generator

This project retrieves the latest video metadata from a specified YouTube channel (Currently ITPM), extracts transcripts from selected videos, and generates insights using the Anthropic Claude API. The insights are then saved in Markdown format for easy access and readability. Currently its setup to get the latest videos from the ITPM youtube channel, transcribe only the Falash videos and parse them through a LLM to summarise and gainm insights

## Features

- Fetches the latest videos from a YouTube channel.
- Extracts transcripts from videos containing "ITPM Flash" in the title.
- Analyzes transcripts to generate actionable insights.
- Saves insights in a Markdown file.

## Requirements

- Python 3.x
- `requests` library
- `youtube-transcript-api` library
- `anthropic` library
- `python-dotenv` library

## Setup

1. **Clone the repository:**
   ```bash
   git clone this repo
   cd this-repo-name
   ```

2. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file in the root directory and add your API keys:**
   ```plaintext
   YOUTUBE_API_KEY=your_youtube_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

## Usage

1. **Run the script:**
   ```bash
   python main.py
   ```

2. **Output:**
   - The insights will be saved in a Markdown file in the specified directory (`TARGET_DIRECTORY`).
   - The filename will be based on the video title, formatted to be URL-friendly.

## License

This project is licensed under the MIT License.
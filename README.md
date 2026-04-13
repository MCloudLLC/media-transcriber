# Video to Text Transcription

This project extracts audio from a video file, transcribes it into English text using the Azure Speech API, and saves the transcription to a text file.

## Features
- Extracts audio from video files (supports multiple formats like MP4).
- Splits audio into manageable segments if necessary (default: 1-minute segments).
- Transcribes audio to text using Azure Speech-to-Text API.
- Saves the transcription to a text file for further editing.
- Cleans up temporary files after processing.
- Handles errors gracefully during audio processing and transcription.

## Prerequisites
- Python 3.8 or higher.
- Azure Speech API key and location.
- `ffmpeg` — required for audio extraction:
  - **macOS:** `brew install ffmpeg`
  - **Ubuntu/Debian:** `sudo apt-get install ffmpeg`
  - **Windows:** Download from https://ffmpeg.org/download.html and add to PATH

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/MCloudLLC/video-to-text-azure-speech-api.git
   cd video-to-text-azure-speech-api
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Azure Speech API credentials as environment variables:
   
   **Linux/macOS:**
   ```bash
   export AZURE_SPEECH_KEY="your_azure_speech_api_key"
   export AZURE_AI_LOCATION="your_azure_ai_location"
   ```
   
   **Windows (Command Prompt):**
   ```cmd
   set AZURE_SPEECH_KEY=your_azure_speech_api_key
   set AZURE_AI_LOCATION=your_azure_ai_location
   ```
   
   **Windows (PowerShell):**
   ```powershell
   $env:AZURE_SPEECH_KEY="your_azure_speech_api_key"
   $env:AZURE_AI_LOCATION="your_azure_ai_location"
   ```

## Usage
1. Run the script with a video file as input:
   ```bash
   python main.py /path/to/video.mp4
   ```

2. The script will:
   - Extract audio from the video.
   - Transcribe the audio into text.
   - Save the transcription to a file named `<video_file_name>_transcription.txt`.
   - Open the transcription file for editing.

## Project Structure
```
video-to-text-azure-speech-api/
├── helper.py          # Contains utility functions for audio processing and transcription.
├── main.py            # Main script to run the transcription process.
├── requirements.txt   # Lists the required Python packages.
├── README.md          # Project documentation.
├── LICENSE            # License information.
├── .gitignore         # Files and directories to ignore in version control.
└── tests/             # Test suite (pytest).
```

## Example
Suppose you have a video file named `example.mp4`. Run the following command:
```bash
python main.py example.mp4
```
The transcription will be saved to `example_transcription.txt` in the same directory.

## Notes
- Supported formats: MP4, AVI, MKV, MOV, MP3, WAV, FLAC, OGG (and others supported by ffmpeg).
- Azure credentials are read from the `AZURE_SPEECH_KEY` and `AZURE_AI_LOCATION` environment variables. The application will exit immediately on startup if either variable is missing.
- Temporary audio files created during processing will be automatically deleted after transcription.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
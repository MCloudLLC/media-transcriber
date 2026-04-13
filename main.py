import os
import sys
import subprocess
import logging
import helper

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    """
    Main function to handle the video-to-text transcription process.
    """
    # Load and validate Azure credentials from environment variables
    azure_speech_key = os.environ.get("AZURE_SPEECH_KEY")
    azure_ai_location = os.environ.get("AZURE_AI_LOCATION")
    if not azure_speech_key or not azure_ai_location:
        logging.error("Missing required environment variables: AZURE_SPEECH_KEY and/or AZURE_AI_LOCATION")
        sys.exit(1)

    # Ensure the input file is provided as a command-line argument
    if len(sys.argv) < 2:
        logging.error("Usage: python main.py <path_to_video_file>")
        sys.exit(1)

    # Get the input file path from the command-line argument
    input_file = sys.argv[1]

    # Check if the input file exists
    if not helper.check_file_exists(input_file):
        logging.error("File does not exist or the path is invalid.")
        sys.exit(1)

    # Initialize audio_files to empty list so finally block can reference it
    audio_files = []
    
    try:
        # Step 1: Extract and process the audio channel from the video
        audio = helper.get_audio_channel(input_file)
        if audio is None:
            logging.error("Failed to process the audio channel.")
            sys.exit(1)

        # Step 2: Split the audio into smaller segments if necessary
        audio_files = helper.load_audio_segments(audio)

        # Step 3: Transcribe the audio segments using Azure Speech-to-Text API
        transcribed_text = helper.transcribe_audio_segments(
            audio_files, api_key=azure_speech_key, api_location=azure_ai_location
        )

        # Step 4: Write the transcribed text to a file
        helper.write_file(input_file, transcribed_text)

        # Step 5: Open the transcription file for editing
        transcription_file = helper.get_transcription_file(input_file)
        
        # Cross-platform file opener
        if sys.platform == "win32":
            os.startfile(transcription_file)
        elif sys.platform == "darwin":
            subprocess.run(["open", transcription_file])
        else:  # Linux and other Unix-like systems
            subprocess.run(["xdg-open", transcription_file])

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
    
    finally:
        # Always clean up temporary audio files
        if audio_files:
            helper.clean_up_temp_files(audio_files)

if __name__ == "__main__":
    main()
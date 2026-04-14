import os
import logging
import gradio as gr
import helper

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_WHISPER_BACKENDS = {"whisper", "openai-whisper"}

def _get_azure_creds(key_input: str, location_input: str):
    key = os.environ.get("AZURE_SPEECH_KEY", key_input or "").strip()
    location = os.environ.get("AZURE_AI_LOCATION", location_input or "").strip()
    return key or None, location or None


def transcribe(
    file_path,
    url: str,
    backend: str,
    model: str,
    device: str,
    azure_key: str,
    azure_location: str,
    progress=gr.Progress(track_tqdm=False),
):
    """Gradio transcription handler."""
    status_msgs = []

    def _cb(step: int, total: int, message: str):
        progress(step / total, desc=message)
        status_msgs.append(message)

    # Resolve input: prefer file upload, fall back to URL
    if file_path:
        input_source = file_path
    elif url and url.strip():
        input_source = url.strip()
    else:
        return "", None, "❌ Please upload a file or enter a YouTube URL."

    azure_speech_key, azure_ai_location = _get_azure_creds(azure_key, azure_location)

    try:
        full_text, output_file = helper.transcribe_pipeline(
            input_source=input_source,
            backend=backend,
            model_size=model,
            device=device,
            azure_speech_key=azure_speech_key,
            azure_ai_location=azure_ai_location,
            progress_callback=_cb,
        )
        return full_text, output_file, "✅ Transcription complete."
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return "", None, f"❌ Error: {e}"


def _backend_change(backend: str):
    is_whisper = backend in _WHISPER_BACKENDS
    is_azure = backend == "azure"
    return (
        gr.update(visible=is_whisper),   # model
        gr.update(visible=is_whisper),   # device
        gr.update(visible=is_azure),     # azure_key
        gr.update(visible=is_azure),     # azure_location
    )


def create_app() -> gr.Blocks:
    with gr.Blocks(title="Media Transcriber") as demo:
        gr.Markdown("# 🎬 Media Transcriber")
        gr.Markdown("Transcribe video/audio files or YouTube URLs to text.")

        with gr.Tabs():
            with gr.Tab("Transcribe"):
                with gr.Row():
                    with gr.Column(scale=1):
                        file_input = gr.File(
                            label="Upload video or audio file",
                            file_types=[
                                ".mp4", ".avi", ".mkv", ".mov", ".webm",
                                ".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a",
                            ],
                        )
                        url_input = gr.Textbox(
                            label="Or enter a YouTube URL",
                            placeholder="https://www.youtube.com/watch?v=...",
                        )
                        backend_radio = gr.Radio(
                            choices=["whisper", "openai-whisper", "azure"],
                            value="whisper",
                            label="Backend",
                            info="whisper = faster (CUDA 11/12) | openai-whisper = CUDA 13.x compatible | azure = cloud",
                        )
                        model_dd = gr.Dropdown(
                            choices=["tiny", "base", "small", "medium", "large"],
                            value="base",
                            label="Model size",
                            info="Larger = more accurate but slower",
                            visible=True,
                        )
                        device_radio = gr.Radio(
                            choices=["cpu", "cuda"],
                            value="cpu",
                            label="Device",
                            visible=True,
                        )
                        azure_key_box = gr.Textbox(
                            label="Azure Speech Key",
                            type="password",
                            placeholder="Leave blank to use AZURE_SPEECH_KEY env var",
                            visible=False,
                        )
                        azure_loc_box = gr.Textbox(
                            label="Azure Region",
                            placeholder="e.g. eastus (or set AZURE_AI_LOCATION env var)",
                            visible=False,
                        )
                        transcribe_btn = gr.Button("Transcribe", variant="primary")

                    with gr.Column(scale=2):
                        output_text = gr.Textbox(
                            label="Transcription",
                            lines=20,
                            show_copy_button=True,
                        )
                        output_file = gr.File(label="Download transcript")
                        status_box = gr.Textbox(label="Status", interactive=False)

                backend_radio.change(
                    fn=_backend_change,
                    inputs=[backend_radio],
                    outputs=[model_dd, device_radio, azure_key_box, azure_loc_box],
                )

                transcribe_btn.click(
                    fn=transcribe,
                    inputs=[
                        file_input, url_input, backend_radio,
                        model_dd, device_radio, azure_key_box, azure_loc_box,
                    ],
                    outputs=[output_text, output_file, status_box],
                )

    return demo


def launch():
    demo = create_app()
    demo.launch(server_port=7860)


if __name__ == "__main__":
    launch()

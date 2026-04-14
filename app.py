import os
import threading
import logging
from tkinter import filedialog
from dotenv import load_dotenv

import customtkinter as ctk

import helper

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_AUDIO_FILE_TYPES = [
    ("Media files", "*.mp4 *.avi *.mkv *.mov *.webm *.mp3 *.wav *.flac *.ogg *.aac *.m4a"),
    ("All files", "*.*"),
]


class App:
    def __init__(self):
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.title("Media Transcriber")
        self.root.minsize(900, 650)
        self._selected_file: str | None = None
        self._qa = None
        self._current_transcript: str = ""
        self._setup_ui()

    def _setup_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        tabview = ctk.CTkTabview(self.root)
        tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tabview.add("Transcribe")
        tabview.add("Q&A")

        tab = tabview.tab("Transcribe")
        tab.grid_columnconfigure(0, weight=35)
        tab.grid_columnconfigure(1, weight=65)
        tab.grid_rowconfigure(0, weight=1)

        self._build_left_panel(tab)
        self._build_right_panel(tab)

        self._build_qa_tab(tabview.tab("Q&A"))

    def _build_left_panel(self, parent):
        left = ctk.CTkFrame(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        left.grid_columnconfigure(0, weight=1)

        row = 0

        # File browse
        self._browse_btn = ctk.CTkButton(left, text="Browse file...", command=self._browse_file)
        self._browse_btn.grid(row=row, column=0, sticky="ew", padx=10, pady=(10, 2))
        row += 1

        self._file_label = ctk.CTkLabel(
            left, text="No file selected", text_color="gray", anchor="w", wraplength=220
        )
        self._file_label.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 6))
        row += 1

        # URL
        ctk.CTkLabel(left, text="Or YouTube URL:", anchor="w").grid(
            row=row, column=0, sticky="ew", padx=10, pady=(0, 2)
        )
        row += 1
        self._url_entry = ctk.CTkEntry(
            left, placeholder_text="https://www.youtube.com/watch?v=..."
        )
        self._url_entry.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))
        row += 1

        # Backend
        ctk.CTkLabel(left, text="Backend:", anchor="w").grid(
            row=row, column=0, sticky="ew", padx=10, pady=(0, 2)
        )
        row += 1
        self._backend_seg = ctk.CTkSegmentedButton(
            left,
            values=["openai-whisper", "azure"],
            command=self._on_backend_change,
        )
        self._backend_seg.set("openai-whisper")
        self._backend_seg.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))
        row += 1

        # Model size (hidden when backend == "azure")
        self._model_label = ctk.CTkLabel(left, text="Model:", anchor="w")
        self._model_label.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 2))
        row += 1
        self._model_menu = ctk.CTkOptionMenu(
            left, values=["tiny", "base", "small", "medium", "large", "large-v3"]
        )
        self._model_menu.set("base")
        self._model_menu.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))
        row += 1

        # Device (hidden when backend == "azure")
        self._device_label = ctk.CTkLabel(left, text="Device:", anchor="w")
        self._device_label.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 2))
        row += 1
        self._device_seg = ctk.CTkSegmentedButton(left, values=["cpu", "cuda"])
        self._device_seg.set("cuda")
        self._device_seg.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))
        row += 1

        # Azure Speech Key (only shown when backend == "azure")
        self._azure_key_label = ctk.CTkLabel(left, text="Azure Speech Key:", anchor="w")
        self._azure_key_label.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 2))
        row += 1
        self._azure_key_entry = ctk.CTkEntry(
            left, placeholder_text="Leave blank to use env var", show="*"
        )
        self._azure_key_entry.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))
        row += 1

        # Azure Region (only shown when backend == "azure")
        self._azure_region_label = ctk.CTkLabel(left, text="Azure Region:", anchor="w")
        self._azure_region_label.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 2))
        row += 1
        self._azure_region_entry = ctk.CTkEntry(left, placeholder_text="e.g. eastus")
        self._azure_region_entry.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))
        row += 1

        # Transcribe button (full width, disabled during transcription)
        self._transcribe_btn = ctk.CTkButton(
            left, text="Transcribe", command=self._start_transcription
        )
        self._transcribe_btn.grid(row=row, column=0, sticky="ew", padx=10, pady=(10, 10))

        # Group widgets for show/hide by backend
        self._whisper_widgets = [
            self._model_label, self._model_menu,
            self._device_label, self._device_seg,
        ]
        self._azure_widgets = [
            self._azure_key_label, self._azure_key_entry,
            self._azure_region_label, self._azure_region_entry,
        ]

        # Azure widgets start hidden (default backend is "whisper")
        for w in self._azure_widgets:
            w.grid_remove()

    def _build_right_panel(self, parent):
        right = ctk.CTkFrame(parent)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        # Transcript output (read-only)
        self._transcript_box = ctk.CTkTextbox(right, state="disabled")
        self._transcript_box.grid(
            row=0, column=0, sticky="nsew", padx=10, pady=(10, 5)
        )

        # Copy + Save As buttons
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(btn_frame, text="Copy", command=self._copy_transcript).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ctk.CTkButton(btn_frame, text="Save As...", command=self._save_transcript).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

        # Progress bar — hidden until transcription starts, stays visible after
        self._progress_bar = ctk.CTkProgressBar(right)
        self._progress_bar.set(0)
        self._progress_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        self._progress_bar.grid_remove()

        # Status label
        self._status_label = ctk.CTkLabel(right, text="", anchor="w")
        self._status_label.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))

    def _on_backend_change(self, value: str):
        is_azure = value == "azure"
        if is_azure:
            for w in self._whisper_widgets:
                w.grid_remove()
            for w in self._azure_widgets:
                w.grid()
        else:
            for w in self._azure_widgets:
                w.grid_remove()
            for w in self._whisper_widgets:
                w.grid()

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select media file",
            filetypes=_AUDIO_FILE_TYPES,
        )
        if path:
            self._selected_file = path
            self._file_label.configure(text=os.path.basename(path))

    def _start_transcription(self):
        if self._selected_file:
            input_source = self._selected_file
            output_dir = os.path.dirname(self._selected_file)
        else:
            url = self._url_entry.get().strip()
            if not url:
                self._status_label.configure(
                    text="❌ Please select a file or enter a URL."
                )
                return
            input_source = url
            output_dir = None

        backend = self._backend_seg.get()
        model_size = self._model_menu.get()
        device = self._device_seg.get()

        # Resolve Azure credentials: env vars take priority, fall back to UI fields
        azure_key = (
            os.environ.get("AZURE_SPEECH_KEY") or self._azure_key_entry.get().strip() or None
        )
        azure_region = (
            os.environ.get("AZURE_AI_LOCATION") or self._azure_region_entry.get().strip() or None
        )

        if backend == "azure" and (not azure_key or not azure_region):
            self._status_label.configure(
                text="❌ Error: Azure backend requires Speech Key and Region."
            )
            return

        self._transcribe_btn.configure(state="disabled")
        self._progress_bar.set(0)
        self._progress_bar.grid()
        self._status_label.configure(text="Transcribing...")
        self._set_transcript("")

        threading.Thread(
            target=self._run_transcription,
            args=(input_source, backend, model_size, device, azure_key, azure_region, output_dir),
            daemon=True,
        ).start()

    def _run_transcription(self, input_source, backend, model_size, device, azure_key, azure_region, output_dir):
        try:
            full_text, _ = helper.transcribe_pipeline(
                input_source=input_source,
                backend=backend,
                model_size=model_size,
                device=device,
                azure_speech_key=azure_key,
                azure_ai_location=azure_region,
                output_dir=output_dir,
                progress_callback=self._update_progress,
            )
            self.root.after(0, lambda: self._set_transcript(full_text))
            self.root.after(0, lambda: self._status_label.configure(text="✅ Complete"))
            self.root.after(0, lambda: self._progress_bar.set(1.0))
        except Exception as e:
            logging.error(f"Transcription error: {e}")
            msg = f"❌ Error: {e}"
            self.root.after(0, lambda m=msg: self._status_label.configure(text=m))
        finally:
            self.root.after(0, lambda: self._transcribe_btn.configure(state="normal"))

    def _update_progress(self, step: int, total: int, message: str):
        """Schedule a thread-safe progress bar + status update."""
        progress = step / total if total else 0

        def _apply(p=progress, m=message):
            self._progress_bar.set(p)
            self._status_label.configure(text=m)

        self.root.after(0, _apply)

    def _set_transcript(self, text: str):
        self._transcript_box.configure(state="normal")
        self._transcript_box.delete("1.0", "end")
        if text:
            self._transcript_box.insert("1.0", text)
        self._transcript_box.configure(state="disabled")
        self._current_transcript = text
        self._qa = None
        if text:
            self._ask_btn.configure(state="normal")
            self._qa_status_label.configure(text="Ready")
        else:
            self._ask_btn.configure(state="disabled")
            self._qa_status_label.configure(text="Transcribe a file first")

    def _copy_transcript(self):
        text = self._transcript_box.get("1.0", "end").strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)

    def _save_transcript(self):
        text = self._transcript_box.get("1.0", "end").strip()
        if not text:
            self._status_label.configure(text="Nothing to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save transcript",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self._status_label.configure(text=f"Saved to {os.path.basename(path)}")

    def _build_qa_tab(self, parent):
        parent.grid_columnconfigure(0, weight=35)
        parent.grid_columnconfigure(1, weight=65)
        parent.grid_rowconfigure(0, weight=1)

        # Left panel — config + input
        left = ctk.CTkFrame(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        left.grid_columnconfigure(0, weight=1)

        row = 0
        ctk.CTkLabel(left, text="LLM URL:", anchor="w").grid(
            row=row, column=0, sticky="ew", padx=10, pady=(10, 2)
        )
        row += 1
        self._llm_url_entry = ctk.CTkEntry(left, placeholder_text="http://localhost:11434/v1")
        self._llm_url_entry.insert(0, "http://localhost:11434/v1")
        self._llm_url_entry.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 6))
        row += 1

        ctk.CTkLabel(left, text="API Key:", anchor="w").grid(
            row=row, column=0, sticky="ew", padx=10, pady=(0, 2)
        )
        row += 1
        self._llm_key_entry = ctk.CTkEntry(
            left, show="*", placeholder_text="Leave blank for Ollama"
        )
        self._llm_key_entry.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 6))
        row += 1

        ctk.CTkLabel(left, text="Model:", anchor="w").grid(
            row=row, column=0, sticky="ew", padx=10, pady=(0, 2)
        )
        row += 1
        self._llm_model_entry = ctk.CTkEntry(left, placeholder_text="llama3")
        self._llm_model_entry.insert(0, "llama3")
        self._llm_model_entry.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))
        row += 1

        # Separator via padding
        ctk.CTkFrame(left, height=2, fg_color="gray50").grid(
            row=row, column=0, sticky="ew", padx=10, pady=(0, 10)
        )
        row += 1

        ctk.CTkLabel(left, text="Ask a question:", anchor="w").grid(
            row=row, column=0, sticky="ew", padx=10, pady=(0, 2)
        )
        row += 1
        self._question_box = ctk.CTkTextbox(left, height=80, wrap="word")
        self._question_box.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 6))
        row += 1

        self._ask_btn = ctk.CTkButton(left, text="Ask", command=self._start_ask, state="disabled")
        self._ask_btn.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 4))
        row += 1

        ctk.CTkButton(left, text="Clear Chat", command=self._clear_chat).grid(
            row=row, column=0, sticky="ew", padx=10, pady=(0, 6)
        )
        row += 1

        self._qa_status_label = ctk.CTkLabel(
            left, text="Transcribe a file first", anchor="w", wraplength=220
        )
        self._qa_status_label.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Right panel — chat history
        right = ctk.CTkFrame(parent)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        self._chat_box = ctk.CTkTextbox(right, state="disabled", wrap="word")
        self._chat_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _start_ask(self):
        question = self._question_box.get("1.0", "end").strip()
        if not question:
            self._qa_status_label.configure(text="Please enter a question.")
            return
        self._ask_btn.configure(state="disabled")
        self._qa_status_label.configure(text="Thinking...")
        threading.Thread(target=self._run_ask, args=(question,), daemon=True).start()

    def _run_ask(self, question: str):
        try:
            if self._qa is None:
                try:
                    from qa import TranscriptQA  # noqa: PLC0415
                except ImportError:
                    self.root.after(
                        0,
                        lambda: self._qa_status_label.configure(
                            text="❌ Q&A requires [qa] extra: uv sync --extra qa"
                        ),
                    )
                    return
                llm_url = self._llm_url_entry.get().strip() or "http://localhost:11434/v1"
                api_key = (
                    os.environ.get("OPENAI_API_KEY")
                    or self._llm_key_entry.get().strip()
                    or None
                )
                model = self._llm_model_entry.get().strip() or "llama3"
                self._qa = TranscriptQA(
                    transcript_text=self._current_transcript,
                    llm_url=llm_url,
                    api_key=api_key,
                    model=model,
                )
            answer = self._qa.ask(question)
            entry = f"You: {question}\n\nAssistant: {answer}\n\n{'─' * 40}\n\n"
            self.root.after(0, lambda e=entry: self._append_chat(e))
            self.root.after(0, lambda: self._qa_status_label.configure(text="Ready"))
        except Exception as e:
            msg = f"❌ Error: {e}"
            self.root.after(0, lambda m=msg: self._qa_status_label.configure(text=m))
        finally:
            self.root.after(0, lambda: self._ask_btn.configure(state="normal"))

    def _append_chat(self, text: str):
        self._chat_box.configure(state="normal")
        self._chat_box.insert("end", text)
        self._chat_box.see("end")
        self._chat_box.configure(state="disabled")

    def _clear_chat(self):
        self._chat_box.configure(state="normal")
        self._chat_box.delete("1.0", "end")
        self._chat_box.configure(state="disabled")
        self._qa = None
        self._qa_status_label.configure(text="Ready")

    def launch(self):
        self.root.mainloop()


def launch():
    app = App()
    app.launch()


if __name__ == "__main__":
    launch()

import os
import threading
import logging
from tkinter import filedialog

import customtkinter as ctk

import helper

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
        self._setup_ui()

    def _setup_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        tabview = ctk.CTkTabview(self.root)
        tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tabview.add("Transcribe")
        # Phase 2: Q&A tab placeholder
        # tabview.add("Q&A")

        tab = tabview.tab("Transcribe")
        tab.grid_columnconfigure(0, weight=35)
        tab.grid_columnconfigure(1, weight=65)
        tab.grid_rowconfigure(0, weight=1)

        self._build_left_panel(tab)
        self._build_right_panel(tab)

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
            values=["whisper", "openai-whisper", "azure"],
            command=self._on_backend_change,
        )
        self._backend_seg.set("whisper")
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
        self._device_seg.set("cpu")
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

    def launch(self):
        self.root.mainloop()


def launch():
    app = App()
    app.launch()


if __name__ == "__main__":
    launch()

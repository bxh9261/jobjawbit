# Video Word Remixer Prototype

Upload a short video, transcribe it into word-level clips, drag words into a new sentence, preview individual words, and export the result as an MP4.

## Requirements

- Python 3.10+
- FFmpeg installed and available on PATH
- Several GB of free disk space for the transcription model

## Windows setup

1. Install FFmpeg:

   winget install Gyan.FFmpeg

2. Open a new PowerShell window and confirm:

   ffmpeg -version

3. Create and activate a virtual environment:

   py -m venv .venv
   .\.venv\Scripts\Activate.ps1

4. Install dependencies:

   pip install -r requirements.txt

5. Start the app:

   uvicorn main:app --reload

6. Open:

   http://127.0.0.1:8000

## Notes

- The first transcription downloads the selected faster-whisper model.
- The default model is `small`, running on CPU with int8 computation.
- Short words may include neighboring sounds. This is expected and supports the intentionally spliced style.
- Uploaded and generated files are stored under `projects/`.

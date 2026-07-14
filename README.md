# JobJawbit

JobJawbit is a local Python tool for creating "word remix" videos. Given a source video, it transcribes the speech, records the timestamp of every spoken word, and allows those words to be stitched together into entirely new sentences.

The goal is not to make the edits seamless. Instead, the output intentionally sounds spliced together, as though someone is constructing new dialogue entirely from existing clips.

## Requirements

- Python 3.11 or newer
- FFmpeg installed and available on your system PATH

To verify FFmpeg is installed:

```bash
ffmpeg -version
```

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/JobJawbit.git
cd JobJawbit
```

Create a virtual environment.

### Windows

```powershell
py -m venv .venv
.\.venv\Scripts\activate
```

If PowerShell blocks script execution:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Alternatively, activate the environment using Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Running

Place the video you want to process into the `input` directory.

Run:

```bash
python main.py
```

The program will:

1. Transcribe the video.
2. Record timestamps for every spoken word.
3. Search for the requested words or phrases.
4. Extract the corresponding clips.
5. Concatenate them into a new video.

The first run on a video will take the longest because transcription must be performed. After that, the generated transcript can be reused without processing the video again.

## Project Structure

```
JobJawbit/
├── input/
├── output/
├── main.py
├── requirements.txt
└── README.md
```

## Troubleshooting

### FFmpeg is not recognized

Verify that FFmpeg is installed and on your system PATH.

```bash
ffmpeg -version
```

### Missing Python packages

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Then reinstall the dependencies:

```bash
pip install -r requirements.txt
```

## Future Work

Current development is focused on improving clip quality and usability, including:

- Better phrase matching
- Improved handling of punctuation and pauses
- Faster searching on previously transcribed videos
- Batch processing of multiple requested phrases
- A graphical interface

## License

This project is intended for personal, educational, and research use.
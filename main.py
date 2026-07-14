from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from faster_whisper import WhisperModel

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR / "projects"
STATIC_DIR = BASE_DIR / "static"
PROJECTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Video Word Remixer")

# CPU-friendly default. Change to device="cuda", compute_type="float16"
# when using a supported NVIDIA GPU.
model = WhisperModel("small", device="cpu", compute_type="int8")


class SelectedWord(BaseModel):
    id: str
    text: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)


class ExportRequest(BaseModel):
    project_id: str
    words: list[SelectedWord]
    start_padding_ms: int = Field(default=0, ge=0, le=300)
    end_padding_ms: int = Field(default=50, ge=0, le=300)


def run_ffmpeg(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-5000:])


def safe_extension(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"} else ".mp4"


def project_path(project_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID.")
    path = PROJECTS_DIR / project_id
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found.")
    return path


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)) -> dict[str, Any]:
    project_id = uuid.uuid4().hex
    folder = PROJECTS_DIR / project_id
    folder.mkdir(parents=True)

    source = folder / f"source{safe_extension(file.filename)}"
    with source.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    try:
        segments, info = model.transcribe(
            str(source),
            word_timestamps=True,
            vad_filter=True,
            beam_size=5,
        )

        words: list[dict[str, Any]] = []
        index = 0

        # faster-whisper returns a generator, so it must be consumed here.
        for segment in segments:
            for word in segment.words or []:
                text = word.word.strip()
                if not text or word.start is None or word.end is None:
                    continue

                words.append(
                    {
                        "id": f"word-{index}",
                        "text": text,
                        "start": round(float(word.start), 3),
                        "end": round(float(word.end), 3),
                        "confidence": round(float(word.probability or 0), 3),
                    }
                )
                index += 1

        metadata = {
            "project_id": project_id,
            "source_filename": source.name,
            "language": info.language,
            "language_probability": info.language_probability,
            "words": words,
        }
        (folder / "transcript.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )
        return metadata

    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc


@app.get("/api/projects/{project_id}/source")
def source_video(project_id: str) -> FileResponse:
    folder = project_path(project_id)
    matches = list(folder.glob("source.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Source video not found.")
    return FileResponse(matches[0])


@app.get("/api/projects/{project_id}/word/{word_id}")
def preview_word(project_id: str, word_id: str) -> FileResponse:
    folder = project_path(project_id)
    metadata = json.loads((folder / "transcript.json").read_text(encoding="utf-8"))
    word = next((item for item in metadata["words"] if item["id"] == word_id), None)
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found.")

    source = folder / metadata["source_filename"]
    preview = folder / f"preview-{word_id}.mp4"

    if not preview.exists():
        start = max(0.0, float(word["start"]))
        end = float(word["end"]) + 0.05
        duration = max(0.05, end - start)

        try:
            run_ffmpeg(
                [
                    "ffmpeg", "-y",
                    "-ss", f"{start:.3f}",
                    "-i", str(source),
                    "-t", f"{duration:.3f}",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-af", "afade=t=in:st=0:d=0.008,afade=t=out:st=0:d=0.008",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "22",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    str(preview),
                ]
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=f"Preview failed: {exc}") from exc

    return FileResponse(preview, media_type="video/mp4")


@app.post("/api/export")
def export_video(request: ExportRequest) -> dict[str, str]:
    if not request.words:
        raise HTTPException(status_code=400, detail="Add at least one word.")

    folder = project_path(request.project_id)
    metadata = json.loads((folder / "transcript.json").read_text(encoding="utf-8"))
    source = folder / metadata["source_filename"]
    output = folder / "remix.mp4"

    start_padding = request.start_padding_ms / 1000.0
    end_padding = request.end_padding_ms / 1000.0

    filters: list[str] = []
    concat_inputs: list[str] = []

    for i, word in enumerate(request.words):
        start = max(0.0, word.start - start_padding)
        end = max(start + 0.05, word.end + end_padding)
        duration = end - start
        fade_out_start = max(0.0, duration - 0.008)

        filters.append(
            f"[0:v]trim=start={start:.3f}:end={end:.3f},"
            f"setpts=PTS-STARTPTS,"
            f"scale=trunc(iw/2)*2:trunc(ih/2)*2[v{i}]"
        )
        filters.append(
            f"[0:a]atrim=start={start:.3f}:end={end:.3f},"
            f"asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.008,"
            f"afade=t=out:st={fade_out_start:.3f}:d=0.008[a{i}]"
        )
        concat_inputs.append(f"[v{i}][a{i}]")

    filters.append(
        "".join(concat_inputs)
        + f"concat=n={len(request.words)}:v=1:a=1[outv][outa]"
    )

    try:
        run_ffmpeg(
            [
                "ffmpeg", "-y",
                "-i", str(source),
                "-filter_complex", ";".join(filters),
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(output),
            ]
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc

    return {
        "download_url": f"/api/projects/{request.project_id}/download",
        "preview_url": f"/api/projects/{request.project_id}/download",
    }


@app.get("/api/projects/{project_id}/download")
def download_remix(project_id: str) -> FileResponse:
    folder = project_path(project_id)
    output = folder / "remix.mp4"
    if not output.exists():
        raise HTTPException(status_code=404, detail="Export not found.")
    return FileResponse(output, media_type="video/mp4", filename="word-remix.mp4")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

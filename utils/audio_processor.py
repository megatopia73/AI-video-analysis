import os
import shutil
from pathlib import Path

import yt_dlp
from pydub import AudioSegment

try:
    from imageio_ffmpeg import get_ffmpeg_exe
except ImportError:
    get_ffmpeg_exe = None


def _ffmpeg_path() -> str | None:
    """Return an ffmpeg binary named `ffmpeg` and put it on PATH.

    Whisper and pydub both spawn the command `ffmpeg`. The imageio-ffmpeg
    package ships a binary under a versioned filename, so it is linked to
    `.bin/ffmpeg` and that directory is prepended to PATH.
    """
    found = shutil.which("ffmpeg")
    if found:
        return found
    if get_ffmpeg_exe is None:
        return None

    exe = Path(get_ffmpeg_exe())
    bin_dir = Path(__file__).resolve().parents[1] / ".bin"
    bin_dir.mkdir(exist_ok=True)
    link = bin_dir / "ffmpeg"
    if not link.exists() or link.resolve() != exe.resolve():
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(exe)

    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    return str(link)


FFMPEG = _ffmpeg_path()
if FFMPEG:
    AudioSegment.converter = FFMPEG
    AudioSegment.ffmpeg = FFMPEG

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR,exist_ok = True)

def download_youtube_audio(url :str) ->str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
    }
    if FFMPEG:
        ydl_opts["ffmpeg_location"] = FFMPEG
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info).replace(".webm", ".wav").replace(".m4a", ".wav")
    return filename



def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000) #16khz
    audio.export(output_path, format="wav")
    return output_path



def chunk_audio(wav_path : str , chunk_minutes : int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000 

    chunks = []

    for i, start in enumerate(range(0,len(audio),chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path , format = "wav")

        chunks.append(chunk_path)
    
    return chunks

def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks



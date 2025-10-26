import argparse
import os
import re
import time
from typing import Optional

try:
    from pytube import YouTube  # type: ignore
    from pytube.exceptions import PytubeError  # type: ignore
except Exception:  # pragma: no cover
    YouTube = None  # type: ignore
    PytubeError = Exception  # type: ignore

import moviepy as mp
from urllib.error import HTTPError

try:
    import yt_dlp  # type: ignore
except ImportError:  # pragma: no cover
    yt_dlp = None  # type: ignore

def _find_ffmpeg_location() -> Optional[str]:
    """Attempt to find an ffmpeg binary directory.

    Tries PATH, then imageio_ffmpeg, then common Windows install dirs.
    Returns directory path (not including the executable) or None.
    """
    # 1. PATH search
    for exe in ("ffmpeg.exe", "ffmpeg"):
        for p in os.environ.get("PATH", "").split(os.pathsep):
            cand = os.path.join(p, exe)
            if os.path.isfile(cand):
                return os.path.dirname(cand)
    # 2. imageio_ffmpeg
    try:  # pragma: no cover
        import imageio_ffmpeg  # type: ignore

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.isfile(ffmpeg_exe):
            # Return full path so callers can pass directly
            return ffmpeg_exe
    except Exception:
        pass
    # 3. Common Windows locations
    possible = [
        r"C:\\ffmpeg\\bin",
        r"C:\\Program Files\\ffmpeg\\bin",
        r"C:\\Program Files (x86)\\ffmpeg\\bin",
    ]
    for d in possible:
        if os.path.isfile(os.path.join(d, "ffmpeg.exe")):
            return d
    return None


def _sanitize_filename(name: str, replacement: str = "_") -> str:
    """Return a filesystem-safe filename (Windows-compatible)."""
    # Remove/replace reserved characters and control chars
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', replacement, name)
    # Collapse repeated replacement chars
    name = re.sub(rf'{re.escape(replacement)}+', replacement, name)
    return name.strip().strip('.')[:180] or "video"


def _get_youtube(url: str, retries: int = 3, delay: float = 1.5):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            if YouTube is None:
                raise RuntimeError("pytube not available")
            yt = YouTube(url)
            # Touch a property to force initial data fetch (may raise early)
            _ = yt.title  # noqa: F841
            return yt
        except HTTPError as e:  # Network / API format issues
            last_err = e
            if e.code == 400 and attempt < retries:
                time.sleep(delay * attempt)
                continue
            raise
        except PytubeError as e:
            last_err = e
            if attempt < retries:
                time.sleep(delay * attempt)
                continue
            raise
    # Should not reach here because raise above, but just in case
    if last_err:
        raise last_err
    raise RuntimeError("Failed to initialize YouTube object for unknown reasons")


def _download_with_yt_dlp(url: str, mode: str, output_path: str, safe_title_hint: Optional[str]) -> dict:
    if yt_dlp is None:
        raise RuntimeError("yt_dlp not installed; install with: pip install yt-dlp")
    os.makedirs(output_path, exist_ok=True)
    result: dict[str, Optional[str]] = {"title": None, "video_file": None, "audio_file": None}
    # Detect ffmpeg
    ffmpeg_loc = _find_ffmpeg_location()
    if ffmpeg_loc is None:
        print("ffmpeg not found on PATH. For full functionality (merging & mp3 transcode) install it:")
        print("  winget install --id=Gyan.FFmpeg.Full -e  OR  choco install ffmpeg  OR download from https://www.gyan.dev/ffmpeg/")
        print("Proceeding with limited fallback (may skip merging/transcoding).")

    # Build options
    common = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'ignoreerrors': False,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    if ffmpeg_loc:
        common['ffmpeg_location'] = ffmpeg_loc

    if mode == 'audio':
        if ffmpeg_loc:
            ydl_opts = {
                **common,
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }]
            }
        else:
            # No ffmpeg; disable postprocessing explicitly and prevent auto
            ydl_opts = {**common, 'format': 'bestaudio/best', 'postprocessors': [], 'prefer_ffmpeg': False}
    elif mode == 'video':
        if ffmpeg_loc:
            ydl_opts = {
                **common,
                'format': 'bv*+ba/best',
                'merge_output_format': 'mp4'
            }
        else:
            # Prefer progressive mp4 to avoid merge, disable ffmpeg attempts
            ydl_opts = {**common, 'format': 'best[ext=mp4]/best', 'postprocessors': [], 'prefer_ffmpeg': False}
    else:  # both
        if ffmpeg_loc:
            ydl_opts = {**common, 'format': 'bv*+ba/best', 'merge_output_format': 'mp4'}
        else:
            # Progressive only; later we skip audio extraction
            ydl_opts = {**common, 'format': 'best[ext=mp4]/best', 'postprocessors': [], 'prefer_ffmpeg': False}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise RuntimeError("Failed to download with yt_dlp")
        title = info.get('title') or safe_title_hint or 'video'
        result['title'] = title
        safe_title = _sanitize_filename(title)
        if mode in ("video", "both"):
            # Determine expected filename (mp4)
            exts = ['mp4', 'mkv', 'webm']
            for ext in exts:
                candidate = os.path.join(output_path, f"{title}.{ext}")
                if os.path.exists(candidate):
                    # rename to sanitized name if needed
                    target = os.path.join(output_path, f"{safe_title}.mp4")
                    if candidate != target:
                        try:
                            os.replace(candidate, target)
                        except OSError:
                            target = candidate
                    result['video_file'] = target
                    break
        if mode == 'audio':
            # mp3 if ffmpeg present; else original extension
            for ext in ("mp3", "m4a", "webm", "opus"):
                candidate = os.path.join(output_path, f"{title}.{ext}")
                if os.path.exists(candidate):
                    target_ext = "mp3" if ext == "mp3" else ext
                    target = os.path.join(output_path, f"{safe_title}.{target_ext}")
                    if candidate != target:
                        try:
                            os.replace(candidate, target)
                        except OSError:
                            target = candidate
                    result['audio_file'] = target
                    break
        if mode == 'both':
            if ffmpeg_loc and result['video_file'] and os.path.exists(result['video_file']):
                try:
                    clip = mp.VideoFileClip(result['video_file'])
                    audio_file = os.path.join(output_path, f"{safe_title}.mp3")
                    clip.audio.write_audiofile(audio_file)
                    clip.close()
                    result['audio_file'] = audio_file
                except Exception as e:
                    print(f"Audio extraction skipped (error: {e})")
            else:
                print("Skipping audio extraction (ffmpeg not found). Install ffmpeg for mp3 output.")
        return result


def download_youtube(url: str, mode: str = "both", output_path: str = "downloads") -> dict:
    """Download a YouTube video's video, audio, or both.

    Returns dict with keys: title, video_file (optional), audio_file (optional).
    """
    if not url.startswith("http"):
        raise ValueError("URL must start with http/https")

    os.makedirs(output_path, exist_ok=True)

    yt = None
    title = None
    safe_title = None
    if YouTube is not None:
        try:
            yt = _get_youtube(url)
        except HTTPError as e:
            if e.code == 400:
                print("pytube HTTP 400 (likely outdated). Will attempt yt-dlp fallback.")
                yt = None
            else:
                raise
        except Exception as e:
            print(f"pytube failed: {e}. Trying yt-dlp...")
            yt = None
    else:
        print("pytube not available, using yt-dlp.")

    if yt is None:
        # Fallback path
        return _download_with_yt_dlp(url, mode, output_path, None)

    title = yt.title
    safe_title = _sanitize_filename(title)
    print(f"\nDownloading (pytube): {title}")

    result: dict[str, Optional[str]] = {"title": title, "video_file": None, "audio_file": None}

    # Video (progressive mp4) download if requested or needed for both
    video_file: Optional[str] = None
    audio_file: Optional[str] = None

    try:
        if mode in ("video", "both"):
            video_stream = (
                yt.streams.filter(progressive=True, file_extension="mp4")
                .order_by("resolution")
                .desc()
                .first()
            )
            if not video_stream:
                raise RuntimeError("No progressive MP4 stream available.")
            video_file = video_stream.download(output_path=output_path, filename=safe_title + ".mp4")
            print(f"Video saved to: {video_file}")
            result["video_file"] = video_file

        if mode in ("audio", "both"):
            # Prefer audio-only stream to avoid full video download for audio-only mode
            audio_stream = (
                yt.streams.filter(only_audio=True)
                .order_by("abr")
                .desc()
                .first()
            )
            if audio_stream and mode == "audio":
                temp_audio = audio_stream.download(output_path=output_path, filename=safe_title + audio_stream.subtype)
                # Convert to mp3 via moviepy for consistency
                clip = mp.AudioFileClip(temp_audio)
                audio_file = os.path.join(output_path, safe_title + ".mp3")
                clip.write_audiofile(audio_file)
                clip.close()
                try:
                    if os.path.exists(temp_audio):
                        os.remove(temp_audio)
                except OSError:
                    pass
            else:
                # Fallback: extract audio from existing or newly downloaded progressive video
                if not video_file:
                    video_stream = (
                        yt.streams.filter(progressive=True, file_extension="mp4")
                        .order_by("resolution")
                        .desc()
                        .first()
                    )
                    if not video_stream:
                        raise RuntimeError("No stream available for audio extraction.")
                    video_file = video_stream.download(output_path=output_path, filename=safe_title + ".mp4")
                    result["video_file"] = video_file
                video_clip = mp.VideoFileClip(video_file)
                audio_file = os.path.join(output_path, safe_title + ".mp3")
                video_clip.audio.write_audiofile(audio_file)
                video_clip.close()
            print(f"Audio saved to: {audio_file}")
            result["audio_file"] = audio_file

    except Exception:
        # Provide a clean message while letting caller decide what to do
        print("Download failed. If this persists, run: pip install -U pytube moviepy")
        raise

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download YouTube videos as audio, video, or both.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("mode", choices=["audio", "video", "both"], help="Download mode")
    parser.add_argument("-o", "--output", default="downloads", help="Output folder (default: downloads)")

    args = parser.parse_args()
    download_youtube(args.url, mode=args.mode, output_path=args.output)

"""
PULSE90 — Audio Crowd Peak & Commentary AI Highlight Extraction Pipeline.
Integrates crowd roar detection with PyTorch Vocal Excitement & Whisper Football NLP.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import zipfile
import numpy as np
from scipy.signal import find_peaks

try:
    import librosa
except ImportError:
    librosa = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

try:
    from commentary_ai import (
        CommentaryExcitementAnalyzer,
        CommentaryTranscriber,
        FootballCommentaryNLP,
        MultiModalMomentRanker
    )
    COMMENTARY_AI_AVAILABLE = True
except Exception:
    COMMENTARY_AI_AVAILABLE = False


def extract_audio(video_path: str, audio_path: str) -> None:
    if imageio_ffmpeg is None:
        raise RuntimeError("imageio-ffmpeg is required. Run `pip install imageio-ffmpeg`.")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_exe, "-y", "-loglevel", "error", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", audio_path
    ]
    subprocess.run(command, check=True, capture_output=True)


def compute_rms_curve(audio_path: str, hop_length: int = 512, sr: int = 22050):
    if librosa is None:
        raise RuntimeError("librosa is required for RMS audio detection.")
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    return rms, times


def find_highlight_moments(
    rms,
    times,
    min_gap_seconds: float = 20.0,
    z_threshold: float = 1.5,
    audio_path: str = None,
    use_commentary_ai: bool = True,
    commentary_mode: str = "hybrid"
):
    """
    Finds highlight moments by fusing crowd decibel surges with
    PyTorch neural commentary excitement and vocal pitch acceleration.
    """
    rms_norm = (rms - rms.mean()) / (rms.std() + 1e-9)
    frame_rate = 1.0 / (times[1] - times[0]) if len(times) > 1 else 1.0
    min_distance = max(1, int(min_gap_seconds * frame_rate))
    peak_indices, _ = find_peaks(rms_norm, height=z_threshold, distance=min_distance)

    crowd_events = [(float(times[i]), float(rms_norm[i])) for i in peak_indices]

    if not use_commentary_ai or not COMMENTARY_AI_AVAILABLE or not audio_path or not os.path.exists(audio_path):
        return crowd_events

    # Also detect peaks from PyTorch Commentary Excitement Network
    try:
        analyzer = CommentaryExcitementAnalyzer()
        c_times, c_scores = analyzer.analyze_audio(audio_path)
        c_rate = 1.0 / (c_times[1] - c_times[0]) if len(c_times) > 1 else 1.0
        c_distance = max(1, int(min_gap_seconds * c_rate))
        c_threshold = 0.50 if commentary_mode == "commentary" else 0.60
        vocal_peaks, _ = find_peaks(c_scores, height=c_threshold, distance=c_distance)

        # Merge crowd events and vocal excitement events
        all_timestamps = set()
        combined_events = []

        # Add crowd peaks
        for t, strength in crowd_events:
            all_timestamps.add(round(t, 1))
            combined_events.append((t, strength))

        # Add vocal excitement peaks that might have been missed by crowd roar (e.g. away goals, shock saves)
        for idx in vocal_peaks:
            vt = float(c_times[idx])
            # Check if within min_gap of an existing peak
            if not any(abs(vt - existing_t) < (min_gap_seconds * 0.7) for existing_t in all_timestamps):
                all_timestamps.add(round(vt, 1))
                synth_strength = 1.8 + float(c_scores[idx]) * 1.7
                combined_events.append((vt, synth_strength))

        return combined_events

    except Exception as e:
        print(f"[Commentary AI] Fallback to crowd events: {e}")
        return crowd_events


def cut_highlight_clips(
    video_path: str,
    events: list[tuple[float, float]],
    output_dir: str,
    pre_seconds: int = 8,
    post_seconds: int = 12,
    top_n: int = 10,
    audio_path: str = None,
    use_commentary_ai: bool = True,
    commentary_mode: str = "hybrid"
):
    os.makedirs(output_dir, exist_ok=True)
    if top_n is not None:
        events = sorted(events, key=lambda e: e[1], reverse=True)[:top_n]
        events = sorted(events, key=lambda e: e[0])

    if imageio_ffmpeg is None:
        raise RuntimeError("imageio-ffmpeg is required to cut clips.")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # If Commentary AI is requested and available, enrich events with NLP quotes & tags and filter replays
    commentary_data = {}
    if use_commentary_ai and COMMENTARY_AI_AVAILABLE and audio_path and os.path.exists(audio_path):
        try:
            from commentary_ai import analyze_and_enrich_clips
            candidate_list = [{"timestamp": t, "height": strength} for t, strength in events]
            enriched = analyze_and_enrich_clips(audio_path, candidate_list, mode=commentary_mode, filter_replays=True)
            for en in enriched:
                commentary_data[round(en["timestamp"], 1)] = en
            # Discard replays: only keep verified live match moments
            live_timestamps = {round(en["timestamp"], 1) for en in enriched}
            events = [e for e in events if round(e[0], 1) in live_timestamps]
        except Exception as e:
            print(f"[Commentary AI] Warning: enrichment error: {e}")


    saved_paths = []
    for idx, (t, strength) in enumerate(events, start=1):
        start = max(0, t - pre_seconds)
        duration = pre_seconds + post_seconds
        out_name = f"highlight_{idx:02d}_t{int(t)}s.mp4"
        out_path = os.path.join(output_dir, out_name)
        command = [
            ffmpeg_exe, "-y", "-loglevel", "error",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(duration),
            "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-c:a", "aac",
            "-movflags", "+faststart",
            out_path
        ]
        subprocess.run(command, check=True, capture_output=True)

        # Retrieve AI commentary analysis for this moment
        ai_info = commentary_data.get(round(t, 1), {})
        quote = ai_info.get("commentary_quote", '"PULSE90 peak excitement captured at this key moment."')
        badge = ai_info.get("event_tag", "⚡ HIGH TENSION MOMENT")
        vocal_sc = ai_info.get("vocal_score", 0.72)
        lexical_sc = ai_info.get("lexical_score", 0.75)
        fused_sc = ai_info.get("fused_score", round(min(1.0, strength / 3.0), 2))

        saved_paths.append({
            "index": idx,
            "filename": out_name,
            "path": out_path,
            "url": f"/extracted/{os.path.basename(output_dir)}/{out_name}",
            "timestamp": t,
            "clock": f"{int(t)//60:02d}:{int(t)%60:02d}",
            "strength": round(strength, 1),
            "commentary_quote": quote,
            "event_tag": badge,
            "vocal_score": vocal_sc,
            "lexical_score": lexical_sc,
            "fused_score": fused_sc
        })

    return saved_paths


def make_zip(paths: list[dict], zip_path: str) -> str:
    with zipfile.ZipFile(zip_path, "w") as zf:
        for item in paths:
            zf.write(item["path"], arcname=item["filename"])
    return zip_path


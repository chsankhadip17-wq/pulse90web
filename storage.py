"""
Storage module for PULSE90:
- Exclusively serves the 5 flow videos for background scroll.
- Manages user highlight records and history storage (from project high).
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
FLOW_DIR = os.path.join(BASE_DIR, "assets", "videos", "google_flow")

# --------------------------------------------------------------------------
# Flow Videos (Exclusively for Scrolling Background)
# --------------------------------------------------------------------------
FLOW_METADATA = [
    {
        "index": 1,
        "filename": "01_neon_waveform_crowd.mp4",
        "url": "/assets/videos/google_flow/01_neon_waveform_crowd.mp4",
        "title": "THE CROWD KNOWS BEFORE YOU DO",
        "subtitle": "STADIUM CROWD • NEON WAVEFORM",
        "quote": "PULSE90 was built on an acoustic truth: 80,000 spectators anticipate the goal before any computer vision model can. We tap directly into the crowd roar.",
    },
    {
        "index": 2,
        "filename": "02_captain_tunnel.mp4",
        "url": "/assets/videos/google_flow/02_captain_tunnel.mp4",
        "title": "CONTINUOUS AUDIO SCAN",
        "subtitle": "STEP 01 • 44.1kHz STREAM EXTRACTION",
        "quote": "When a match video is uploaded, our pipeline extracts pure 44.1kHz audio, scanning 90 minutes acoustically 100× faster than visual frame processing.",
    },
    {
        "index": 3,
        "filename": "03_boots_step_over.mp4",
        "url": "/assets/videos/google_flow/03_boots_step_over.mp4",
        "title": "RMS ENERGY SPECTROGRAM",
        "subtitle": "STEP 02 • LIBROSA ROLLING WINDOWS",
        "quote": "Using Librosa signal processing, we track Root Mean Square (RMS) energy across the match. Gameplay hum is smoothed while decibel surges spike.",
    },
    {
        "index": 4,
        "filename": "04_scoring_net.mp4",
        "url": "/assets/videos/google_flow/04_scoring_net.mp4",
        "title": "Z-SCORE PEAK DETECTION",
        "subtitle": "STEP 03 • STATISTICAL FILTERING",
        "quote": "Scipy signal algorithms apply adaptive z-score normalization (Z > 1.5), filtering commentary chatter and flagging the exact seconds of match-defining strikes.",
    },
    {
        "index": 5,
        "filename": "05_celebrating_knee_slide.mp4",
        "url": "/assets/videos/google_flow/05_celebrating_knee_slide.mp4",
        "title": "SURGICAL REEL CUTTING",
        "subtitle": "STEP 04 • FFmpeg PRECISION SLICING",
        "quote": "FFmpeg buffers 8s of pre-strike buildup and 12s of celebration euphoria, slicing surgical MP4 clips with zero re-encoding loss into an instant highlight reel.",
    },
]


def get_flow_videos() -> list[dict]:
    return FLOW_METADATA


def get_all_videos() -> list[dict]:
    return get_flow_videos()


# --------------------------------------------------------------------------
# User Highlight History & Records (Project High Workflow)
# --------------------------------------------------------------------------
def _ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def _load_history() -> dict:
    _ensure_dirs()
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_history(history: dict) -> None:
    _ensure_dirs()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_user_history(username: str) -> list[dict]:
    history = _load_history()
    raw_entries = history.get(username, [])
    formatted = []
    for entry in raw_entries:
        entry_id = entry.get("id", "")
        clips = entry.get("clips", [])
        clip_details = entry.get("clip_details", {})
        
        # Build playable URLs
        clip_objs = []
        for idx, cname in enumerate(clips, start=1):
            detail = clip_details.get(cname, {})
            clip_objs.append({
                "index": idx,
                "filename": cname,
                "url": f"/uploads/{username}/{entry_id}/{cname}",
                "commentary_quote": detail.get("commentary_quote", '"PULSE90 highlight moment."'),
                "event_tag": detail.get("event_tag", "⚡ MATCH HIGHLIGHT"),
                "fused_score": detail.get("fused_score", None)
            })
            
        zip_filename = "highlights.zip"
        formatted.append({
            "id": entry_id,
            "timestamp": entry.get("timestamp", time.time()),
            "date_str": time.strftime("%d %b %Y, %H:%M", time.localtime(entry.get("timestamp", time.time()))),
            "source_filename": entry.get("source_filename", "match.mp4"),
            "settings": entry.get("settings", {}),
            "clips": clip_objs,
            "zip_url": f"/uploads/{username}/{entry_id}/{zip_filename}",
        })
    return formatted


def add_history_entry(username: str, source_filename: str, settings: dict, clip_items: list) -> str:
    _ensure_dirs()
    entry_id = uuid.uuid4().hex[:10]
    user_dir = os.path.join(UPLOADS_DIR, username, entry_id)
    os.makedirs(user_dir, exist_ok=True)

    saved_clip_names = []
    clip_details = {}
    for item in clip_items:
        if isinstance(item, dict):
            path = item.get("path", "")
            cname = os.path.basename(path)
            clip_details[cname] = {
                "commentary_quote": item.get("commentary_quote", ""),
                "event_tag": item.get("event_tag", ""),
                "fused_score": item.get("fused_score", None)
            }
        else:
            path = str(item)
            cname = os.path.basename(path)

        if os.path.exists(path):
            dest = os.path.join(user_dir, cname)
            shutil.copy2(path, dest)
            saved_clip_names.append(cname)

    # Create zip archive in user_dir
    zip_path = os.path.join(user_dir, "highlights.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name in saved_clip_names:
            p = os.path.join(user_dir, name)
            if os.path.exists(p):
                zf.write(p, arcname=name)

    history = _load_history()
    history.setdefault(username, [])
    rel_clip_dir = os.path.join("data", "uploads", username, entry_id)
    history[username].insert(0, {
        "id": entry_id,
        "timestamp": time.time(),
        "source_filename": source_filename,
        "settings": settings,
        "clip_dir": rel_clip_dir,
        "clips": saved_clip_names,
        "clip_details": clip_details
    })
    _save_history(history)
    return entry_id



def delete_history_entry(username: str, entry_id: str) -> bool:
    history = _load_history()
    entries = history.get(username, [])
    remaining = []
    deleted = False
    for entry in entries:
        if entry.get("id") == entry_id:
            user_entry_dir = os.path.join(UPLOADS_DIR, username, entry_id)
            shutil.rmtree(user_entry_dir, ignore_errors=True)
            if "clip_dir" in entry and os.path.isabs(entry["clip_dir"]) and os.path.exists(entry["clip_dir"]):
                shutil.rmtree(entry["clip_dir"], ignore_errors=True)
            deleted = True
        else:
            remaining.append(entry)
    history[username] = remaining
    _save_history(history)
    return deleted


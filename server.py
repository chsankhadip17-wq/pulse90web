"""
Async server for PULSE90 Scrolling Website & Highlight Extraction.
Includes authentication and highlight history records from project high.
"""

from __future__ import annotations

import os
import sys
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

import auth
import storage
import extractor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
FLOW_DIR = os.path.join(BASE_DIR, "assets", "videos", "google_flow")
EXTRACTED_DIR = os.path.join(BASE_DIR, "data", "extracted")
UPLOADS_DIR = os.path.join(BASE_DIR, "data", "uploads")
os.makedirs(EXTRACTED_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)


async def serve_index(request):
    return FileResponse(INDEX_FILE)


async def api_get_videos(request):
    videos = storage.get_flow_videos()
    return JSONResponse({"status": "success", "videos": videos})


# --------------------------------------------------------------------------
# Authentication (From Project High)
# --------------------------------------------------------------------------
async def api_auth_signin(request):
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        ok, msg = auth.sign_in(username, password)
        if ok:
            return JSONResponse({"status": "success", "message": msg, "username": username})
        return JSONResponse({"status": "error", "message": msg}, status_code=401)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


async def api_auth_signup(request):
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        confirm = data.get("confirm_password", "")
        if confirm and password != confirm:
            return JSONResponse({"status": "error", "message": "Passwords do not match."}, status_code=400)
        ok, msg = auth.sign_up(username, password)
        if ok:
            return JSONResponse({"status": "success", "message": msg, "username": username})
        return JSONResponse({"status": "error", "message": msg}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


# --------------------------------------------------------------------------
# Highlight Records & History (From Project High)
# --------------------------------------------------------------------------
async def api_get_history(request):
    username = request.query_params.get("username", "").strip()
    if not username:
        return JSONResponse({"status": "error", "message": "Username required"}, status_code=400)
    history = storage.get_user_history(username)
    return JSONResponse({"status": "success", "username": username, "records": history})


async def api_delete_history(request):
    username = request.query_params.get("username", "").strip()
    entry_id = request.query_params.get("id", "").strip()
    if not username or not entry_id:
        return JSONResponse({"status": "error", "message": "Username and Entry ID required"}, status_code=400)
    deleted = storage.delete_history_entry(username, entry_id)
    return JSONResponse({"status": "success" if deleted else "error", "deleted": deleted})


# --------------------------------------------------------------------------
# Highlight Extraction Pipeline
# --------------------------------------------------------------------------
async def api_extract_highlights(request):
    try:
        form = await request.form()
        video_file = form.get("video")
        if not video_file:
            return JSONResponse({"status": "error", "message": "No match video uploaded."}, status_code=400)

        username = form.get("username", "").strip()
        sensitivity = float(form.get("sensitivity", 1.5))
        pre_seconds = int(form.get("pre_seconds", 8))
        post_seconds = int(form.get("post_seconds", 12))
        top_n = int(form.get("max_clips", 10))
        min_gap = float(form.get("min_gap", 20))
        sensitivity_label = form.get("sensitivity_label", "⚖️ Balanced")
        length_label = form.get("length_label", "🎬 Standard highlight")
        use_commentary_ai = form.get("use_commentary_ai", "true").lower() in ("true", "1", "yes")
        commentary_mode = form.get("commentary_mode", "hybrid").strip().lower()

        session_id = os.urandom(6).hex()
        session_dir = os.path.join(EXTRACTED_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)

        input_video_path = os.path.join(session_dir, video_file.filename)
        with open(input_video_path, "wb") as f:
            f.write(await video_file.read())

        audio_path = os.path.join(session_dir, "audio.wav")
        clips_dir = os.path.join(session_dir, "clips")

        # 1. Extract audio
        extractor.extract_audio(input_video_path, audio_path)

        # 2. Compute RMS curve
        rms, times = extractor.compute_rms_curve(audio_path)

        # 3. Find peaks (Acoustic crowd roar + PyTorch vocal excitement)
        events = extractor.find_highlight_moments(
            rms, times,
            min_gap_seconds=min_gap,
            z_threshold=sensitivity,
            audio_path=audio_path,
            use_commentary_ai=use_commentary_ai,
            commentary_mode=commentary_mode
        )

        if not events:
            return JSONResponse({
                "status": "success",
                "clips": [],
                "message": "No highlight-worthy moments detected with this sensitivity. Try setting sensitivity to 'Catch everything loud' or switching to Commentary Priority."
            })

        # 4. Cut highlight clips and enrich with Commentary AI (Whisper NLP + PyTorch Arousal)
        saved_clips = extractor.cut_highlight_clips(
            input_video_path, events, clips_dir,
            pre_seconds=pre_seconds, post_seconds=post_seconds, top_n=top_n,
            audio_path=audio_path,
            use_commentary_ai=use_commentary_ai,
            commentary_mode=commentary_mode
        )

        # 5. Create ZIP archive
        zip_path = os.path.join(session_dir, "highlights.zip")
        extractor.make_zip(saved_clips, zip_path)

        for c in saved_clips:
            c["url"] = f"/extracted/{session_id}/clips/{c['filename']}"

        # 6. Save to User History if user is provided
        record_id = None
        if username:
            settings = {
                "sensitivity": sensitivity_label,
                "clip_length": length_label,
                "commentary_ai": "Enabled" if use_commentary_ai else "Disabled",
                "commentary_mode": commentary_mode.capitalize()
            }
            record_id = storage.add_history_entry(
                username=username,
                source_filename=video_file.filename,
                settings=settings,
                clip_items=saved_clips
            )


        return JSONResponse({
            "status": "success",
            "session_id": session_id,
            "record_id": record_id,
            "clips": saved_clips,
            "zip_url": f"/extracted/{session_id}/highlights.zip",
            "message": f"Successfully extracted {len(saved_clips)} match highlights!"
        })

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


routes = [
    Route("/", serve_index),
    Route("/api/videos", api_get_videos, methods=["GET"]),
    Route("/api/auth/signin", api_auth_signin, methods=["POST"]),
    Route("/api/auth/signup", api_auth_signup, methods=["POST"]),
    Route("/api/history", api_get_history, methods=["GET"]),
    Route("/api/history/entry", api_delete_history, methods=["DELETE"]),
    Route("/api/extract", api_extract_highlights, methods=["POST"]),
    Mount("/assets", StaticFiles(directory=os.path.join(BASE_DIR, "assets")), name="assets"),
    Mount("/styles", StaticFiles(directory=os.path.join(BASE_DIR, "styles")), name="styles"),
    Mount("/js", StaticFiles(directory=os.path.join(BASE_DIR, "js")), name="js"),
    Mount("/extracted", StaticFiles(directory=EXTRACTED_DIR), name="extracted"),
    Mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads"),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    print(">> Starting PULSE90 on http://localhost:8080 ...")
    uvicorn.run("server:app", host="127.0.0.1", port=8080, reload=False, log_level="info")

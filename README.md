# PULSE90 — Cinematic Scrolling Motion Website & Video Studio

> *"The crowd knows the moment before you do."*

A high-performance **scrolling motion web experience** designed for football highlight reels and Google Flow AI-generated video storytelling.

---

## ⚡ Quick Start

### 1. Launch the Website
Double-click `start.bat` or run in your terminal:
```powershell
python server.py
```
Open your browser at:
👉 **[http://localhost:8080](http://localhost:8080)**

---

## 🎥 Google Flow Videos Integration

Google Flow (`flow.google`) is Google's creative AI video filmmaking studio (using Veo and Gemini).

Because Google Flow runs in your private Google Account cloud, you can seamlessly feature your generated videos on this website through **either** of these two methods:

### Method 1: Drop Files into the Folder (Recommended)
Simply copy or move your exported `.mp4`, `.mov`, or `.webm` files into:
📁 `pulse90-scrolling-web/assets/videos/google_flow/`

The website automatically detects new files and showcases them in the interactive scrolling video reel with the **`GOOGLE FLOW`** AI badge.

### Method 2: Use the In-Browser Uploader
Click the **`+ Import Flow Video`** button in the top navigation bar of the website. Drag and drop any video generated from your Google Flow account, and it will immediately be added to your live motion showcase without restarting the server.

---

## 🌟 Key Features

1. **Lenis Momentum Scrolling**: Buttery smooth 60fps scrolling motion throughout the entire experience.
2. **GSAP ScrollTrigger**: Pinned narrative cards, text parallax reveals, and scroll-linked video cards.
3. **Live Audio Spectrogram**: Dynamic HTML5 Canvas waveform simulating stadium crowd decibels and roar peaks.
4. **Cinematic Video Lightbox**: Click any video card to launch full theater playback with time scrubbing, download options, and high-bitrate streaming (HTTP 206 Partial Content).
5. **Real-Time Football News Ticker**: Seamless infinite marquee banner pulling live football stories directly from BBC Sport.
6. **Authentication & User History**: Lightweight local JSON auth system preserved from your original PULSE90 files.

---

## 📂 Project Structure

```
pulse90-scrolling-web/
├── index.html                 # Main scrolling motion experience
├── styles/
│   └── main.css              # Dark pitch palette, floodlight glows, Anton typography
├── js/
│   ├── motion.js             # GSAP ScrollTrigger & Lenis smooth scroll orchestrator
│   ├── player.js             # Cinema video lightbox & drag-and-drop upload modal
│   └── app.js                # Dynamic video reel rendering, news ticker & auth
├── assets/
│   └── videos/
│       ├── google_flow/      # Drop your Google Flow AI generated clips here
│       └── highlights/       # PULSE90 crowd roar highlight clips
├── data/
│   ├── history.json          # User extraction sessions
│   └── users.json            # User credentials (PBKDF2 salted hash)
├── server.py                 # Starlette + Uvicorn async streaming web server
├── auth.py                   # Authentication module
├── news.py                   # BBC Sport live RSS fetcher
├── storage.py                # Video directory scanner and user storage
└── start.bat                 # One-click Windows launcher
```

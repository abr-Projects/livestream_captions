# Live Stream with Subtitles

This project creates a live streaming transcription service that displays real-time subtitles on a video stream. It uses Flask with Flask-SocketIO as the backend, integrates Faster-Whisper for on-the-fly audio transcription, and employs FFmpeg for video chunk processing. The provided HTML/JavaScript frontend allows users to configure the stream URL, language options, chunk length, and buffering parameters.

## Overview

The system downloads a livestream in sequential video chunks, transcribes each chunk using the Faster-Whisper ASR engine, and then transforms the video segment before serving it to the client. Transcription segments (with timestamps) are emitted via Socket.IO so that the client can render subtitles in sync with video playback.

Key components:
- **Backend (Python):**  
  - A Flask app serving the video and handling real-time events via Socket.IO.  
  - A custom class (`FasterWhisperASR`) that initializes a Whisper model and transcribes audio segments.
  - A pipeline that downloads chunks (using yt-dlp), processes them with FFmpeg, and performs transcription.
  - Optional translation and language detection settings.
- **Frontend (HTML/JS):**  
  - A simple, responsive GUI that lets users input the livestream URL, select language and translation options, and configure chunk length and buffering.
  - A video element that plays the processed stream and a subtitle panel that displays real-time transcription updates.
  - JavaScript code that handles media buffering via the MediaSource API and coordinates with the backend via Socket.IO.

## Features

- **Real-time Transcription:** Process livestreams in near real-time with reduced latency.
- **Multi-Language Support:** Choose the original language or let the model auto-detect; optionally translate the transcript.
- **Customizable Processing:** Adjust chunk length and buffering settings for performance tuning.
- **Seamless Video Playback:** Chunks are appended to a MediaSource object, ensuring smooth video playback.
- **Parallel Processing:** The backend pipeline can be adapted to pipeline download and processing tasks concurrently.

## Installation

### Prerequisites
- Python 3.8+
- CUDA-compatible GPU with appropriate drivers (if running inference on GPU)
- [FFmpeg](https://ffmpeg.org/) installed and accessible in your system's PATH.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) installed (e.g., via `pip install yt-dlp`).

### Python Dependencies

Install required Python packages using pip:

```bash
pip install flask flask-socketio faster-whisper

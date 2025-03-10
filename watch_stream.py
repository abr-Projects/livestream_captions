import os
import subprocess
import threading
import queue
import concurrent.futures
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
from faster_whisper import WhisperModel
import logging

class FasterWhisperASR:
    def __init__(self, lan, modelsize=None, translate_to=None):
        self.translate_to = translate_to
        self.model = WhisperModel(modelsize, device="cuda", compute_type="float16")
        self.original_language = None if lan == "auto" else lan

    def transcribe(self, audio):
        task = "translate" if self.translate_to else "transcribe"
        segments, _ = self.model.transcribe(
            audio,
            language=self.original_language,
            beam_size=1,
            word_timestamps=False,
            condition_on_previous_text=True,
            task=task
        )
        return [(segment.start, segment.end, segment.text) for segment in segments]

time_format = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt=time_format)
logger = logging.getLogger('custom_logger')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.CRITICAL)

app = Flask(__name__)
socketio = SocketIO(app)
asr = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chunks/<path:filename>")
def serve_video(filename):
    return send_from_directory("chunks", filename)

@socketio.on("connect")
def handle_connect():
    print("Client connected")

@socketio.on("start_stream")
def handle_start_stream(data):
    global asr
    stream_url = data["streamUrl"]
    language = data["language"]
    translation = data["translation"]
    chunk_length = int(data["chunkLength"])
    
    asr = FasterWhisperASR(
        lan=language,
        modelsize="medium",
        translate_to=translation if translation != "none" else None
    )
    
    socketio.start_background_task(main, stream_url, chunk_length)

def download(url, out, duration=30):
    command = [
        "yt-dlp",
        url,
        "--cookies", "cookies.txt",
        "--no-live-from-start",
        "--no-part",
        "--quiet",
        "--no-warnings",
        "--no-progress",
        "-f", "bv*+ba/b",
        "-o", out,
        "--external-downloader", "ffmpeg",
        "--external-downloader-args", f"-t {duration}"
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error downloading chunk: {e}")
        raise

def transform(inp, out):
    segment_command = [
        "ffmpeg",
        "-y",
        "-loglevel", "panic",
        "-i", inp,
        "-c", "copy",
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "-reset_timestamps", "1",
        "-avoid_negative_ts", "make_zero",
        "-f", "mp4",
        out
    ]
    subprocess.run(segment_command, check=True)

def transcribe_chunk(chunk_index, raw_file, chunk_length, transformation_queue):
    logger.debug(f"Chunk {chunk_index}: Transcribing {raw_file}")
    segments = asr.transcribe(raw_file)
    logger.debug(f"Chunk {chunk_index}: Transcript Segments: {segments}")

    transformation_queue.put((chunk_index, raw_file, segments, chunk_length))

def transform_chunk(chunk_index, raw_file, segments, chunk_length):
    transformed = f"chunks/chunk_{chunk_index}.mp4"
    logger.debug(f"Chunk {chunk_index}: Transforming {raw_file} -> {transformed}")
    
    transform(raw_file, transformed)

    socketio.emit("transcript_update", {
        "segments": segments,
        "chunk_index": chunk_index,
        "chunk_length": chunk_length
    })

    os.remove(raw_file)
    logger.debug(f"Chunk {chunk_index}: Processing complete")

def main(stream_url, chunk_length):
    index = 0
    if os.path.exists("chunks"):
        for file in os.listdir("chunks"):
            os.remove(os.path.join("chunks", file))
    else:
        os.mkdir("chunks")

    transcription_queue = queue.Queue()   
    transformation_queue = queue.Queue()  
    def downloader():
        nonlocal index
        while True:
            raw_file = f"chunks/raw_chunk_{index}.mp4"
            logger.debug(f"Downloader: Downloading chunk {index} to {raw_file}")
            download(stream_url, raw_file, duration=chunk_length)
            logger.debug(f"Downloader: Downloaded chunk {index}")
            transcription_queue.put((index, raw_file))   
            index += 1

    download_thread = threading.Thread(target=downloader, daemon=True)
    download_thread.start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as transcription_executor, \
         concurrent.futures.ThreadPoolExecutor(max_workers=4) as transformation_executor:

        while True:
            try:
 
                chunk_index, raw_file = transcription_queue.get(timeout=chunk_length * 2)
                transcription_executor.submit(transcribe_chunk, chunk_index, raw_file, chunk_length, transformation_queue)
            except queue.Empty:
                pass

            try:
  
                chunk_index, raw_file, segments, chunk_length = transformation_queue.get(timeout=chunk_length * 2)
                transformation_executor.submit(transform_chunk, chunk_index, raw_file, segments, chunk_length)
            except queue.Empty:
                pass

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5100)

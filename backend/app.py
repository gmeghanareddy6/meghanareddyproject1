import os
import json
import traceback
import time
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

import PyPDF2
from pptx import Presentation
from PIL import Image
import io
import yt_dlp

import logging
from ml_pipeline import get_pipeline

# -------------------- SETUP --------------------
logging.basicConfig(filename='backend_errors.log', level=logging.ERROR, 
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Trusted YouTube channels (Refined List for Academic Context)
TRUSTED_CHANNELS = [
    "Neso Academy", "Abdul Bari", "Jenny's Lectures CS IT", "freeCodeCamp.org",
    "CS Dojo", "Traversy Media", "Fireship", "Programming with Mosh",
    "Khan Academy", "mitocw", "StatQuest with Josh Starmer", "3Blue1Brown",
    "The Coding Train", "Sentdex", "Corey Schafer", "Tech With Tim",
    "Web Dev Simplified", "Amigoscode", "Kevin Powell", "Net Ninja",
    "Academind", "Harvard University", "Stanford Online", "CrashCourse",
    "Kurzgesagt – In a Nutshell", "Veritasium", "Vsauce", "Computerphile", "Numberphile"
]

# -------------------- HELPER FUNCTIONS --------------------

def extract_content_from_file(file):
    """
    Extracts text from PDF, PPTX.
    Note: Image processing is disabled as we moved from Gemini (Multimodal) to local Text models.
    """
    filename = file.filename.lower()
    text = ""
    is_image = False
    
    try:
        if filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        
        elif filename.endswith('.pptx'):
            prs = Presentation(file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
        
        elif filename.endswith('.txt'):
            text = file.read().decode('utf-8')

        elif filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            is_image = True
            
    except Exception as e:
        print(f"File extraction error: {e}")
        return None, False

    return text.strip(), is_image

def get_youtube_video(query):
    """
    Searches YouTube for the query and returns the BEST result based on ranking.
    Uses yt-dlp for robust searching.
    """
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch5:{query}"
            info = ydl.extract_info(search_query, download=False)
            
            best_video = None
            highest_score = -1

            if 'entries' in info:
                for video in info['entries']:
                    score = 0
                    channel_name = video.get('uploader', '')
                    title = video.get('title', '').lower()
                    duration_seconds = video.get('duration')

                    if any(trusted.lower() in channel_name.lower() for trusted in TRUSTED_CHANNELS):
                        score += 10
                    
                    if any(keyword in title for keyword in ["tutorial", "course", "lecture", "explained", "crash course", "introduction", "learn"]):
                        score += 5
                    
                    if duration_seconds:
                        try:
                            seconds = int(duration_seconds)
                            minutes = seconds / 60
                            if minutes >= 3 and minutes <= 60:
                                score += 3
                            elif minutes < 2:
                                score -= 5
                        except:
                            pass
                    
                    if score > highest_score:
                        highest_score = score
                        best_video = video
            
            if best_video:
                return {
                    "id": best_video['id'],
                    "title": best_video['title'],
                    "link": best_video.get('url', f"https://www.youtube.com/watch?v={best_video['id']}"),
                    "thumbnail": best_video.get('thumbnail') or f"https://img.youtube.com/vi/{best_video['id']}/mqdefault.jpg",
                    "channel": best_video.get('uploader'),
                    "duration": f"{int(best_video.get('duration', 0)//60)}:{int(best_video.get('duration', 0)%60):02d}"
                }
    except Exception as e:
        print(f"YouTube Search Error for '{query}': {e}")
    
    return {
        "id": None,
        "title": f"Search: {query}",
        "link": f"https://www.youtube.com/results?search_query={query}",
        "thumbnail": "https://img.youtube.com/vi/mq5-7/mqdefault.jpg",
        "channel": "YouTube",
        "duration": "N/A"
    }

from youtube_transcript_api import YouTubeTranscriptApi

def extract_transcript(youtube_url):
    """
    Extracts the transcript from a YouTube video natively if available.
    """
    try:
        video_id = youtube_url.split("v=")[1].split("&")[0]
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except:
            transcript = next(iter(transcript_list))
            
        full_transcript = transcript.fetch()
        text = " ".join([entry['text'] for entry in full_transcript])
        return text
    except Exception as e:
        print(f"Transcript Error: {e}")
        return None

def download_youtube_audio(youtube_url):
    """
    Downloads ONLY the audio from a YouTube video to save bandwidth/processing.
    """
    print(f"Downloading audio from {youtube_url}...")
    if not os.path.exists("temp"):
        os.makedirs("temp")
        
    timestamp = int(time.time())
    output_template = os.path.join("temp", f"yt_{timestamp}_%(id)s.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            # The actual file saved will end in .wav because of the postprocessor
            base_filename = ydl.prepare_filename(info)
            wav_filename = os.path.splitext(base_filename)[0] + ".wav"
            print(f"Audio downloaded to: {wav_filename}")
            if os.path.exists(wav_filename):
                 return wav_filename
            return base_filename # Fallback if postprocessor failed
    except Exception as e:
        print(f"yt-dlp Audio Download Error: {e}")
        raise e

def extract_audio_and_transcribe(video_path):
    """
    Extracts audio from a local video file (MP4, etc.) and transcribes it using Whisper.
    """
    audio_path = video_path + ".wav"
    try:
        print(f"Extracting Audio from {video_path} to {audio_path}...")
        subprocess.run(["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y", "-hide_banner", "-loglevel", "error"], check=True)
        pipe = get_pipeline()
        print("Transcribing with Local Whisper Model...")
        return pipe.transcribe_audio(audio_path)
    except Exception as e:
         print(f"Extraction/Transcription error: {e}")
         return None
    finally:
         if os.path.exists(audio_path):
             os.remove(audio_path)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Backend running", "mode": "Local Machine Learning Models"})

# -------------------- MAIN API --------------------

@app.route("/api/summarize", methods=["POST"])
def summarize_and_recommend():
    try:
        # Load models dynamically (lazy loading) if not already loaded
        pipe = get_pipeline()
        
        # 1. PARSE INPUT
        text_content = request.form.get("text", "").strip()
        youtube_url = request.form.get("youtube_url", "").strip()
        file = request.files.get("file")
        
        final_text_content = ""

        if youtube_url:
            print(f"Processing YouTube URL: {youtube_url}")
            transcript_text = extract_transcript(youtube_url)
            
            if transcript_text:
                final_text_content = transcript_text
            else:
                print("Transcript missing. Downloading audio and running through Whisper locally...")
                audio_path = None
                try:
                    audio_path = download_youtube_audio(youtube_url)
                    # For youtube downloads that were already converted to wav by yt-dlp
                    if audio_path.endswith('.wav'):
                         final_text_content = pipe.transcribe_audio(audio_path)
                    else:
                         final_text_content = extract_audio_and_transcribe(audio_path)
                         
                    if not final_text_content:
                        raise ValueError("Whisper failed to transcribe audio.")
                    
                except Exception as e:
                    print(f"YouTube Local Fallback Error: {e}")
                    return jsonify({"error": f"Could not transcribe video: {str(e)}"}), 400
                finally:
                    if audio_path and os.path.exists(audio_path):
                        try:
                            os.remove(audio_path)
                        except:
                            pass

        elif file:
            filename = file.filename.lower()
            if filename.endswith(('.mp4', '.mov', '.avi', '.mpeg', '.mpg', '.webm', '.wmv', '.3gp')):
                # VIDEO UPLOAD LOGIC
                temp_path = None
                try:
                    if not os.path.exists("temp"):
                        os.makedirs("temp")

                    safe_name = "".join([c for c in filename if c.isalnum() or c in "._-"])
                    temp_path = os.path.join("temp", safe_name)
                    file.save(temp_path)
                    print(f"Video saved to {temp_path}")

                    # Use Whisper Locally
                    final_text_content = extract_audio_and_transcribe(temp_path)
                    if not final_text_content:
                         return jsonify({"error": "Failed to extract or transcribe audio from the video."}), 400
                    
                except Exception as e:
                    print(f"Video Upload Error: {str(e)}")
                    raise ValueError(f"Video Error: {str(e)}")
                    
                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
            
            else:
                # DOCUMENT (PDF/PPTX) LOGIC
                extracted_text, is_img = extract_content_from_file(file)
                if is_img:
                    return jsonify({"error": "Image processing is not supported in the local text-based ML pipeline. Please upload documents or videos."}), 400
                elif extracted_text:
                    final_text_content = extracted_text
                else:
                     return jsonify({"error": "Could not extract text from file."}), 400
                     
        elif text_content:
            final_text_content = text_content
            
        else:
            return jsonify({"error": "No content provided. Upload a file, paste text, or provide a YouTube URL."}), 400

        # 2. LOCAL AI PROCESSING
        print("Generating Summary with Local BART Model...")
        text_len = len(final_text_content)
        is_extensive = text_len > 5000
        
        # Dynamic proportional length scaling based on input length
        if text_len < 300:
            req_max_len = 45
            req_min_len = 15
        elif text_len < 1200:
            req_max_len = 90
            req_min_len = 35
        elif text_len < 4000:
            req_max_len = 180
            req_min_len = 65
        elif text_len < 10000:
            req_max_len = 280
            req_min_len = 100
        else:
            req_max_len = 350
            req_min_len = 130
            
        summary_text = pipe.summarize_text(final_text_content, max_length=req_max_len, min_length=req_min_len)
        
        # Split into bullet points by sentence (filter out short fragments < 20 chars)
        raw_sentences = [s.strip() for s in summary_text.replace(".\n", ". ").replace("\n", " ").split(".") if len(s.strip()) > 20]
        
        # Deduplicate while maintaining order
        sentences = []
        seen = set()
        for s in raw_sentences:
            s_clean = s.strip()
            if s_clean.lower() not in seen:
                seen.add(s_clean.lower())
                sentences.append(s_clean + ".")

        if not sentences:
             sentences = [summary_text + "." if not summary_text.endswith(".") else summary_text]

        pdf_notice = None
        if is_extensive or len(sentences) > 10:
            pdf_notice = "📄 Content exceeds standard display range. For total complete information, please download the full PDF report below!"
            sentences.append("ℹ️ Note: For total complete information and full details, please download the full PDF report below!")

        print("Extracting Keywords with Local KeyBERT...")
        # Get keywords/cognitive gaps
        cognitive_gaps = pipe.extract_keywords(final_text_content, top_n=6)

        # 3. ENRICH WITH REAL YOUTUBE DATA
        for gap in cognitive_gaps:
            query = gap["youtube_query"]
            video_data = get_youtube_video(query)
            gap["video"] = video_data

        # 4. RETURN RESULT
        result_json = {
            "summary": sentences,
            "cognitive_gaps": cognitive_gaps,
            "is_extensive": is_extensive,
            "pdf_notice": pdf_notice
        }

        return jsonify(result_json)

    except Exception as e:
        traceback_str = traceback.format_exc()
        print("SERVER ERROR:", traceback_str)
        logging.error(traceback_str)
        return jsonify({"error": f"Processing Failed: {str(e)}", "details": traceback_str}), 500

if __name__ == "__main__":
    # Pre-load ML models before app starts serving requests
    print("Pre-loading machine learning models into memory...")
    get_pipeline()
    app.run(host="127.0.0.1", port=5000, debug=True)

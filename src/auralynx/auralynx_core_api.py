#!/usr/bin/env python3
"""
Auralynx Core API wrapper for AssemblyAI

- API key diambil dari environment variable AAI_API_KEY
- Upload streaming per chunk
"""

import requests
import time
import json
import sys
import os
from argparse import ArgumentParser

UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"

CHUNK_SIZE = 5242880  # 5 MB

def get_api_key():
    key = os.environ.get("AAI_API_KEY")
    if not key:
        print("ERROR: AAI_API_KEY environment variable is not set.")
        print("Set it with: export AAI_API_KEY=\"your_key_here\"")
        sys.exit(2)
    return key

def upload_file(audio_file, api_key):
    print(f"Uploading {audio_file} ...")
    headers = {"authorization": api_key}
    try:
        with open(audio_file, "rb") as f:
            def gen():
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
            resp = requests.post(UPLOAD_URL, headers=headers, data=gen(), timeout=120)
    except FileNotFoundError:
        print(f"ERROR: File not found: {audio_file}")
        sys.exit(3)
    except PermissionError:
        print(f"ERROR: Permission denied: {audio_file}")
        sys.exit(15)
    except IOError as e:
        print(f"ERROR: Cannot read file: {e}")
        sys.exit(16)
    except requests.RequestException as e:
        print(f"ERROR: Upload request failed: {e}")
        sys.exit(4)

    if resp.status_code not in (200, 201):
        print(f"ERROR: Upload failed ({resp.status_code}): {resp.text}")
        sys.exit(5)

    try:
        upload_url = resp.json().get("upload_url")
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON response from upload API")
        sys.exit(17)
    
    if not upload_url:
        print("ERROR: No upload_url returned by API.")
        sys.exit(6)

    print(f"Uploaded to: {upload_url}")
    return upload_url

def request_transcript(audio_url, api_key, options=None):
    print("Requesting transcription...")
    # debug/validation
    if not isinstance(audio_url, str) or not audio_url.startswith("https://"):
        print(f"ERROR: Invalid audio_url passed to request_transcript: {audio_url!r}")
        sys.exit(21)

    data = {"audio_url": audio_url}
    if options:
        data.update(options)

    # debug: show payload about to be sent
    print("DEBUG: transcript request payload =", json.dumps(data, ensure_ascii=False))
    
    headers = {
        "authorization": api_key,
        "content-type": "application/json"
    }

    try:
        resp = requests.post(TRANSCRIPT_URL, json=data, headers=headers, timeout=180)
    except requests.RequestException as e:
        print(f"ERROR: Transcript request failed: {e}")
        sys.exit(7)

    if resp.status_code not in (200, 201):
        print(f"ERROR: Transcript request failed ({resp.status_code}): {resp.text}")
        sys.exit(8)

    try:
        transcript_id = resp.json().get("id")
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON response from transcript API")
        sys.exit(18)
    
    if not transcript_id:
        print("ERROR: No transcript id returned.")
        sys.exit(9)

    print(f"Transcript ID: {transcript_id}")
    return transcript_id

def poll_transcript(transcript_id, api_key, timeout=300, poll_interval=3):
    url = f"{TRANSCRIPT_URL}/{transcript_id}"
    headers = {"authorization": api_key}
    start_time = time.time()
    print("Waiting for transcription to complete...")
    while True:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as e:
            print(f"ERROR: Polling request failed: {e}")
            sys.exit(10)

        if resp.status_code != 200:
            print(f"ERROR: Poll failed ({resp.status_code}): {resp.text}")
            sys.exit(11)

        try:
            result = resp.json()
        except json.JSONDecodeError:
            print("ERROR: Invalid JSON response from polling API")
            sys.exit(19)
        
        status = result.get("status", "unknown")
        if status == "completed":
            print("Transcription completed.")
            return result
        if status == "error":
            print(f"ERROR: Transcription error: {result.get('error', 'unknown')}")
            sys.exit(12)

        elapsed = time.time() - start_time
        if elapsed > timeout:
            print(f"ERROR: Transcription timed out after {timeout} seconds.")
            sys.exit(13)

        print(f"Status: {status}. Elapsed: {int(elapsed)}s. Polling again in {poll_interval}s...")
        time.sleep(poll_interval)

def parse_words(transcript_data, model_name=None):
    words = transcript_data.get("words", [])
    if not words:
       if model_name == "slam-1":
         print("Warning: This model is still in beta stage")
       else:
         print("Warning: No word-level data found in transcript.")
    return words

def save_output(audio_file, transcript_result, words, output_file):
    out = {
        "source_file": audio_file,
        "text": transcript_result.get("text", ""),
        "words": words,
        "meta": {
            "status": transcript_result.get("status"),
            "id": transcript_result.get("id")
        }
    }
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"ERROR: Failed to write output file: {e}")
        sys.exit(14)
    print(f"Saved output to: {output_file}")

def main():
    parser = ArgumentParser(description="Auralynx: Transcribe audio with AssemblyAI")
    parser.add_argument("audio_file", help="Path to audio file (mp3/wav/m4a)")
    parser.add_argument("--output", "-o", help="Output json filename (default: <audio>_alynx.json)")
    parser.add_argument("--timeout", type=int, default=300, help="Polling timeout in seconds (default 300)")
    parser.add_argument("--model", default="universal", help="Change speech-to-text model")
    args = parser.parse_args()
    
    allowed_models = ["slam-1", "universal"]
    if args.model not in allowed_models:
      print(f"ERROR: Invalid model '{args.model}' | Allowed : {allowed_models}")
      sys.exit(20)

    api_key = get_api_key()
    audio_file = args.audio_file
    output_file = args.output or (os.path.splitext(audio_file)[0] + "_alynx.json")
    transcript_options = {
        # minimal options; can be extended
        "speech_model": args.model,
        "format_text": True,
        "punctuate": True,
    }

    upload_url = upload_file(audio_file, api_key)
    transcript_id = request_transcript(upload_url, api_key, options=transcript_options)
    result = poll_transcript(transcript_id, api_key, timeout=args.timeout)
    words = parse_words(result, args.model)
    save_output(audio_file, result, words, output_file)

    # print a brief preview
    print("=" * 60)
    print("WORD-LEVEL PREVIEW (first 30 words)")
    print("=" * 60)
    for w in words[:30]:
        start = w.get("start", 0) / 1000
        end = w.get("end", 0) / 1000
        text = w.get("text", "")
        print(f"{start:6.2f}s - {end:6.2f}s : {text}")
    print(f"... total words: {len(words)}")
    print("Success.")
    print(f"using model: {args.model}")
    sys.exit(0)

if __name__ == "__main__":
    main()
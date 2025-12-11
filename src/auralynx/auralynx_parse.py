#!/usr/bin/env python3
"""
Auralynx: Parse AssemblyAI JSON

Behavior:
- `parse <json>` (no --lrc) : show WORD-LEVEL TIMESTAMPS + WORD_DATA
- `parse --lrc` or `parse-lrc` : export .lrc (if requested), NO WORD_DATA, NO READABLE JSON
"""

import json
import sys
import os
from argparse import ArgumentParser

def load_json(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {json_file}")
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        sys.exit(3)

def format_seconds_to_lrc_ts(sec):
    minutes = int(sec // 60)
    seconds = sec - minutes * 60
    return f"{minutes:02d}:{seconds:05.2f}"

def export_lrc(words, outpath):
    lines = []
    for w in words:
        start_ms = w.get('start')
        text = w.get('text', '').strip()
        if start_ms is None or not text:
            continue
        
        try:
            start_s = start_ms / 1000.0
        except (TypeError, ZeroDivisionError):
            print(f"WARNING: Invalid timestamp for word: {text}")
            continue
        
        ts = format_seconds_to_lrc_ts(start_s)
        lines.append(f"[{ts}]{text}")
    try:
        with open(outpath, 'w', encoding='utf-8') as f:
            for l in lines:
                f.write(l + "\n")
    except PermissionError:
        print(f"ERROR: Permission denied writing to: {outpath}")
        sys.exit(6)
    except IOError as e:
        print(f"ERROR: Failed to write LRC file: {e}")
        sys.exit(4)
    print(f"LRC exported to: {outpath}")

def auralynx_parse(json_file, export_lrc_flag=False, lrc_out=None):
    data = load_json(json_file)
    words = data.get('words', [])

    if not words:
        print("ERROR: No words found in JSON.")
        sys.exit(5)
    
    if not isinstance(words, list):
        print("ERROR: 'words' field is not a list in JSON")
        sys.exit(5)

    # Always show timestamps
    print("=" * 60)
    print("WORD-LEVEL TIMESTAMPS")
    print("=" * 60)
    for word in words:
        start_ms = word.get('start')
        end_ms = word.get('end')
        
        if start_ms is None or end_ms is None:
            print(f"WARNING: Missing timestamp for word: {word.get('text', 'unknown')}")
            continue
        
        try:
            start = start_ms / 1000
            end = end_ms / 1000
            duration = end - start
        except (TypeError, ZeroDivisionError):
            print(f"WARNING: Invalid timestamp for word: {word.get('text', 'unknown')}")
            continue
        
        text = word.get('text', '')
        print(f"{start:6.2f}s - {end:6.2f}s ({duration:.2f}s) : {text}")

    if export_lrc_flag:
        # Export LRC (no WORD_DATA, no JSON output)
        if not lrc_out:
            base = os.path.splitext(json_file)[0]
            lrc_out = base + ".lrc"

        export_lrc(words, lrc_out)

        print("\n[SUCCESS] LRC export complete.")
        sys.exit(0)

    else:
        # Default parse → show WORD_DATA
        print("\n" + "=" * 60)
        print("WORD_DATA = [")
        for w in words:
            start_ms = w.get('start')
            end_ms = w.get('end')
            
            if start_ms is None or end_ms is None:
                continue
            
            try:
                start = start_ms / 1000
                end = end_ms / 1000
                duration = end - start
            except (TypeError, ZeroDivisionError):
                continue
            
            text = w.get('text', '').replace("'", "\\'")
            print(f"    {{'word': '{text}', 'start': {start:.2f}, 'end': {end:.2f}, 'duration': {duration:.2f}}},")
        print("]")
        print("\n[SUCCESS] Parse complete.")
        sys.exit(0)

def main():
    parser = ArgumentParser(description="Auralynx: Parse AssemblyAI JSON and optionally export LRC")
    parser.add_argument("json_file", help="AssemblyAI JSON (output from auralynx_core_api.py)")
    parser.add_argument("--lrc", action="store_true", help="Export .lrc file")
    parser.add_argument("--lrc-out", help="Custom LRC output filename")
    args = parser.parse_args()

    auralynx_parse(args.json_file, export_lrc_flag=args.lrc, lrc_out=args.lrc_out)

if __name__ == "__main__":
    main()
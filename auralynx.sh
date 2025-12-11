#!/bin/bash
# Auralynx - Audio Transcription & Parsing CLI Tool

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    echo -e "\033[1;96m
░█▀█░█░█░█▀▄░█▀█░█░░░█░█░█▀█░█░█
░█▀█░█░█░█▀▄░█▀█░█░░░░█░░█░█░▄▀▄
░▀░▀░▀▀▀░▀░▀░▀░▀░▀▀▀░░▀░░▀░▀░▀░▀
         AURALYNX CLI
      \033[0m"
    cat <<EOF
Usage:
  export AAI_API_KEY="your_assemblyai_api_here"
      - Set your AssemblyAI API key before using any commands.

  ./auralynx.sh transcribe <audio.mp3> [--model <name>]
      - Transcribe audio file and save output as <audio>_alynx.json.
        Default model: universal

  ./auralynx.sh parse <json_file>
      - Parse transcription JSON and show word-level preview.

  ./auralynx.sh parse-lrc <json_file>
      - Parse transcription JSON and export LRC (karaoke-style timestamps).

  ./auralynx.sh auto <audio.mp3> [--model <name>]
      - Transcribe + Parse automatically (produces JSON).

  ./auralynx.sh auto-lrc <audio.mp3> [--model <name>]
      - Transcribe + Parse + Export LRC automatically.

Models:
  universal   → Supports word-level timestamps. Recommended for LRC.
  slam-1      → Beta

Examples:
  ./auralynx.sh transcribe song.mp3
  ./auralynx.sh transcribe song.mp3 --model universal
  ./auralynx.sh parse song_alynx.json
  ./auralynx.sh parse-lrc song_alynx.json
  ./auralynx.sh auto song.mp3
  ./auralynx.sh auto-lrc song.mp3 --model universal
EOF
}

transcribe() {
    if [ -z "$1" ]; then
        echo "ERROR: Audio file required"
        exit 1
    fi
    
    audio="$1"
    shift
    extra_args=("$@")
    base_name="${audio%.*}"
    out_json="${base_name}_alynx.json"

    echo "Transcribing: ${audio} -> ${out_json}"
    python "$SCRIPT_DIR/src/auralynx/auralynx_core_api.py" "$audio" "${extra_args[@]}" --output "$out_json"
    return $?
}

parse() {
    if [ -z "$1" ]; then
        echo "ERROR: JSON file required"
        exit 1
    fi

    echo "Parsing: $1"
    python "$SCRIPT_DIR/src/auralynx/auralynx_parse.py" "$1"
    return $?
}

parse_lrc() {
    if [ -z "$1" ]; then
        echo "ERROR: JSON file required"
        exit 1
    fi

    echo "Parsing and exporting LRC: $1"
    python "$SCRIPT_DIR/src/auralynx/auralynx_parse.py" "$1" --lrc
    return $?
}

auto() {
    if [ -z "$1" ]; then
        echo "ERROR: Audio file required"
        exit 1
    fi

    base_name="${1%.*}"
    json_file="${base_name}_alynx.json"

    echo "Auto mode: transcribe -> parse"
    transcribe "$1"
    if [ $? -ne 0 ]; then
        echo "ERROR: Transcription failed"
        exit 1
    fi

    if [ -f "$json_file" ]; then
        parse "$json_file"
    else
        echo "ERROR: Expected JSON file not found: $json_file"
        exit 1
    fi
}

auto_lrc() {
    if [ -z "$1" ]; then
        echo "ERROR: Audio file required"
        exit 1
    fi

    base_name="${1%.*}"
    json_file="${base_name}_alynx.json"

    echo "Auto mode: transcribe -> parse -> lrc"
    transcribe "$1"
    if [ $? -ne 0 ]; then
        echo "ERROR: Transcription failed"
        exit 1
    fi

    if [ -f "$json_file" ]; then
        parse_lrc "$json_file"
    else
        echo "ERROR: Expected JSON file not found: $json_file"
        exit 1
    fi
}

case "$1" in
    transcribe)
        transcribe "${@:2}"
        ;;
    parse)
        parse "$2"
        ;;
    parse-lrc)
        parse_lrc "$2"
        ;;
    auto)
        auto "$2"
        ;;
    auto-lrc)
        auto_lrc "$2"
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "ERROR: Unknown command: $1"
        show_help
        exit 1
        ;;
esac
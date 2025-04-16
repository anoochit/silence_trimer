import subprocess
import re
import json
import argparse

def detect_silence(input_file):
    cmd = [
        "ffmpeg", "-i", input_file,
        "-af", "silencedetect=noise=-30dB:d=0.5",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    return result.stderr

def parse_silence(log):
    silence = []
    start = None
    for line in log.splitlines():
        if "silence_start" in line:
            match = re.search(r"silence_start: (\d+\.?\d*)", line)
            if match:
                start = float(match.group(1))
        elif "silence_end" in line and start is not None:
            match = re.search(r"silence_end: (\d+\.?\d*)", line)
            if match:
                end = float(match.group(1))
                duration = end - start
                silence.append({"start": start, "duration": duration})
                start = None
    return silence

def save_as_resolve_json(silence_data, output_file):
    markers = {
        "version": "1.0",
        "markers": [
            {
                "start": s["start"],
                "duration": s["duration"],
                "color": "Blue",
                "name": "Silence",
                "note": "Auto-marked silent section"
            } for s in silence_data
        ]
    }
    with open(output_file, "w") as f:
        json.dump(markers, f, indent=2)

def seconds_to_tc(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    f = int((seconds % 1) * 30)  # Assuming 30fps for EDL
    return f"{h:02}:{m:02}:{s:02}:{f:02}"

def save_as_edl(silence_data, output_file):
    lines = []
    lines.append("TITLE: Silence Detection")
    lines.append("FCM: NON-DROP FRAME")
    lines.append("")

    for i, s in enumerate(silence_data, start=1):
        start_tc = seconds_to_tc(s["start"])
        end_tc = seconds_to_tc(s["start"] + s["duration"])
        lines.append(f"{i:03}  AX       V     C        {start_tc} {end_tc} {start_tc} {end_tc}")
        lines.append(f"* FROM: {s['start']} TO: {s['start'] + s['duration']}")
        lines.append("* SILENCE\n")

    with open(output_file, "w") as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser(description="Detect silent parts in a video and export markers.")
    parser.add_argument("-i", "--input", default="video.mp4", help="Input video file (default: video.mp4)")
    parser.add_argument("-o", "--output", default="marker.json", help="Output marker file (default: marker.json)")
    parser.add_argument("-f", "--format", default="json", choices=["json", "edl"], help="Output format: json or edl (default: json)")
    args = parser.parse_args()

    print(f"🔍 Detecting silence in: {args.input}")
    log = detect_silence(args.input)

    print("🧠 Parsing silence data...")
    silent_ranges = parse_silence(log)

    print(f"💾 Saving markers to: {args.output} ({args.format})")
    if args.format == "json":
        save_as_resolve_json(silent_ranges, args.output)
    elif args.format == "edl":
        save_as_edl(silent_ranges, args.output)

    print("✅ Done!")

if __name__ == "__main__":
    main()

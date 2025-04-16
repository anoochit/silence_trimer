import subprocess
import re
import os
import argparse
from pathlib import Path
import shutil
import json

SILENCE_THRESHOLD = "-30dB"
SILENCE_DURATION = "1"  # in seconds

def detect_silence(input_file):
    cmd = [
        "ffmpeg", "-i", input_file,
        "-af", f"silencedetect=n={SILENCE_THRESHOLD}:d={SILENCE_DURATION}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    return result.stderr

def parse_silence_log(log):
    silence_times = []
    for line in log.splitlines():
        match_start = re.search(r"silence_start: ([\d.]+)", line)
        match_end = re.search(r"silence_end: ([\d.]+)", line)
        if match_start:
            silence_times.append(("start", float(match_start.group(1))))
        elif match_end:
            silence_times.append(("end", float(match_end.group(1))))
    return silence_times

def generate_keep_segments(silence_times, video_duration):
    segments = []
    prev_end = 0.0

    for i in range(0, len(silence_times), 2):
        start = silence_times[i][1]
        end = silence_times[i + 1][1] if i + 1 < len(silence_times) else video_duration
        if start > prev_end:
            segments.append((prev_end, start))
        prev_end = end

    if prev_end < video_duration:
        segments.append((prev_end, video_duration))

    return segments

def get_video_duration(input_file):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    return float(result.stdout.strip())

def check_audio_streams(input_file):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a", 
        "-show_entries", "stream=index", 
        "-of", "csv=p=0",
        input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    audio_streams = result.stdout.strip().split('\n')
    return len(audio_streams) > 0 and audio_streams[0] != ''

def get_stream_info(input_file):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_streams", "-show_format",
        "-print_format", "json",
        input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

def cut_segments(input_file, segments, has_audio):
    segment_files = []
    for i, (start, end) in enumerate(segments):
        output = f"part{i}.mp4"
        
        # Base command with seeking before input for accuracy
        cmd = [
            "ffmpeg", "-ss", str(start),
            "-i", input_file,
            "-to", str(end - start),
            "-c:v", "copy"  # Copy video stream without re-encoding
        ]
        
        # Add audio parameters only if the input has audio
        if has_audio:
            cmd.extend([
                "-c:a", "aac",     # Use AAC codec for audio
                "-b:a", "192k",    # Set audio bitrate
            ])
        
        # Add output file
        cmd.append(output)
        
        print(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd)
        
        # Verify the segment has audio if expected
        if has_audio and not check_audio_streams(output):
            print(f"Warning: Segment {output} missing audio, retrying with different encoding...")
            # Try again with a different approach
            fallback_cmd = [
                "ffmpeg", "-ss", str(start),
                "-i", input_file,
                "-to", str(end - start),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-strict", "experimental",
                f"fallback_{output}"
            ]
            subprocess.run(fallback_cmd)
            if os.path.exists(f"fallback_{output}") and check_audio_streams(f"fallback_{output}"):
                shutil.move(f"fallback_{output}", output)
            
        segment_files.append(output)
    
    return segment_files

def concat_segments(segment_files, output_file, has_audio):
    # Method 1: Concat demuxer (usually best for identical codecs)
    try:
        print("Trying concat demuxer method...")
        with open("file_list.txt", "w") as f:
            for file in segment_files:
                f.write(f"file '{file}'\n")
        
        concat_cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", "file_list.txt"
        ]
        
        # Add specific mapping if audio is expected
        if has_audio:
            concat_cmd.extend([
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k"
            ])
        else:
            concat_cmd.extend(["-c", "copy"])
            
        concat_cmd.append(output_file)
        subprocess.run(concat_cmd)
        
        # Verify the output has audio if expected
        if has_audio and not check_audio_streams(output_file):
            raise Exception("Concat demuxer method failed to preserve audio")
            
    except Exception as e:
        print(f"First method failed: {e}")
        print("Trying filter_complex method...")
        
        # Method 2: Using filter_complex (more reliable for complex cases)
        inputs = []
        for file in segment_files:
            inputs.extend(["-i", file])
        
        filter_parts = []
        for i in range(len(segment_files)):
            if has_audio:
                filter_parts.append(f"[{i}:v:0][{i}:a:0]")
            else:
                filter_parts.append(f"[{i}:v:0]")
        
        if has_audio:
            filter_complex = "".join(filter_parts) + f"concat=n={len(segment_files)}:v=1:a=1[outv][outa]"
            map_params = ["-map", "[outv]", "-map", "[outa]"]
        else:
            filter_complex = "".join(filter_parts) + f"concat=n={len(segment_files)}:v=1:a=0[outv]"
            map_params = ["-map", "[outv]"]
            
        filter_cmd = [
            "ffmpeg"
        ] + inputs + [
            "-filter_complex", filter_complex
        ] + map_params + [
            "-c:v", "libx264"  # Re-encode video for compatibility
        ]
        
        if has_audio:
            filter_cmd.extend(["-c:a", "aac", "-b:a", "192k"])
            
        filter_cmd.append(output_file)
        subprocess.run(filter_cmd)

def direct_copy_with_audio(input_file, output_file):
    """Directly copy the input file with audio preservation."""
    cmd = [
        "ffmpeg", "-i", input_file,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        output_file
    ]
    subprocess.run(cmd)

def cleanup(files):
    for f in files:
        try:
            Path(f).unlink(missing_ok=True)
        except:
            print(f"Could not delete temporary file: {f}")
    
    try:
        Path("file_list.txt").unlink(missing_ok=True)
    except:
        print("Could not delete file_list.txt")

def main():
    parser = argparse.ArgumentParser(description="Remove silent parts from a video while preserving audio.")
    parser.add_argument("input", help="Input video file")
    parser.add_argument("output", help="Output trimmed video file")
    parser.add_argument("--keep-all", action="store_true", help="Keep the entire video without trimming")
    parser.add_argument("--method", choices=["concat", "filter", "direct"], default="concat", 
                       help="Method for concatenating: concat (demuxer), filter (complex), or direct (one-step)")
    args = parser.parse_args()

    input_file = args.input
    output_file = args.output

    # Check if input has audio
    has_audio = check_audio_streams(input_file)
    if not has_audio:
        print("Information: Input file doesn't contain audio streams, output will be video-only.")
    else:
        print("Input file contains audio streams, will preserve audio.")

    if args.keep_all:
        print(f"Keeping entire video and copying to {output_file}...")
        direct_copy_with_audio(input_file, output_file)
        print(f"✅ Done! Output saved as: {output_file}")
        return

    # If using direct method, process all in one step
    if args.method == "direct":
        print("Using direct one-step processing method...")
        # Get silence information
        silence_log = detect_silence(input_file)
        silence_times = parse_silence_log(silence_log)
        
        if not silence_times:
            print("No silence detected. Creating a copy of the entire file...")
            direct_copy_with_audio(input_file, output_file)
        else:
            # Get video duration
            duration = get_video_duration(input_file)
            keep_segments = generate_keep_segments(silence_times, duration)
            
            # Create filter complex string for trimming and concatenating in one step
            filter_parts = []
            for i, (start, end) in enumerate(keep_segments):
                trim_duration = end - start
                filter_parts.append(f"[0:v]trim=start={start}:duration={trim_duration},setpts=PTS-STARTPTS[v{i}];")
                if has_audio:
                    filter_parts.append(f"[0:a]atrim=start={start}:duration={trim_duration},asetpts=PTS-STARTPTS[a{i}];")
            
            v_streams = "".join([f"[v{i}]" for i in range(len(keep_segments))])
            filter_complex = "".join(filter_parts)
            
            if has_audio:
                a_streams = "".join([f"[a{i}]" for i in range(len(keep_segments))])
                filter_complex += f"{v_streams}concat=n={len(keep_segments)}:v=1:a=0[outv];"
                filter_complex += f"{a_streams}concat=n={len(keep_segments)}:v=0:a=1[outa]"
                map_params = ["-map", "[outv]", "-map", "[outa]"]
            else:
                filter_complex += f"{v_streams}concat=n={len(keep_segments)}:v=1:a=0[outv]"
                map_params = ["-map", "[outv]"]
            
            # Run FFmpeg command
            cmd = [
                "ffmpeg", "-i", input_file,
                "-filter_complex", filter_complex
            ] + map_params + [
                "-c:v", "libx264"  # Re-encode video
            ]
            
            if has_audio:
                cmd.extend(["-c:a", "aac", "-b:a", "192k"])
                
            cmd.append(output_file)
            subprocess.run(cmd)
        
        # Final verification
        if has_audio:
            final_has_audio = check_audio_streams(output_file)
            if not final_has_audio:
                print("⚠️ Warning: Could not preserve audio in the output file.")
            else:
                print("✓ Audio successfully preserved in the output file.")
                
        print(f"✅ Done! Output saved as: {output_file}")
        return

    # Standard processing flow
    print(f"[1] Detecting silence in {input_file}...")
    silence_log = detect_silence(input_file)
    silence_times = parse_silence_log(silence_log)

    if not silence_times:
        print("No silence detected or input has no audio. Creating a copy of the entire file...")
        direct_copy_with_audio(input_file, output_file)
        print(f"✅ Done! Output saved as: {output_file}")
        return

    print("[2] Getting video duration...")
    duration = get_video_duration(input_file)

    print("[3] Generating keep segments...")
    keep_segments = generate_keep_segments(silence_times, duration)

    print(f"[4] Cutting {len(keep_segments)} segments...")
    segment_files = cut_segments(input_file, keep_segments, has_audio)

    print(f"[5] Concatenating into {output_file} using {args.method} method...")
    if args.method == "filter":
        concat_segments(segment_files, output_file, has_audio)
    else:  # concat demuxer method
        concat_segments(segment_files, output_file, has_audio)

    print("[6] Cleaning up temporary files...")
    cleanup(segment_files)

    # Final verification
    if has_audio:
        final_has_audio = check_audio_streams(output_file)
        if not final_has_audio:
            print("⚠️ Warning: Could not preserve audio in the output file.")
            print("Try using a different method with --method filter or --method direct")
            
            # Last resort - try direct copy from input
            backup_output = output_file + ".backup"
            if os.path.exists(output_file):
                os.rename(output_file, backup_output)
            
            print("Attempting emergency audio recovery...")
            direct_copy_with_audio(input_file, output_file)
            
            if check_audio_streams(output_file):
                print("✓ Audio successfully recovered in the output file.")
                os.remove(backup_output)
            else:
                os.rename(backup_output, output_file)
                print("Recovery failed. Original output file restored.")
        else:
            print("✓ Audio successfully preserved in the output file.")

    print(f"✅ Done! Output saved as: {output_file}")

if __name__ == "__main__":
    main()
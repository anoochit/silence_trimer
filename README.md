# Silent Video Trimmer

A Python script to automatically remove silent portions from videos while preserving audio in non-silent sections.

## Overview

This tool analyzes a video file to detect silent segments and creates a new video that only contains the non-silent parts. It's useful for:

- Removing "dead air" from recorded presentations
- Cleaning up video recordings with long pauses
- Creating more concise versions of videos without manual editing
- Automatically editing out silence from interviews or lectures

## Requirements

- Python 3.6+
- FFmpeg (must be installed and available in your PATH)
- Required Python packages (see `requirements.txt`)

## Installation

1. Ensure FFmpeg is installed on your system:
   ```bash
   # For Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # For macOS using Homebrew
   brew install ffmpeg
   
   # For Windows, download from https://ffmpeg.org/download.html
   ```

2. Clone this repository or download the script files

3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Basic usage:

```bash
python silent_trimmer.py input.mp4 output.mp4
```

### Options

```
usage: silent_trimmer.py [-h] [--keep-all] [--method {concat,filter,direct}] input output

Remove silent parts from a video while preserving audio.

positional arguments:
  input                 Input video file
  output                Output trimmed video file

optional arguments:
  -h, --help            show this help message and exit
  --keep-all            Keep the entire video without trimming
  --method {concat,filter,direct}
                        Method for concatenating: concat (demuxer), filter (complex), or direct (one-step)
```

### Concatenation Methods

The script offers three different methods for handling the video processing:

1. **concat** (default): Uses FFmpeg's concat demuxer - fastest but may have audio issues with some files
2. **filter**: Uses filter_complex for more reliable audio preservation but may be slower
3. **direct**: One-step processing that avoids separate segment files - most reliable but slower

If you experience audio issues, try:

```bash
python silent_trimmer.py input.mp4 output.mp4 --method filter
```

Or for the most reliable method:

```bash
python silent_trimmer.py input.mp4 output.mp4 --method direct
```

## Customization

You can adjust the silence detection parameters by modifying these constants in the script:

```python
SILENCE_THRESHOLD = "-30dB"  # Adjust based on your audio levels
SILENCE_DURATION = "1"       # Minimum silence duration in seconds
```

- Lower the threshold (e.g., `-40dB`) to detect quieter sounds as non-silence
- Increase the threshold (e.g., `-20dB`) to only keep louder sections
- Adjust the duration to change how long a silent segment needs to be before it's cut

## Troubleshooting

### No Audio in Output

If your output video has no audio:

1. First try the `filter` method:
   ```
   python silent_trimmer.py input.mp4 output.mp4 --method filter
   ```

2. If that fails, try the `direct` method:
   ```
   python silent_trimmer.py input.mp4 output.mp4 --method direct
   ```

3. Verify your input file actually has audio:
   ```
   ffprobe -v error -show_entries stream=codec_type -of default=noprint_wrappers=1 input.mp4
   ```

### Other Issues

- **Script fails immediately**: Make sure FFmpeg is installed and in your PATH
- **No silence detected**: Try adjusting the `SILENCE_THRESHOLD` value in the script
- **Process is too slow**: Use the default `concat` method (fastest but less reliable)
- **Output file quality issues**: The `direct` method re-encodes video which may affect quality

## How It Works

1. The script analyzes your video to detect silent segments
2. It identifies the non-silent portions to keep
3. It extracts these segments (either as temporary files or directly)
4. Finally, it concatenates the segments into a single output file

## License

This tool is released under the MIT License.
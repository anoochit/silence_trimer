# 🎬 Silence Marker CLI

A simple CLI tool to detect **silent sections (dead space)** in a video file and export them as markers in various formats such as **DaVinci Resolve JSON** and **EDL**.

Useful for post-production workflows like skipping silences in interviews, podcasts, or tutorials.
 

## 📦 Features

- Detects silence using `ffmpeg`.
- Outputs markers in:
  - ✅ DaVinci Resolve-compatible **JSON**
  - ✅ Generic **EDL (Edit Decision List)**
- Lightweight, fast, and customizable.
 
## 🚀 How to Use

### ✅ Requirements

- Python 3.6+
- [`ffmpeg`](https://ffmpeg.org/) installed on your system.
 

### ▶️ Run the CLI

```bash
python silence_marker.py
```

This runs with default settings:
- Input: `video.mp4`
- Output: `marker.json`
- Format: `json`

#### 🔧 Custom usage:

```bash
python silence_marker.py -i input.mp4 -o silence_markers.edl -f edl
```

| Flag             | Description                  | Default       |
| ---------------- | ---------------------------- | ------------- |
| `-i`, `--input`  | Input video file             | `video.mp4`   |
| `-o`, `--output` | Output file path             | `marker.json` |
| `-f`, `--format` | Output format: `json`, `edl` | `json`        |
 

### 📥 Import to DaVinci Resolve (for JSON)

1. Open timeline in Resolve.
2. Go to `Timeline` → `Import` → `Timeline Markers`.
3. Choose the `.edl` file.
 

## 📄 Output Formats

### 📁 JSON (DaVinci Resolve)

```json
{
  "version": "1.0",
  "markers": [
    {
      "start": 10.3,
      "duration": 1.2,
      "color": "Blue",
      "name": "Silence",
      "note": "Auto-marked silent section"
    }
  ]
}
```

### 🎞️ EDL Example

```edl
TITLE: Silence Detection
FCM: NON-DROP FRAME

001  AX       V     C        00:00:10:07 00:00:11:02 00:00:10:07 00:00:11:02
* FROM: 10.3 TO: 11.5
* SILENCE
```
 


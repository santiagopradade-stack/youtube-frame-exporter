# YouTube Frame Exporter

A small Windows desktop app that downloads one YouTube video and exports one JPG image for every second of video.

## Fastest way to build the `.exe`

1. Install [Python 3.11 or newer](https://www.python.org/downloads/windows/) and enable **Add Python to PATH** during setup.
2. Double-click `build_windows.bat`.
3. When it finishes, open `dist` and run `YouTubeFrameExporter.exe`.

The build script downloads Deno from its official GitHub release. The executable includes Deno and FFmpeg, so the finished app does not require separate installs. The build is large because it contains the Python runtime, `yt-dlp`, Deno, and FFmpeg.

Alternatively, put these files in a GitHub repository and run **Build Windows executable** from the Actions tab. Download `YouTubeFrameExporter-Windows` from that workflow run.

## Use

1. Paste a YouTube or `youtu.be` video link.
2. Choose the folder where the images should be saved.
3. Click **Export frames**.

The app creates a folder named after the video. Frames are numbered from `frame_000000.jpg`, with one image for each second. Temporary video files are deleted when the export finishes or is cancelled.

## Run without building

Double-click `run_from_source.bat`. The first run downloads Deno, creates a private Python environment, and installs the required packages.

## Notes

- Only download videos you have permission to use and follow YouTube's terms.
- A 60-minute video produces roughly 3,600 JPG files and can use substantial disk space.
- YouTube changes occasionally. If downloads stop working, rebuild after updating the version of `yt-dlp` in `requirements.txt`.
- Building and first-time source setup require an internet connection. The app itself requires internet access to download the selected video.

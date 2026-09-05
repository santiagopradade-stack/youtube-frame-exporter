# YouTube Frame Exporter

A simple Windows desktop app that downloads one YouTube video and exports frames into three separate interval folders.

## Use the app

1. Run `YouTubeSceneFrameExporter.exe`.
2. Paste a YouTube or `youtu.be` video link.
3. Choose where to save the images.
4. Click **Export frames**.

For each link, the app creates a video-specific folder like this:

```text
Video title [video-id]/
├── Every 1 Second/
│   ├── frame_000000s.jpg
│   ├── frame_000001s.jpg
│   └── ...
├── Every 3 Seconds/
│   ├── frame_000000s.jpg
│   ├── frame_000003s.jpg
│   └── ...
└── Every 5 Seconds/
    ├── frame_000000s.jpg
    ├── frame_000005s.jpg
    └── ...
```

Every new export gets its own folder. If the same video is exported again, the app adds `(2)`, `(3)`, and so on instead of overwriting existing images.

## Build the Windows `.exe`

1. Install [Python 3.11 or newer](https://www.python.org/downloads/windows/) and enable **Add Python to PATH**.
2. Double-click `build_windows.bat`.
3. Run `dist\\YouTubeSceneFrameExporter.exe`.

The build script packages Deno, FFmpeg, OpenCV, `yt-dlp`, and Python into the executable. The result does not require separate runtime installations.

You can also run the **Build Windows executable** workflow in GitHub Actions and download the `YouTubeSceneFrameExporter-Windows` artifact.

## Notes

- Only download videos you have permission to use and follow YouTube's terms.
- Long or high-resolution videos can take several minutes and produce many images.

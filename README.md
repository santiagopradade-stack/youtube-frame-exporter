# YouTube Frame Exporter

A simple Windows desktop app that downloads one YouTube video and exports frames into three separate interval folders.

## Download

Download the latest Windows executable from a successful
[GitHub Actions build](https://github.com/santiagopradade-stack/youtube-frame-exporter/actions).
Open the newest **Build Windows executable** run and download the
`YouTubeFrameExporter-Windows` artifact.

The project is applying for free origin-verified code signing provided by
[SignPath.io](https://signpath.io/), with a certificate provided by the
[SignPath Foundation](https://signpath.org/). See the
[code signing policy](CODE_SIGNING_POLICY.md).

## Use the app

1. Run `YouTubeFrameExporter.exe`.
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
3. Run `dist\\YouTubeFrameExporter.exe`.

The build script packages Deno, FFmpeg, OpenCV, `yt-dlp`, and Python into the executable. The result does not require separate runtime installations.

You can also run the **Build Windows executable** workflow in GitHub Actions and download the `YouTubeFrameExporter-Windows` artifact.

## Notes

- Only download videos you have permission to use and follow YouTube's terms.
- Long or high-resolution videos can take several minutes and produce many images.

## License and privacy

The project is released under the [MIT License](LICENSE). It does not collect
analytics, telemetry, or personal information. See the
[privacy policy](PRIVACY.md) for details.

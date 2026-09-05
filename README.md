# YouTube Scene Frame Exporter

A Windows desktop app that downloads one YouTube video, detects scene changes, and exports the exact first and last frame of every detected scene.

## Use the app

1. Run `YouTubeSceneFrameExporter.exe`.
2. Paste a YouTube or `youtu.be` video link.
3. Choose where to save the images.
4. Start with **Normal** scene sensitivity.
5. Click **Export scene frames**.

The app creates a new video-specific folder on every run. Files look like:

```text
scene_0001_first.jpg
scene_0001_last.jpg
scene_0002_first.jpg
scene_0002_last.jpg
```

If separate shots are combined into one scene, choose **High — more scenes**. If flashes or rapid motion create too many scenes, choose **Low — fewer scenes**.

## Build the Windows `.exe`

1. Install [Python 3.11 or newer](https://www.python.org/downloads/windows/) and enable **Add Python to PATH**.
2. Double-click `build_windows.bat`.
3. Run `dist\YouTubeSceneFrameExporter.exe`.

The build script packages Deno, FFmpeg, OpenCV, PySceneDetect, `yt-dlp`, and Python into the executable. The result is large but does not require separate runtime installations.

You can also run the **Build Windows executable** workflow in GitHub Actions and download the `YouTubeSceneFrameExporter-Windows` artifact.

## Notes

- Only download videos you have permission to use and follow YouTube's terms.
- Scene detection is content-based and may take several minutes for long videos.
- Scene boundaries are subjective. The sensitivity setting lets you tune the result.

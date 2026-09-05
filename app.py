from __future__ import annotations

import math
import os
import queue
import shutil
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
import imageio_ffmpeg
import yt_dlp

from core import INTERVALS, intervals_for_second, is_youtube_url, safe_folder_name, sample_seconds, unique_output_folder


APP_NAME = "YouTube Frame Exporter"
VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


class Cancelled(Exception):
    pass


def find_deno() -> str:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    bundled = bundle_root / ("deno.exe" if os.name == "nt" else "deno")
    if bundled.is_file():
        return str(bundled)
    installed = shutil.which("deno")
    if installed:
        return installed
    raise RuntimeError(
        "The Deno JavaScript runtime is missing. Rebuild with build_windows.bat "
        "or install Deno from https://deno.com/."
    )


def write_jpeg(path: Path, frame: object) -> None:
    """Encode first, then let Python write the file.

    OpenCV's direct imwrite call can fail on Windows when any folder in the
    path contains Unicode characters (for example, characters in a video
    title).  Python's pathlib supports those paths correctly.
    """
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        raise RuntimeError(f"Could not encode {path.name} as a JPG image.")
    try:
        path.write_bytes(encoded.tobytes())
    except OSError as exc:
        raise RuntimeError(f"Could not write {path.name}:\n{exc}") from exc


class FrameExporterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("700x420")
        self.root.minsize(620, 390)
        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.home() / "Pictures" / "YouTube Frames"))
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.running = False
        self._build_ui()
        self.root.after(100, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=22)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        ttk.Label(container, text=APP_NAME, font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            container,
            text="Export frames into separate 1-second, 3-second, and 5-second folders.",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 18))
        ttk.Label(container, text="YouTube link").grid(row=2, column=0, columnspan=2, sticky="w")
        self.url_entry = ttk.Entry(container, textvariable=self.url_var)
        self.url_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 14))
        self.url_entry.focus_set()
        ttk.Label(container, text="Save frames in").grid(row=4, column=0, columnspan=2, sticky="w")
        self.output_entry = ttk.Entry(container, textvariable=self.output_var)
        self.output_entry.grid(row=5, column=0, sticky="ew", pady=(5, 14), padx=(0, 8))
        self.browse_button = ttk.Button(container, text="Browse…", command=self._browse)
        self.browse_button.grid(row=5, column=1, sticky="ew", pady=(5, 14))
        ttk.Label(
            container,
            text="The app creates: Every 1 Second, Every 3 Seconds, and Every 5 Seconds.",
            foreground="#666666",
            wraplength=650,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 16))
        self.progress = ttk.Progressbar(container, variable=self.progress_var, maximum=100)
        self.progress.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(container, textvariable=self.status_var, wraplength=650).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(0, 18)
        )
        button_bar = ttk.Frame(container)
        button_bar.grid(row=9, column=0, columnspan=2, sticky="e")
        self.cancel_button = ttk.Button(button_bar, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(0, 8))
        self.export_button = ttk.Button(button_bar, text="Export frames", command=self._start)
        self.export_button.pack(side="left")
        ttk.Label(
            container,
            text="Only download videos you have permission to use. Long videos can take several minutes.",
            foreground="#666666",
            wraplength=650,
        ).grid(row=10, column=0, columnspan=2, sticky="w", pady=(18, 0))

    def _browse(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.home()))
        if chosen:
            self.output_var.set(chosen)

    def _set_running(self, value: bool) -> None:
        self.running = value
        state = "disabled" if value else "normal"
        self.url_entry.configure(state=state)
        self.output_entry.configure(state=state)
        self.browse_button.configure(state=state)
        self.export_button.configure(state=state)
        self.cancel_button.configure(state="normal" if value else "disabled")

    def _start(self) -> None:
        url = self.url_var.get().strip()
        if not is_youtube_url(url):
            messagebox.showerror(APP_NAME, "Please enter a valid YouTube or youtu.be link.")
            return
        output_root = Path(self.output_var.get()).expanduser()
        try:
            output_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"The output folder could not be created:\n{exc}")
            return
        self.cancel_event.clear()
        self.progress_var.set(0)
        self.status_var.set("Starting…")
        self._set_running(True)
        threading.Thread(target=self._worker, args=(url, output_root), daemon=True).start()

    def _progress_hook(self, data: dict) -> None:
        if self.cancel_event.is_set():
            raise Cancelled()
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes", 0)
            percent = min(60.0, (downloaded / total * 60.0)) if total else 5.0
            self.events.put(("progress", (percent, "Downloading video…")))
        elif data.get("status") == "finished":
            self.events.put(("progress", (60.0, "Download complete; preparing frames…")))

    @staticmethod
    def _video_duration(video_file: Path, reported_duration: object) -> float:
        try:
            duration = float(reported_duration)
        except (TypeError, ValueError):
            duration = 0.0
        if math.isfinite(duration) and duration > 0:
            return duration
        capture = cv2.VideoCapture(str(video_file))
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        finally:
            capture.release()
        if fps > 0 and frames > 0:
            return frames / fps
        raise RuntimeError("The video duration could not be determined.")

    def _save_interval_frames(self, video_file: Path, duration: float, folder: Path) -> dict[int, int]:
        interval_folders = {
            1: folder / "Every 1 Second",
            3: folder / "Every 3 Seconds",
            5: folder / "Every 5 Seconds",
        }
        for output_folder in interval_folders.values():
            output_folder.mkdir(parents=True)

        seconds = sample_seconds(duration)
        capture = cv2.VideoCapture(str(video_file))
        if not capture.isOpened():
            raise RuntimeError("The downloaded video could not be opened for frame extraction.")
        counts = {interval: 0 for interval in INTERVALS}
        try:
            for index, second in enumerate(seconds):
                if self.cancel_event.is_set():
                    raise Cancelled()
                capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000.0)
                ok, frame = capture.read()
                if not ok:
                    if second == 0:
                        raise RuntimeError("The first video frame could not be read.")
                    break
                filename = f"frame_{second:06d}s.jpg"
                for interval in intervals_for_second(second):
                    write_jpeg(interval_folders[interval] / filename, frame)
                    counts[interval] += 1
                percent = 65.0 + ((index + 1) / len(seconds)) * 34.0
                self.events.put(("progress", (min(99.0, percent), f"Exporting frame at {second:,} seconds…")))
        finally:
            capture.release()
        return counts

    def _worker(self, url: str, output_root: Path) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="yt-frame-exporter-"))
        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            deno = find_deno()
            self.events.put(("status", "Reading video information…"))
            options = {
                "format": "bestvideo*+bestaudio/best",
                "outtmpl": str(temp_dir / "video.%(ext)s"),
                "merge_output_format": "mp4",
                "ffmpeg_location": ffmpeg,
                "js_runtimes": {"deno": {"path": deno}},
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [self._progress_hook],
            }
            with yt_dlp.YoutubeDL(options) as downloader:
                info = downloader.extract_info(url, download=True)
            if self.cancel_event.is_set():
                raise Cancelled()
            candidates = [p for p in temp_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES]
            if not candidates:
                raise RuntimeError("The downloaded video file could not be found.")
            video_file = max(candidates, key=lambda path: path.stat().st_size)
            duration = self._video_duration(video_file, info.get("duration"))
            video_id = str(info.get("id") or "video")
            base_name = safe_folder_name(str(info.get("title") or "youtube_video"), video_id)
            folder = unique_output_folder(output_root, base_name)
            folder.mkdir(parents=True)
            counts = self._save_interval_frames(video_file, duration, folder)
            self.events.put(("done", (folder, counts)))
        except Cancelled:
            self.events.put(("cancelled", None))
        except Exception as exc:
            if self.cancel_event.is_set():
                self.events.put(("cancelled", None))
            else:
                self.events.put(("error", str(exc)))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _cancel(self) -> None:
        self.cancel_event.set()
        if self.running:
            self.status_var.set("Cancelling…")

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "status":
                    self.status_var.set(str(payload))
                elif event == "progress":
                    percent, status = payload  # type: ignore[misc]
                    self.progress_var.set(float(percent))
                    self.status_var.set(str(status))
                elif event == "done":
                    folder, counts = payload  # type: ignore[misc]
                    total = sum(counts.values())
                    self.progress_var.set(100)
                    self.status_var.set(f"Done — exported {total:,} images across three folders.")
                    self._set_running(False)
                    summary = "\n".join(
                        f"Every {interval} second{'s' if interval != 1 else ''}: {counts[interval]:,} images"
                        for interval in INTERVALS
                    )
                    if messagebox.askyesno(
                        APP_NAME,
                        f"Export complete:\n\n{summary}\n\nSaved to:\n{folder}\n\nOpen the folder now?",
                    ):
                        os.startfile(folder)  # type: ignore[attr-defined]
                elif event == "cancelled":
                    self.progress_var.set(0)
                    self.status_var.set("Cancelled")
                    self._set_running(False)
                elif event == "error":
                    self.progress_var.set(0)
                    self.status_var.set("Export failed")
                    self._set_running(False)
                    messagebox.showerror(APP_NAME, f"Could not export frames:\n\n{payload}")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _on_close(self) -> None:
        if self.running and not messagebox.askyesno(APP_NAME, "An export is running. Cancel it and exit?"):
            return
        self._cancel()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.25)
    except tk.TclError:
        pass
    FrameExporterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

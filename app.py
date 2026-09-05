from __future__ import annotations

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
from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector

from core import is_youtube_url, safe_folder_name, scene_frame_targets, unique_output_folder


APP_NAME = "YouTube Scene Frame Exporter"
VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
SENSITIVITY = {"High — more scenes": 18.0, "Normal": 27.0, "Low — fewer scenes": 38.0}


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


class SceneFrameExporterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("700x470")
        self.root.minsize(620, 430)
        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.home() / "Pictures" / "YouTube Scene Frames"))
        self.sensitivity_var = tk.StringVar(value="Normal")
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
            container, text="Export the first and last frame of every automatically detected scene."
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 18))
        ttk.Label(container, text="YouTube link").grid(row=2, column=0, columnspan=2, sticky="w")
        self.url_entry = ttk.Entry(container, textvariable=self.url_var)
        self.url_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 14))
        self.url_entry.focus_set()
        ttk.Label(container, text="Save scene frames in").grid(row=4, column=0, columnspan=2, sticky="w")
        self.output_entry = ttk.Entry(container, textvariable=self.output_var)
        self.output_entry.grid(row=5, column=0, sticky="ew", pady=(5, 14), padx=(0, 8))
        self.browse_button = ttk.Button(container, text="Browse…", command=self._browse)
        self.browse_button.grid(row=5, column=1, sticky="ew", pady=(5, 14))
        ttk.Label(container, text="Scene sensitivity").grid(row=6, column=0, columnspan=2, sticky="w")
        self.sensitivity_box = ttk.Combobox(
            container, textvariable=self.sensitivity_var, values=list(SENSITIVITY), state="readonly", width=24
        )
        self.sensitivity_box.grid(row=7, column=0, columnspan=2, sticky="w", pady=(5, 5))
        ttk.Label(
            container,
            text="Use Normal first. Choose High if shots were combined, or Low if too many scenes were found.",
            foreground="#666666",
            wraplength=650,
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 16))
        self.progress = ttk.Progressbar(container, variable=self.progress_var, maximum=100)
        self.progress.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(container, textvariable=self.status_var, wraplength=650).grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(0, 18)
        )
        button_bar = ttk.Frame(container)
        button_bar.grid(row=11, column=0, columnspan=2, sticky="e")
        self.cancel_button = ttk.Button(button_bar, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(0, 8))
        self.export_button = ttk.Button(button_bar, text="Export scene frames", command=self._start)
        self.export_button.pack(side="left")
        ttk.Label(
            container,
            text="Only download videos you have permission to use. Scene detection can take several minutes.",
            foreground="#666666",
            wraplength=650,
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(18, 0))

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
        self.sensitivity_box.configure(state="disabled" if value else "readonly")
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
        threshold = SENSITIVITY[self.sensitivity_var.get()]
        threading.Thread(target=self._worker, args=(url, output_root, threshold), daemon=True).start()

    def _progress_hook(self, data: dict) -> None:
        if self.cancel_event.is_set():
            raise Cancelled()
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes", 0)
            percent = min(60.0, (downloaded / total * 60.0)) if total else 5.0
            self.events.put(("progress", (percent, "Downloading video…")))
        elif data.get("status") == "finished":
            self.events.put(("progress", (60.0, "Download complete; preparing scene detection…")))

    def _detect_scenes(self, video_file: Path, threshold: float) -> list[tuple[int, int]]:
        video = open_video(str(video_file))
        manager = SceneManager()
        manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=10))
        detection_finished = threading.Event()

        def stop_when_cancelled() -> None:
            while not detection_finished.wait(0.2):
                if self.cancel_event.is_set():
                    manager.stop()
                    return

        threading.Thread(target=stop_when_cancelled, daemon=True).start()
        self.events.put(("progress", (65.0, "Detecting scene changes…")))
        try:
            manager.detect_scenes(video=video, show_progress=False)
        finally:
            detection_finished.set()
        if self.cancel_event.is_set():
            raise Cancelled()
        scenes = manager.get_scene_list(start_in_scene=True)
        return [(start.frame_num, end.frame_num) for start, end in scenes]

    def _save_scene_frames(self, video_file: Path, scenes: list[tuple[int, int]], folder: Path) -> int:
        targets = scene_frame_targets(scenes)
        capture = cv2.VideoCapture(str(video_file))
        if not capture.isOpened():
            raise RuntimeError("The downloaded video could not be opened for frame extraction.")
        target_frames = set(targets)
        last_target = max(target_frames, default=0)
        frame_number = 0
        written = 0
        try:
            while target_frames:
                if self.cancel_event.is_set():
                    raise Cancelled()
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_number in target_frames:
                    for filename in targets[frame_number]:
                        if not cv2.imwrite(str(folder / filename), frame):
                            raise RuntimeError(f"Could not write {filename}.")
                        written += 1
                    target_frames.remove(frame_number)
                if frame_number % 30 == 0:
                    percent = 70.0 + (frame_number / max(1, last_target)) * 29.0
                    self.events.put(
                        ("progress", (min(99.0, percent), "Exporting first and last scene frames…"))
                    )
                frame_number += 1
        finally:
            capture.release()
        if target_frames:
            raise RuntimeError("The video ended before all scene frames could be exported.")
        return written

    def _worker(self, url: str, output_root: Path, threshold: float) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="yt-scene-exporter-"))
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
            scenes = self._detect_scenes(video_file, threshold)
            if not scenes:
                raise RuntimeError("No scenes were detected.")
            video_id = str(info.get("id") or "video")
            base_name = safe_folder_name(str(info.get("title") or "youtube_video"), video_id)
            folder = unique_output_folder(output_root, f"{base_name} - scene frames")
            folder.mkdir(parents=True)
            written = self._save_scene_frames(video_file, scenes, folder)
            self.events.put(("done", (folder, len(scenes), written)))
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
                    folder, scene_count, frame_count = payload  # type: ignore[misc]
                    self.progress_var.set(100)
                    self.status_var.set(
                        f"Done — detected {scene_count:,} scenes and exported {frame_count:,} images."
                    )
                    self._set_running(False)
                    if messagebox.askyesno(
                        APP_NAME,
                        f"Detected {scene_count:,} scenes and exported {frame_count:,} images to:\n{folder}\n\nOpen the folder now?",
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
                    messagebox.showerror(APP_NAME, f"Could not export scene frames:\n\n{payload}")
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
    SceneFrameExporterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

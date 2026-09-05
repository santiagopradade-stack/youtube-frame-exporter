from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import imageio_ffmpeg
import yt_dlp

from core import is_youtube_url, make_ffmpeg_command, safe_folder_name


APP_NAME = "YouTube Frame Exporter"
VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def find_deno() -> str:
    """Find Deno bundled by PyInstaller or installed on PATH."""
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


class Cancelled(Exception):
    pass


class FrameExporterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("680x390")
        self.root.minsize(600, 360)

        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.home() / "Pictures" / "YouTube Frames"))
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.ffmpeg_process: subprocess.Popen[str] | None = None
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
            text="Paste a YouTube link and export one high-quality JPG for every second.",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 18))

        ttk.Label(container, text="YouTube link").grid(row=2, column=0, columnspan=2, sticky="w")
        self.url_entry = ttk.Entry(container, textvariable=self.url_var)
        self.url_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 14))
        self.url_entry.focus_set()

        ttk.Label(container, text="Save frames in").grid(row=4, column=0, columnspan=2, sticky="w")
        self.output_entry = ttk.Entry(container, textvariable=self.output_var)
        self.output_entry.grid(row=5, column=0, sticky="ew", pady=(5, 18), padx=(0, 8))
        self.browse_button = ttk.Button(container, text="Browse…", command=self._browse)
        self.browse_button.grid(row=5, column=1, sticky="ew", pady=(5, 18))

        self.progress = ttk.Progressbar(container, variable=self.progress_var, maximum=100)
        self.progress.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(container, textvariable=self.status_var, wraplength=620).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(0, 18)
        )

        button_bar = ttk.Frame(container)
        button_bar.grid(row=8, column=0, columnspan=2, sticky="e")
        self.cancel_button = ttk.Button(button_bar, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(0, 8))
        self.export_button = ttk.Button(button_bar, text="Export frames", command=self._start)
        self.export_button.pack(side="left")

        ttk.Label(
            container,
            text="Only download videos you have permission to use. A long video can create thousands of images.",
            foreground="#666666",
            wraplength=620,
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(18, 0))

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
        if not str(output_root).strip():
            messagebox.showerror(APP_NAME, "Please choose an output folder.")
            return
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
            percent = min(95.0, (downloaded / total * 95.0)) if total else 0
            speed = data.get("_speed_str", "").strip()
            eta = data.get("_eta_str", "").strip()
            details = "Downloading video"
            if speed:
                details += f" — {speed}"
            if eta:
                details += f", ETA {eta}"
            self.events.put(("progress", (percent, details)))
        elif data.get("status") == "finished":
            self.events.put(("progress", (96.0, "Download complete; preparing frames…")))

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

            candidates = [
                path for path in temp_dir.iterdir()
                if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
            ]
            if not candidates:
                raise RuntimeError("The downloaded video file could not be found.")
            video_file = max(candidates, key=lambda path: path.stat().st_size)
            video_id = str(info.get("id") or "video")
            folder = output_root / safe_folder_name(str(info.get("title") or "youtube_video"), video_id)
            folder.mkdir(parents=True, exist_ok=True)

            self.events.put(("progress", (97.0, "Exporting one frame per second…")))
            command = make_ffmpeg_command(ffmpeg, video_file, folder / "frame_%06d.jpg")
            self.ffmpeg_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            _, stderr = self.ffmpeg_process.communicate()
            return_code = self.ffmpeg_process.returncode
            self.ffmpeg_process = None
            if self.cancel_event.is_set():
                raise Cancelled()
            if return_code:
                raise RuntimeError(stderr.strip() or "FFmpeg could not export the frames.")

            frame_count = sum(1 for _ in folder.glob("frame_*.jpg"))
            if frame_count == 0:
                raise RuntimeError("No frames were created.")
            self.events.put(("done", (folder, frame_count)))
        except Cancelled:
            self.events.put(("cancelled", None))
        except Exception as exc:
            if self.cancel_event.is_set():
                self.events.put(("cancelled", None))
            else:
                self.events.put(("error", str(exc)))
        finally:
            self.ffmpeg_process = None
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _cancel(self) -> None:
        self.cancel_event.set()
        self.status_var.set("Cancelling…")
        process = self.ffmpeg_process
        if process and process.poll() is None:
            process.terminate()

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
                    folder, frame_count = payload  # type: ignore[misc]
                    self.progress_var.set(100)
                    self.status_var.set(f"Done — exported {frame_count:,} frames.")
                    self._set_running(False)
                    if messagebox.askyesno(
                        APP_NAME,
                        f"Exported {frame_count:,} frames to:\n{folder}\n\nOpen the folder now?",
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

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

from core import VALID_INTERVALS, VIDEO_SUFFIXES, is_youtube_url, make_ffmpeg_command, safe_folder_name


APP_NAME = "Exportador de fotogramas de YouTube — Studio Moka"


class Cancelled(Exception):
    pass


def resource_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / relative


def find_deno() -> str:
    executable = "deno.exe" if os.name == "nt" else "deno"
    bundled = resource_path(executable)
    if bundled.is_file():
        return str(bundled)
    installed = shutil.which("deno")
    if installed:
        return installed
    raise RuntimeError("No se encontró Deno, necesario para descargar vídeos de YouTube.")


class FrameExporterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x600")
        self.root.minsize(760, 560)

        default_output = Path.home() / "Pictures" / "Fotogramas de YouTube"
        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(default_output))
        self.interval_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="Listo")
        self.progress_var = tk.DoubleVar(value=0)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.ffmpeg_process: subprocess.Popen[str] | None = None
        self.running = False

        self._build_ui()
        self.root.after(100, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=24)
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text=APP_NAME, font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )
        ttk.Label(
            container,
            text="Pega un enlace de YouTube y exporta fotogramas JPG de alta calidad.",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 20))

        self.logo_image = tk.PhotoImage(file=str(resource_path("assets/studio_moka_logo.png")))
        self.root.iconphoto(True, self.logo_image)
        ttk.Label(container, image=self.logo_image).grid(
            row=0, column=2, rowspan=2, sticky="ne", padx=(18, 0)
        )

        ttk.Label(container, text="Enlace de YouTube").grid(
            row=2, column=0, columnspan=3, sticky="w"
        )
        self.url_entry = ttk.Entry(container, textvariable=self.url_var)
        self.url_entry.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(5, 16))
        self.url_entry.focus_set()

        ttk.Label(container, text="Guardar fotogramas en").grid(
            row=4, column=0, columnspan=3, sticky="w"
        )
        self.output_entry = ttk.Entry(container, textvariable=self.output_var)
        self.output_entry.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=(0, 8))
        self.browse_button = ttk.Button(container, text="Examinar…", command=self._browse)
        self.browse_button.grid(row=5, column=2, sticky="e", pady=(5, 10))

        ttk.Label(container, text="Exportar un fotograma cada").grid(
            row=6, column=0, columnspan=3, sticky="w"
        )
        interval_bar = ttk.Frame(container)
        interval_bar.grid(row=7, column=0, columnspan=3, sticky="w", pady=(6, 18))
        self.interval_buttons: list[ttk.Radiobutton] = []
        for seconds in VALID_INTERVALS:
            label = f"{seconds} segundo" if seconds == 1 else f"{seconds} segundos"
            button = ttk.Radiobutton(
                interval_bar, text=label, value=seconds, variable=self.interval_var
            )
            button.pack(side="left", padx=(0, 18))
            self.interval_buttons.append(button)

        self.progress = ttk.Progressbar(container, variable=self.progress_var, maximum=100)
        self.progress.grid(row=8, column=0, columnspan=3, sticky="ew")
        ttk.Label(container, textvariable=self.status_var, wraplength=820).grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(7, 16)
        )

        button_bar = ttk.Frame(container)
        button_bar.grid(row=10, column=0, columnspan=3, sticky="e")
        self.cancel_button = ttk.Button(
            button_bar, text="Cancelar", command=self._cancel, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=(0, 8))
        self.export_button = ttk.Button(
            button_bar, text="Exportar fotogramas", command=self._start
        )
        self.export_button.pack(side="left")

        ttk.Label(
            container,
            text=(
                "Descarga únicamente vídeos que tengas permiso para utilizar. "
                "Un vídeo largo puede crear miles de imágenes."
            ),
            foreground="#666666",
            wraplength=820,
        ).grid(row=11, column=0, columnspan=3, sticky="w", pady=(22, 0))

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
        for button in self.interval_buttons:
            button.configure(state=state)
        self.cancel_button.configure(state="normal" if value else "disabled")

    def _start(self) -> None:
        url = self.url_var.get().strip()
        if not is_youtube_url(url):
            messagebox.showerror(APP_NAME, "Introduce un enlace válido de YouTube o youtu.be.")
            return

        output_text = self.output_var.get().strip()
        if not output_text:
            messagebox.showerror(APP_NAME, "Elige una carpeta de destino.")
            return

        interval = self.interval_var.get()
        if interval not in VALID_INTERVALS:
            messagebox.showerror(APP_NAME, "Elige un intervalo válido.")
            return

        output_root = Path(output_text).expanduser()
        try:
            output_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"No se pudo crear la carpeta de destino:\n{exc}")
            return

        self.cancel_event.clear()
        self.progress_var.set(0)
        self.status_var.set("Iniciando…")
        self._set_running(True)
        threading.Thread(
            target=self._worker,
            args=(url, output_root, interval),
            daemon=True,
        ).start()

    def _progress_hook(self, data: dict[str, object]) -> None:
        if self.cancel_event.is_set():
            raise Cancelled
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = min(95.0, float(downloaded) * 95.0 / float(total)) if total else 0.0
            speed = str(data.get("_speed_str") or "").strip()
            eta = str(data.get("_eta_str") or "").strip()
            details = "Descargando vídeo"
            if speed:
                details += f" — {speed}"
            if eta:
                details += f", tiempo restante {eta}"
            self.events.put(("progress", (percent, details)))
        elif status == "finished":
            self.events.put(("progress", (96.0, "Descarga completa; preparando fotogramas…")))

    def _worker(self, url: str, output_root: Path, interval: int) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="studio-moka-frames-"))
        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            deno = find_deno()
            self.events.put(("status", "Leyendo información del vídeo…"))
            options: dict[str, object] = {
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
                raise Cancelled

            candidates = [
                path
                for path in temp_dir.iterdir()
                if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
            ]
            if not candidates:
                raise RuntimeError("No se encontró el archivo de vídeo descargado.")
            video_file = max(candidates, key=lambda path: path.stat().st_size)
            video_id = str(info.get("id") or "video")
            folder = output_root / safe_folder_name(str(info.get("title") or "video_youtube"), video_id)
            folder.mkdir(parents=True, exist_ok=True)
            output_pattern = folder / "fotograma_%06d.jpg"

            self.events.put(("progress", (97.0, f"Exportando un fotograma cada {interval} segundo(s)…")))
            command = make_ffmpeg_command(ffmpeg, video_file, output_pattern, interval)
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flags,
            )
            self.ffmpeg_process = process
            _, stderr = process.communicate()
            self.ffmpeg_process = None

            if self.cancel_event.is_set():
                raise Cancelled
            if process.returncode:
                raise RuntimeError(stderr.strip() or "FFmpeg no pudo exportar los fotogramas.")

            frame_count = sum(1 for _ in folder.glob("fotograma_*.jpg"))
            if not frame_count:
                raise RuntimeError("No se creó ningún fotograma.")
            self.events.put(("done", (folder, frame_count)))
        except Cancelled:
            self.events.put(("cancelled", None))
        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            self.ffmpeg_process = None
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _cancel(self) -> None:
        self.cancel_event.set()
        self.status_var.set("Cancelando…")
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
                    self.status_var.set(f"Terminado — {frame_count} fotogramas exportados.")
                    self._set_running(False)
                    if messagebox.askyesno(
                        APP_NAME,
                        f"Se han exportado {frame_count} fotogramas en:\n{folder}\n\n¿Abrir la carpeta ahora?",
                    ):
                        os.startfile(folder)  # type: ignore[attr-defined]
                elif event == "cancelled":
                    self.progress_var.set(0)
                    self.status_var.set("Cancelado")
                    self._set_running(False)
                elif event == "error":
                    self.status_var.set("Error de exportación")
                    self._set_running(False)
                    messagebox.showerror(APP_NAME, f"No se pudieron exportar los fotogramas:\n\n{payload}")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _on_close(self) -> None:
        if self.running and not messagebox.askyesno(
            APP_NAME, "Hay una exportación en curso. ¿Cancelarla y salir?"
        ):
            return
        if self.running:
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


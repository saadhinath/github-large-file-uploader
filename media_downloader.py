#!/usr/bin/env python3
"""
Simple Media Downloader
Windows + Linux + Termux

Features:
- MP4 video
- MP3 audio
- Folder selection
- Progress
- Error handling
- Dark Tkinter GUI
- Termux automatic dependency setup
- CLI fallback when Tkinter is unavailable

Important:
Only download media that you own or are authorized to download.
Spotify protected-track downloading is not supported.
"""

import os
import sys
import shutil
import subprocess
import importlib.util
import threading
from pathlib import Path


# ============================================================
# Platform detection
# ============================================================

IS_TERMUX = (
    "TERMUX_VERSION" in os.environ
    or "com.termux" in os.environ.get("PREFIX", "")
)

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")


# ============================================================
# Termux-only automatic setup
# ============================================================

def run_command(command):
    try:
        return subprocess.run(
            command,
            check=True
        ).returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def setup_termux():
    """
    Runs ONLY on Termux.

    Windows/Linux are completely unaffected.
    """

    print("\n" + "=" * 58)
    print("TERMUX SETUP")
    print("=" * 58)

    # Python is already running this program, so there is no
    # reason to install Python again.

    # FFmpeg
    if shutil.which("ffmpeg") is None:
        print("\n[SETUP] FFmpeg is missing.")
        print("[SETUP] Installing FFmpeg...")

        if not run_command(["pkg", "install", "ffmpeg", "-y"]):
            print("\n[ERROR] Could not install FFmpeg.")
            print("Try manually:")
            print("pkg update")
            print("pkg install ffmpeg -y")
            return False

        print("[OK] FFmpeg installed.")
    else:
        print("[OK] FFmpeg already installed.")

    # yt-dlp
    if importlib.util.find_spec("yt_dlp") is None:
        print("\n[SETUP] yt-dlp is missing.")
        print("[SETUP] Installing yt-dlp...")

        if not run_command([
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "yt-dlp"
        ]):
            print("\n[ERROR] Could not install yt-dlp.")
            print("Try manually:")
            print("pip install -U yt-dlp")
            return False

        print("[OK] yt-dlp installed.")
    else:
        print("[OK] yt-dlp already installed.")

    print("\n[OK] Termux setup complete.")
    return True


# Only Termux executes the automatic setup.
if IS_TERMUX:
    if not setup_termux():
        sys.exit(1)


# ============================================================
# yt-dlp import
# ============================================================

if importlib.util.find_spec("yt_dlp") is None:
    print("\n[ERROR] yt-dlp is not installed.")
    print("Install it with:")
    print("    python -m pip install -U yt-dlp")
    sys.exit(1)

import yt_dlp


# ============================================================
# Helpers
# ============================================================

def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def default_download_folder():
    home = Path.home()

    # Termux shared Downloads folder
    termux_downloads = home / "storage" / "downloads"

    if IS_TERMUX and termux_downloads.exists():
        return str(termux_downloads)

    downloads = home / "Downloads"

    if downloads.exists():
        return str(downloads)

    return str(home)


def validate_url(url):
    url = url.strip()

    if not url:
        return False, "Please enter a URL."

    lower = url.lower()

    if "spotify.com" in lower:
        return False, (
            "Spotify protected track downloading is not supported."
        )

    if not (
        lower.startswith("http://")
        or lower.startswith("https://")
    ):
        return False, "URL must start with http:// or https://."

    return True, ""


# ============================================================
# Downloader engine
# ============================================================

class MediaDownloader:

    def __init__(self):
        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True

    def clean_error(self, error):
        error = str(error).strip()

        if "Unsupported URL" in error:
            return "This URL is not supported."

        if "Private" in error:
            return "This media is private."

        if "Sign in" in error:
            return "This media requires authentication."

        if "not available" in error.lower():
            return "This media is not available."

        if "ffmpeg" in error.lower():
            return "FFmpeg is required for this operation."

        return error[:1000]

    def progress_hook(self, data, callback):
        if self.cancel_requested:
            raise Exception("Download cancelled.")

        status = data.get("status")

        if status == "downloading":

            downloaded = data.get("downloaded_bytes", 0)
            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
            )

            percent = 0.0

            if total:
                percent = downloaded / total * 100

            speed = data.get("speed")
            eta = data.get("eta")

            speed_text = "--"

            if speed:
                speed_text = (
                    f"{speed / 1024 / 1024:.2f} MB/s"
                )

            eta_text = "--"

            if eta is not None:
                eta_text = f"{eta}s"

            callback(
                "progress",
                percent,
                f"{percent:.1f}% • {speed_text} • ETA {eta_text}"
            )

        elif status == "finished":

            callback(
                "progress",
                100,
                "Download finished. Processing..."
            )

    def download(
        self,
        url,
        folder,
        mode,
        quality,
        callback
    ):
        self.cancel_requested = False

        valid, error = validate_url(url)

        if not valid:
            callback("error", 0, error)
            return False

        folder = os.path.abspath(
            os.path.expanduser(folder)
        )

        try:
            os.makedirs(
                folder,
                exist_ok=True
            )
        except Exception as exc:
            callback(
                "error",
                0,
                f"Cannot create folder:\n{exc}"
            )
            return False

        if mode == "audio":

            if not ffmpeg_available():
                callback(
                    "error",
                    0,
                    "FFmpeg is required for MP3."
                )
                return False

            format_string = "bestaudio/best"

            postprocessors = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }
            ]

        else:

            postprocessors = []

            if quality == "720p":
                format_string = (
                    "bestvideo[height<=720][ext=mp4]+"
                    "bestaudio[ext=m4a]/"
                    "best[height<=720][ext=mp4]/best"
                )

            elif quality == "480p":
                format_string = (
                    "bestvideo[height<=480][ext=mp4]+"
                    "bestaudio[ext=m4a]/"
                    "best[height<=480][ext=mp4]/best"
                )

            else:
                format_string = (
                    "bestvideo[ext=mp4]+"
                    "bestaudio[ext=m4a]/"
                    "best[ext=mp4]/best"
                )

        options = {
            "format": format_string,
            "outtmpl": os.path.join(
                folder,
                "%(title)s.%(ext)s"
            ),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 3,
            "continuedl": True,
            "postprocessors": postprocessors,
            "progress_hooks": [
                lambda data: self.progress_hook(
                    data,
                    callback
                )
            ]
        }

        if mode == "video":
            options["merge_output_format"] = "mp4"

        try:

            callback(
                "status",
                0,
                "Connecting..."
            )

            with yt_dlp.YoutubeDL(options) as ydl:

                info = ydl.extract_info(
                    url,
                    download=False
                )

                if not info:
                    raise Exception(
                        "Unable to retrieve media information."
                    )

                title = info.get(
                    "title",
                    "Unknown media"
                )

                callback(
                    "status",
                    0,
                    f"Found: {title}"
                )

                ydl.download([url])

            if self.cancel_requested:
                callback(
                    "error",
                    0,
                    "Download cancelled."
                )
                return False

            callback(
                "complete",
                100,
                f"Saved successfully:\n{title}"
            )

            return True

        except yt_dlp.utils.DownloadError as exc:

            callback(
                "error",
                0,
                self.clean_error(exc)
            )

            return False

        except Exception as exc:

            callback(
                "error",
                0,
                self.clean_error(exc)
            )

            return False


# ============================================================
# GUI
# ============================================================

def launch_gui():

    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except ImportError:
        return False

    root = tk.Tk()

    root.title("Media Downloader")
    root.geometry("760x560")
    root.minsize(680, 500)
    root.configure(bg="#0b0f14")

    bg = "#0b0f14"
    panel = "#111820"
    panel2 = "#151e28"
    text = "#e8eef5"
    muted = "#8b98a8"
    accent = "#5b9cff"
    danger = "#ff5c6c"
    success = "#4fd18b"

    style = ttk.Style()

    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "TProgressbar",
        troughcolor=panel2,
        background=accent,
        bordercolor=panel2,
        lightcolor=accent,
        darkcolor=accent
    )

    downloader = MediaDownloader()

    url_var = tk.StringVar()
    folder_var = tk.StringVar(
        value=default_download_folder()
    )

    mode_var = tk.StringVar(
        value="video"
    )

    quality_var = tk.StringVar(
        value="best"
    )

    status_var = tk.StringVar(
        value="Ready"
    )

    percent_var = tk.StringVar(
        value="0%"
    )

    def browse_folder():
        selected = filedialog.askdirectory(
            title="Select Download Folder"
        )

        if selected:
            folder_var.set(selected)

    def gui_callback(kind, percent, message):

        def update():

            progress["value"] = percent
            percent_var.set(
                f"{percent:.1f}%"
            )
            status_var.set(message)

            if kind == "error":
                status_label.configure(
                    foreground=danger
                )

            elif kind == "complete":
                status_label.configure(
                    foreground=success
                )

            else:
                status_label.configure(
                    foreground=muted
                )

        root.after(0, update)

    def start_download():

        url = url_var.get().strip()
        folder = folder_var.get().strip()
        mode = mode_var.get()
        quality = quality_var.get()

        valid, error = validate_url(url)

        if not valid:
            messagebox.showerror(
                "Invalid URL",
                error
            )
            return

        if not folder:
            messagebox.showerror(
                "Folder Error",
                "Select a download folder."
            )
            return

        if mode == "audio" and not ffmpeg_available():
            messagebox.showerror(
                "FFmpeg Required",
                "FFmpeg is required for MP3 conversion."
            )
            return

        download_button.configure(
            state="disabled"
        )

        cancel_button.configure(
            state="normal"
        )

        progress["value"] = 0
        percent_var.set("0%")
        status_var.set("Preparing...")
        status_label.configure(
            foreground=muted
        )

        def worker():

            downloader.download(
                url,
                folder,
                mode,
                quality,
                gui_callback
            )

            root.after(
                0,
                lambda: download_button.configure(
                    state="normal"
                )
            )

            root.after(
                0,
                lambda: cancel_button.configure(
                    state="disabled"
                )
            )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def cancel_download():

        downloader.cancel()

        status_var.set(
            "Cancelling..."
        )

    def mode_changed():

        if mode_var.get() == "audio":

            quality_combo.configure(
                state="disabled"
            )

        else:

            quality_combo.configure(
                state="readonly"
            )

    def clear_url():

        url_var.set("")
        progress["value"] = 0
        percent_var.set("0%")
        status_var.set("Ready")

    # Header
    header = tk.Frame(
        root,
        bg=bg
    )
    header.pack(
        fill="x",
        padx=32,
        pady=(28, 12)
    )

    tk.Label(
        header,
        text="MEDIA DOWNLOADER",
        font=("Arial", 22, "bold"),
        bg=bg,
        fg=text
    ).pack(anchor="w")

    tk.Label(
        header,
        text="Simple • Fast • Windows • Linux • Termux",
        font=("Arial", 10),
        bg=bg,
        fg=muted
    ).pack(
        anchor="w",
        pady=(4, 0)
    )

    # Main panel
    main = tk.Frame(
        root,
        bg=panel
    )
    main.pack(
        fill="both",
        expand=True,
        padx=32,
        pady=12
    )

    tk.Label(
        main,
        text="MEDIA URL",
        font=("Arial", 9, "bold"),
        bg=panel,
        fg=muted
    ).pack(
        anchor="w",
        padx=24,
        pady=(24, 7)
    )

    url_frame = tk.Frame(
        main,
        bg=panel2
    )
    url_frame.pack(
        fill="x",
        padx=24
    )

    url_entry = tk.Entry(
        url_frame,
        textvariable=url_var,
        font=("Arial", 11),
        bg=panel2,
        fg=text,
        insertbackground=text,
        relief="flat",
        bd=0
    )
    url_entry.pack(
        side="left",
        fill="x",
        expand=True,
        padx=12,
        pady=12
    )

    tk.Button(
        url_frame,
        text="×",
        command=clear_url,
        font=("Arial", 13, "bold"),
        bg=panel2,
        fg=muted,
        activebackground=panel2,
        activeforeground=text,
        relief="flat",
        bd=0,
        cursor="hand2"
    ).pack(
        side="right",
        padx=10
    )

    # Folder
    tk.Label(
        main,
        text="DOWNLOAD LOCATION",
        font=("Arial", 9, "bold"),
        bg=panel,
        fg=muted
    ).pack(
        anchor="w",
        padx=24,
        pady=(22, 7)
    )

    folder_frame = tk.Frame(
        main,
        bg=panel2
    )
    folder_frame.pack(
        fill="x",
        padx=24
    )

    tk.Entry(
        folder_frame,
        textvariable=folder_var,
        font=("Arial", 10),
        bg=panel2,
        fg=text,
        insertbackground=text,
        relief="flat",
        bd=0
    ).pack(
        side="left",
        fill="x",
        expand=True,
        padx=12,
        pady=11
    )

    tk.Button(
        folder_frame,
        text="Browse",
        command=browse_folder,
        font=("Arial", 9, "bold"),
        bg=accent,
        fg="white",
        activebackground=accent,
        relief="flat",
        bd=0,
        padx=14,
        pady=8,
        cursor="hand2"
    ).pack(
        side="right",
        padx=7
    )

    # Options
    options = tk.Frame(
        main,
        bg=panel
    )
    options.pack(
        fill="x",
        padx=24,
        pady=22
    )

    mode_box = tk.Frame(
        options,
        bg=panel
    )
    mode_box.pack(
        side="left",
        fill="x",
        expand=True
    )

    tk.Label(
        mode_box,
        text="FORMAT",
        font=("Arial", 9, "bold"),
        bg=panel,
        fg=muted
    ).pack(anchor="w")

    tk.Radiobutton(
        mode_box,
        text="MP4 Video",
        variable=mode_var,
        value="video",
        command=mode_changed,
        bg=panel,
        fg=text,
        selectcolor=panel2,
        activebackground=panel,
        activeforeground=text
    ).pack(
        side="left",
        pady=8
    )

    tk.Radiobutton(
        mode_box,
        text="MP3 Audio",
        variable=mode_var,
        value="audio",
        command=mode_changed,
        bg=panel,
        fg=text,
        selectcolor=panel2,
        activebackground=panel,
        activeforeground=text
    ).pack(
        side="left",
        pady=8,
        padx=12
    )

    quality_box = tk.Frame(
        options,
        bg=panel
    )
    quality_box.pack(
        side="right"
    )

    tk.Label(
        quality_box,
        text="QUALITY",
        font=("Arial", 9, "bold"),
        bg=panel,
        fg=muted
    ).pack(anchor="w")

    quality_combo = ttk.Combobox(
        quality_box,
        textvariable=quality_var,
        values=("best", "720p", "480p"),
        state="readonly",
        width=10
    )
    quality_combo.pack(
        pady=6
    )

    # Progress
    progress = ttk.Progressbar(
        main,
        orient="horizontal",
        mode="determinate",
        maximum=100
    )
    progress.pack(
        fill="x",
        padx=24
    )

    progress_info = tk.Frame(
        main,
        bg=panel
    )
    progress_info.pack(
        fill="x",
        padx=24,
        pady=(8, 10)
    )

    status_label = tk.Label(
        progress_info,
        textvariable=status_var,
        font=("Arial", 9),
        bg=panel,
        fg=muted,
        anchor="w"
    )
    status_label.pack(
        side="left",
        fill="x",
        expand=True
    )

    tk.Label(
        progress_info,
        textvariable=percent_var,
        font=("Arial", 9, "bold"),
        bg=panel,
        fg=text
    ).pack(side="right")

    # Buttons
    buttons = tk.Frame(
        main,
        bg=panel
    )
    buttons.pack(
        fill="x",
        padx=24,
        pady=(10, 24)
    )

    cancel_button = tk.Button(
        buttons,
        text="Cancel",
        command=cancel_download,
        font=("Arial", 10, "bold"),
        bg=panel2,
        fg=text,
        activebackground=panel2,
        relief="flat",
        bd=0,
        padx=22,
        pady=11,
        cursor="hand2",
        state="disabled"
    )
    cancel_button.pack(
        side="right"
    )

    download_button = tk.Button(
        buttons,
        text="DOWNLOAD",
        command=start_download,
        font=("Arial", 10, "bold"),
        bg=accent,
        fg="white",
        activebackground=accent,
        relief="flat",
        bd=0,
        padx=25,
        pady=11,
        cursor="hand2"
    )
    download_button.pack(
        side="right",
        padx=(0, 10)
    )

    tk.Label(
        root,
        text="Download only media you own or are authorized to save.",
        font=("Arial", 8),
        bg=bg,
        fg=muted
    ).pack(
        pady=(0, 15)
    )

    url_entry.focus()
    root.mainloop()

    return True


# ============================================================
# CLI fallback
# ============================================================

def launch_cli():

    downloader = MediaDownloader()
    folder = default_download_folder()

    print("\n" + "=" * 58)
    print("              MEDIA DOWNLOADER")
    print("=" * 58)
    print("        Windows • Linux • Termux")
    print("=" * 58)

    while True:

        print("\n1. Download MP4")
        print("2. Download MP3")
        print("3. Change folder")
        print("4. Exit")

        choice = input("\nSelect: ").strip()

        if choice == "4":
            break

        if choice == "3":

            new_folder = input(
                "Enter folder: "
            ).strip()

            if new_folder:
                folder = os.path.expanduser(
                    new_folder
                )

            continue

        if choice not in ("1", "2"):
            print("[ERROR] Invalid choice.")
            continue

        url = input(
            "\nEnter URL: "
        ).strip()

        if choice == "1":

            mode = "video"

            print("\nQuality:")
            print("1. Best")
            print("2. 720p")
            print("3. 480p")

            q = input("Select: ").strip()

            quality = {
                "1": "best",
                "2": "720p",
                "3": "480p"
            }.get(q, "best")

        else:

            mode = "audio"
            quality = "best"

        def callback(kind, percent, message):

            if kind == "progress":

                print(
                    f"\r{message}",
                    end="",
                    flush=True
                )

            elif kind == "status":

                print(f"\n[*] {message}")

            elif kind == "complete":

                print(f"\n[OK] {message}")

            elif kind == "error":

                print(f"\n[ERROR] {message}")

        downloader.download(
            url,
            folder,
            mode,
            quality,
            callback
        )

        print()


# ============================================================
# Main
# ============================================================

def main():

    # Termux setup has already happened above.
    # Windows and Linux NEVER execute pkg commands.

    try:
        if launch_gui():
            return
    except Exception as exc:
        print(f"[GUI] Could not start: {exc}")

    launch_cli()


if __name__ == "__main__":
    main()

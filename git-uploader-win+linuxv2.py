#!/usr/bin/env python3
"""
GitHub Easy File Uploader
Cross-platform Windows/Linux version
Based on the uploaded model specification.
"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Tkinter is part of most Python installations.
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None
    filedialog = None


# -------------------- COLORS --------------------

RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
WHITE = "\033[97m"
BOLD = "\033[1m"


def enable_colors():
    """Enable ANSI colors on Windows where possible."""
    if os.name == "nt":
        os.system("")  # Enables ANSI processing on modern Windows terminals.


def c(text, color):
    return f"{color}{text}{RESET}"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    input("\nPress Enter to continue...")


def progress(message="Processing", width=30, delay=0.015):
    print(message)
    for i in range(width + 1):
        filled = "█" * i
        empty = " " * (width - i)
        percent = int(i * 100 / width)
        print(f"\r[{filled}{empty}] {percent:3d}%", end="", flush=True)
        time.sleep(delay)
    print()


def run_command(command, cwd=None, check=False, capture=False):
    """Run a command safely without shell=True."""
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=capture,
            check=check,
        )
        return result
    except FileNotFoundError:
        return None
    except OSError as exc:
        print(c(str(exc), RED))
        return None


def command_exists(command):
    result = run_command([command, "--version"], capture=True)
    return result is not None and result.returncode == 0


# -------------------- GIT HELPERS --------------------

def git_version():
    result = run_command(["git", "--version"], capture=True)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def git_lfs_version():
    result = run_command(["git", "lfs", "version"], capture=True)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def repo_name_from_url(url):
    cleaned = url.rstrip("/")
    name = cleaned.rsplit("/", 1)[-1]
    if name.lower().endswith(".git"):
        name = name[:-4]
    return name or "repository"


def validate_repo_url(url):
    return bool(
        re.match(r"^https?://github\.com/[^/\s]+/[^/\s]+/?(?:\.git)?$", url)
    )


# -------------------- FILE DIALOG --------------------

def choose_file():
    if filedialog is None:
        print(c("Tkinter is not available. Enter the file path manually.", YELLOW))
        return input("Path of uploading file: ").strip().strip('"')

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilename(title="Select file to upload")
    finally:
        root.destroy()

    return selected


def choose_directory():
    if filedialog is None:
        return input("Repository path: ").strip().strip('"')

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title="Select Git repository")
    finally:
        root.destroy()

    return selected


# -------------------- REPOSITORY FILES --------------------

def list_repo_files(repo):
    repo = Path(repo)
    files = []

    for path in repo.rglob("*"):
        if not path.is_file():
            continue

        # Do not show files inside .git.
        try:
            path.relative_to(repo / ".git")
            continue
        except ValueError:
            pass

        files.append(path)

    return sorted(files, key=lambda p: str(p).lower())


def display_repo_files(repo):
    files = list_repo_files(repo)

    print("\n" + "-" * 60)
    print("FILES IN REPOSITORY")
    print("-" * 60)

    if not files:
        print("No files found.")
        return files

    for number, path in enumerate(files, 1):
        relative = path.relative_to(repo)
        print(f"{number:3d}  {relative}")

    print("-" * 60)
    return files


# -------------------- WINDOWS PACKAGE MENU --------------------

def windows_update():
    clear()
    header("WINDOWS - UPDATE / INSTALL PACKAGE")

    print("Checking Git...")
    version = git_version()

    if version is None:
        print(c("❌ Git is not installed.", RED))
        print("Please install Git for Windows first.")
        print("Official installer: https://git-scm.com/download/win")
        pause()
        return

    print(c(f"✅ {version}", GREEN))
    print("\nChecking Git LFS...")

    lfs = git_lfs_version()

    if lfs is None:
        print(c("❌ Git LFS is not available.", RED))
        print("Install Git LFS, then run this option again.")
        print("Git LFS: https://git-lfs.com/")
        pause()
        return

    print(c(f"✅ {lfs}", GREEN))

    print("\nRunning: git lfs install")
    result = run_command(["git", "lfs", "install"], capture=True)

    if result and result.returncode == 0:
        print(c("\n==================================================", GREEN))
        print(c("✅ Git and Git LFS are ready!", GREEN))
        print(c("==================================================", GREEN))
    else:
        print(c("\n❌ Git LFS setup failed.", RED))
        if result:
            print(result.stderr or result.stdout)

    pause()


# -------------------- LINUX PACKAGE MENU --------------------

def linux_update():
    clear()
    header("LINUX - UPDATE / INSTALL PACKAGE")

    if not command_exists("git"):
        print(c("❌ Git is not installed.", RED))
        print("Install Git using your Linux distribution's package manager.")
        pause()
        return

    print(c("Git is installed.", GREEN))
    print("\nThe model specifies these commands:")
    print("  sudo apt update")
    print("  sudo apt install git-lfs -y")
    print("  git lfs install")

    print("\nThe sudo password will be requested by sudo directly.")
    print("Running the commands now...\n")

    commands = [
        ["sudo", "apt", "update"],
        ["sudo", "apt", "install", "git-lfs", "-y"],
        ["git", "lfs", "install"],
    ]

    for command in commands:
        print(c("$ " + " ".join(command), CYAN))
        result = run_command(command)

        if result is None or result.returncode != 0:
            print(c("\n❌ Command failed:", RED))
            print(" ".join(command))
            pause()
            return

    print(c("\n✅ Git LFS setup completed successfully!", GREEN))
    pause()


# -------------------- UPLOAD --------------------

def clone_repository(url):
    name = repo_name_from_url(url)
    destination = Path.cwd() / name

    # If the directory already exists and is a Git repository, reuse it.
    if (destination / ".git").is_dir():
        print(c(f"Repository already exists: {destination}", YELLOW))
        return destination

    if destination.exists():
        print(c(f"❌ Directory already exists: {destination}", RED))
        print("Choose another working directory or remove/rename that directory.")
        return None

    print("\n📥 Cloning repository...")
    result = run_command(["git", "clone", url, str(destination)], capture=True)

    if result is None or result.returncode != 0:
        print(c("❌ Git clone failed.", RED))
        if result:
            print(result.stderr or result.stdout)
        return None

    print(c("✅ Repository cloned successfully.", GREEN))
    return destination


def choose_repo_file(repo):
    files = display_repo_files(repo)

    if not files:
        return None

    while True:
        value = input("Select the file you want to upload: ").strip()

        try:
            number = int(value)
        except ValueError:
            print(c("❌ Enter a valid number.", RED))
            continue

        if 1 <= number <= len(files):
            return files[number - 1]

        print(c("❌ Invalid selection.", RED))


def upload_process():
    clear()
    header("START UPLOADING PROCESS")

    url = input(
        "\nGive your repository HTTPS ID:\n"
        "Example: https://github.com/saadhinath/github-large-file-uploader.git\n"
        "Repository URL: "
    ).strip()

    if not validate_repo_url(url):
        print(c("\n❌ Invalid GitHub HTTPS repository URL.", RED))
        pause()
        return

    repo = clone_repository(url)
    if repo is None:
        pause()
        return

    print(f"\nRepository: {repo}")

    source = choose_file()
    if not source:
        print(c("❌ No file selected.", RED))
        pause()
        return

    source = Path(source).expanduser().resolve()

    if not source.is_file():
        print(c("❌ Selected file does not exist.", RED))
        pause()
        return

    # Prevent copying a file onto itself.
    try:
        if source.parent == repo.resolve() and source.is_file():
            print(c("The selected file is already inside the repository.", YELLOW))
        else:
            destination = repo / source.name
            print(f"\nCopying:\n{source}\n↓\n{destination}")
            shutil.copy2(source, destination)
            print(c("✅ File copied to repository.", GREEN))
    except OSError as exc:
        print(c(f"❌ Could not copy file: {exc}", RED))
        pause()
        return

    progress("\nScanning to repository...", 20)

    selected = choose_repo_file(repo)
    if selected is None:
        pause()
        return

    relative = selected.relative_to(repo)
    filename = str(relative)

    print(f"\nSelected file: {filename}")

    # Git LFS is useful for large binary files. If LFS is available,
    # track common large/binary formats before adding them.
    lfs_extensions = {
        ".apk", ".aab", ".iso", ".img", ".zip", ".7z", ".rar",
        ".tar", ".gz", ".mp4", ".mkv", ".avi", ".mov", ".webm",
        ".mp3", ".wav", ".flac", ".m4a"
    }

    if selected.suffix.lower() in lfs_extensions and git_lfs_version():
        print("\nConfiguring Git LFS for this file...")
        lfs_result = run_command(
            ["git", "lfs", "track", filename],
            cwd=repo,
            capture=True,
        )

        if lfs_result and lfs_result.returncode == 0:
            # .gitattributes is required after git lfs track.
            run_command(["git", "add", ".gitattributes"], cwd=repo)

    print("\nAdding file...")
    result = run_command(["git", "add", "--", filename], cwd=repo, capture=True)

    if result is None or result.returncode != 0:
        print(c("❌ git add failed.", RED))
        if result:
            print(result.stderr or result.stdout)
        pause()
        return

    commit_message = f"Add {Path(filename).name}"

    print(f"Creating commit: {commit_message}")
    result = run_command(
        ["git", "commit", "-m", commit_message],
        cwd=repo,
        capture=True,
    )

    if result is None or result.returncode != 0:
        output = ""
        if result:
            output = (result.stdout or "") + (result.stderr or "")

        # A clean working tree is not an upload success.
        if "nothing to commit" in output.lower():
            print(c("❌ Nothing new to commit.", RED))
        else:
            print(c("❌ Commit failed.", RED))
            print(output)

        pause()
        return

    print("\n🚀 Uploading to GitHub...")
    result = run_command(
        ["git", "push", "origin", "main"],
        cwd=repo,
        capture=False,
    )

    if result is not None and result.returncode == 0:
        progress("\nUploading...", 20)
        print(c("\n==================================================", GREEN))
        print(c("✅ File uploaded successfully!", GREEN))
        print(c("==================================================", GREEN))
        print(c(f"📄 File: {filename}", BLUE))
        print(f"📦 Repository: {repo.name}")
        print("🌿 Branch: main")
    else:
        print(c("\n==================================================", RED))
        print(c("❌ Upload failed!", RED))
        print(c("==================================================", RED))
        print("Check the Git error above.")

    pause()


# -------------------- DELETE --------------------

def delete_process():
    clear()
    header("DELETE GITHUB FILE")

    repo_input = input(
        "\nGive the path of your repository:\n"
        "Example: C:\\Users\\YourName\\Documents\\MyProject\n"
        "or: /home/kali/MyProject\n"
        "Repository path: "
    ).strip().strip('"')

    repo = Path(repo_input).expanduser().resolve()

    if not repo.is_dir():
        print(c("❌ Repository directory does not exist.", RED))
        pause()
        return

    if not (repo / ".git").is_dir():
        print(c("❌ This directory is not a Git repository.", RED))
        pause()
        return

    files = display_repo_files(repo)

    if not files:
        pause()
        return

    while True:
        value = input("Select the file you want to delete: ").strip()

        try:
            number = int(value)
        except ValueError:
            print(c("❌ Enter a valid number.", RED))
            continue

        if 1 <= number <= len(files):
            selected = files[number - 1]
            break

        print(c("❌ Invalid selection.", RED))

    relative = selected.relative_to(repo)

    print(f'\nAre you sure you want to delete "{relative}"?')
    print("1  Yes")
    print("2  No")

    confirm = input("Select: ").strip()

    if confirm != "1":
        print(c("Deletion cancelled.", YELLOW))
        pause()
        return

    print("\nRunning git rm...")
    result = run_command(
        ["git", "rm", "--", str(relative)],
        cwd=repo,
        capture=True,
    )

    if result is None or result.returncode != 0:
        print(c("❌ git rm failed.", RED))
        if result:
            print(result.stderr or result.stdout)
        pause()
        return

    commit_message = f"Delete {Path(relative).name}"

    print(f"Creating commit: {commit_message}")
    result = run_command(
        ["git", "commit", "-m", commit_message],
        cwd=repo,
        capture=True,
    )

    if result is None or result.returncode != 0:
        print(c("❌ Commit failed.", RED))
        if result:
            print(result.stderr or result.stdout)
        pause()
        return

    print("\nPushing deletion to GitHub...")
    result = run_command(
        ["git", "push", "origin", "main"],
        cwd=repo,
        capture=False,
    )

    if result is not None and result.returncode == 0:
        print(c("\n==================================================", GREEN))
        print(c("✅ File deleted successfully!", GREEN))
        print(c("==================================================", GREEN))
        print(c(f"🗑️ File: {relative}", BLUE))
        print(f"📦 Repository: {repo.name}")
        print("🌿 Branch: main")
    else:
        print(c("\n❌ Delete push failed.", RED))

    pause()


# -------------------- INFORMATION --------------------

SUPPORTED = [
    ("🐍 Python", [".py", ".pyw", ".pyi"]),
    ("☕ Java", [".java", ".jar", ".class"]),
    ("🟦 C/C++", [".c", ".h", ".cpp", ".hpp", ".cc"]),
    ("🟨 JavaScript", [".js", ".mjs", ".cjs"]),
    ("🌐 Web", [".html", ".css", ".scss", ".xml"]),
    ("📱 Android", [".kt", ".java", ".gradle", ".aab", ".apk"]),
    ("🦀 Rust", [".rs"]),
    ("🐹 Go", [".go"]),
    ("💎 Ruby", [".rb"]),
    ("🐘 PHP", [".php"]),
    ("🦘 Dart", [".dart"]),
    ("📝 Text", [".txt", ".md", ".log", ".csv"]),
    ("⚙️ Config", [".json", ".yaml", ".yml", ".toml", ".ini", ".env"]),
    ("🖼️ Images", [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]),
    ("🎵 Audio", [".mp3", ".wav", ".ogg", ".flac", ".m4a"]),
    ("🎬 Video", [".mp4", ".mkv", ".avi", ".mov", ".webm"]),
    ("📦 Archives", [".zip", ".tar", ".gz", ".7z", ".rar"]),
    ("💿 Disk images", [".iso", ".img"]),
    ("📄 Documents", [".pdf", ".docx", ".xlsx", ".pptx"]),
]


def information():
    clear()
    header("INFORMATION - SUPPORTED FORMATS")

    print("+----------------+-----------------------------------------------+")
    print("| Category       | Extensions                                    |")
    print("+----------------+-----------------------------------------------+")

    for category, extensions in SUPPORTED:
        extension_text = ", ".join(extensions)
        print(f"| {category:<14} | {extension_text:<45} |")

    print("+----------------+-----------------------------------------------+")
    print("\n* GitHub repository/file-size limits still apply.")
    print("* Large files may require Git LFS.")
    pause()


# -------------------- MENUS --------------------

def header(title):
    print("=" * 58)
    print("        GitHub Easy File Uploader")
    print(f"              {title}")
    print("                 By saadhinath")
    print("=" * 58)


def windows_menu():
    while True:
        clear()
        header("WINDOWS")
        print("\nMENU\n")
        print("01  Update / Install Package")
        print("02  Start Uploading Process")
        print("03  Delete GitHub File")
        print("04  Information")
        print("05  Exit")
        print("-" * 58)

        choice = input("Select: ").strip()

        if choice == "1" or choice == "01":
            windows_update()
        elif choice == "2" or choice == "02":
            upload_process()
        elif choice == "3" or choice == "03":
            delete_process()
        elif choice == "4" or choice == "04":
            information()
        elif choice == "5" or choice == "05":
            return
        else:
            print(c("❌ Invalid option.", RED))
            time.sleep(1)


def linux_menu():
    while True:
        clear()
        header("LINUX")
        print("\nMENU\n")
        print("01  Update / Install Package")
        print("02  Start Uploading Process")
        print("03  Delete GitHub File")
        print("04  Information")
        print("05  Exit")
        print("-" * 58)

        choice = input("Select: ").strip()

        if choice == "1" or choice == "01":
            linux_update()
        elif choice == "2" or choice == "02":
            upload_process()
        elif choice == "3" or choice == "03":
            delete_process()
        elif choice == "4" or choice == "04":
            information()
        elif choice == "5" or choice == "05":
            return
        else:
            print(c("❌ Invalid option.", RED))
            time.sleep(1)


def main():
    enable_colors()

    while True:
        clear()
        header("SELECT THE OS")
        print("\n01  Windows")
        print("02  Linux")
        print("03  Exit")
        print("_" * 58)

        choice = input("Select: ").strip()

        if choice == "1" or choice == "01":
            windows_menu()
        elif choice == "2" or choice == "02":
            linux_menu()
        elif choice == "3" or choice == "03":
            clear()
            print("=" * 58)
            print("Thank you for using GitHub Easy File Uploader!")
            print("=" * 58)
            break
        else:
            print(c("❌ Invalid option.", RED))
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\n\nProgram stopped by user.", YELLOW))
    except Exception as exc:
        print(c(f"\n❌ Unexpected error: {exc}", RED))
        print("The program has stopped safely.")

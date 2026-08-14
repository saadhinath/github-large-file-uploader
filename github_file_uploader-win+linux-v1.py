#!/usr/bin/env python3
"""
GitHub Easy File Uploader
Cross-platform Linux + Windows version.

Based on the supplied program model:
- Update / Install Package
- Start Uploading Process
- Delete GitHub File
- Information
- Exit

Requirements:
    Python 3.8+
    Git installed and available in PATH

Linux:
    Option 01 installs Git LFS using apt when available.

Windows:
    Option 01 checks for Git/Git LFS and opens the official Git download
    page if Git is not installed. It does not silently install software.
"""

from __future__ import annotations

import getpass
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path


APP_NAME = "GitHub Easy File Uploader"
DEFAULT_BRANCH = "main"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def pause(message: str = "\nPress Enter to continue...") -> None:
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        print()


def run_command(
    command: list[str],
    cwd: str | Path | None = None,
    check: bool = False,
    hide_input: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command while keeping output visible."""
    print("\n> " + " ".join(command))
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            check=check,
            text=True,
            stdin=subprocess.DEVNULL if hide_input else None,
        )
    except FileNotFoundError:
        print(f"\nCommand not found: {command[0]}")
        return subprocess.CompletedProcess(command, 127)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return subprocess.CompletedProcess(command, 130)


def command_output(
    command: list[str], cwd: str | Path | None = None
) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return result.returncode, result.stdout.strip()
    except FileNotFoundError:
        return 127, f"Command not found: {command[0]}"
    except OSError as exc:
        return 1, str(exc)


def git_available() -> bool:
    return shutil.which("git") is not None


def git_lfs_available() -> bool:
    if shutil.which("git-lfs"):
        return True
    code, _ = command_output(["git", "lfs", "version"])
    return code == 0


def normalize_repo_url(url: str) -> str:
    """Validate a GitHub HTTPS/SSH URL without modifying it unnecessarily."""
    url = url.strip()
    if not url:
        return ""

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return url

    if url.startswith("git@github.com:"):
        return url

    return ""


def repository_name_from_url(url: str) -> str:
    cleaned = url.rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned.rsplit("/", 1)[-1] or "repository"


def open_terminal_linux() -> bool:
    """Try to open a terminal emulator on Linux."""
    terminals = [
        ("x-terminal-emulator", ["x-terminal-emulator"]),
        ("gnome-terminal", ["gnome-terminal"]),
        ("konsole", ["konsole"]),
        ("xfce4-terminal", ["xfce4-terminal"]),
        ("mate-terminal", ["mate-terminal"]),
        ("xterm", ["xterm"]),
    ]

    for executable, command in terminals:
        if shutil.which(executable):
            try:
                subprocess.Popen(command)
                return True
            except OSError:
                pass

    return False


def install_update_package() -> None:
    clear_screen()
    print("=" * 58)
    print("             UPDATE / INSTALL PACKAGE")
    print("=" * 58)

    system = platform.system()

    if system == "Linux":
        if not shutil.which("sudo"):
            print("\n❌ sudo was not found.")
            print("Please install/configure sudo, then run this option again.")
            pause()
            return

        print("\nOpening a terminal is optional; this program can run the commands")
        print("in the current terminal so that sudo can request your password safely.")

        # apt is the package manager specified by the supplied model.
        if shutil.which("apt") is None:
            print("\n❌ apt was not found on this Linux system.")
            print("The model specifies apt, so automatic package installation cannot continue.")
            pause()
            return

        commands = [
            ["sudo", "apt", "update"],
            ["sudo", "apt", "install", "git-lfs", "-y"],
            ["git", "lfs", "install"],
        ]

        for command in commands:
            result = run_command(command)
            if result.returncode != 0:
                print("\n❌ Command failed.")
                pause()
                return

        print("\n✅ Git LFS setup completed successfully!")

    elif system == "Windows":
        print("\nWindows detected.")
        print("Git for Windows is required.")
        print("Git LFS is included with modern Git for Windows installations.")

        if not git_available():
            print("\n❌ Git is not installed or is not in PATH.")
            print("Opening the official Git for Windows download page...")
            webbrowser.open("https://git-scm.com/download/win")
            print("Install Git, restart this program, and choose option 01 again.")
            pause()
            return

        print("\n✅ Git is available.")
        if git_lfs_available():
            result = run_command(["git", "lfs", "install"])
            if result.returncode == 0:
                print("\n✅ Git LFS setup completed successfully!")
            else:
                print("\n❌ Git LFS setup failed.")
        else:
            print("\n❌ Git LFS is not available.")
            print("Please reinstall/update Git for Windows from the official site.")
            webbrowser.open("https://git-scm.com/download/win")

        pause()

    else:
        print(f"\n❌ Unsupported operating system: {system}")
        print("This program supports Linux and Windows.")
        pause()


def clone_repository(repo_url: str) -> Path | None:
    repo_name = repository_name_from_url(repo_url)
    destination = Path.cwd() / repo_name

    if destination.exists():
        print(f"\n📁 Repository folder already exists: {destination}")
        answer = input("Use this existing folder? [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            if (destination / ".git").is_dir():
                return destination
            print("❌ The existing folder is not a Git repository.")
            return None

        print("Please choose another working directory or rename the existing folder.")
        return None

    result = run_command(["git", "clone", repo_url])
    if result.returncode != 0:
        print("\n❌ Git clone failed.")
        return None

    if not destination.is_dir():
        print("\n❌ Clone completed but the repository folder was not found.")
        return None

    return destination


def list_repository_files(repo_path: Path) -> list[Path]:
    """List tracked files first, then untracked files, recursively."""
    files: list[Path] = []

    try:
        for path in repo_path.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts:
                continue
            files.append(path)
    except OSError as exc:
        print(f"\n❌ Could not scan repository: {exc}")
        return []

    return sorted(files, key=lambda p: str(p.relative_to(repo_path)).lower())


def show_repository_files(repo_path: Path) -> list[Path]:
    files = list_repository_files(repo_path)

    print("\n------------------------------")
    print("Files in repository")
    print("------------------------------")

    if not files:
        print("(No files found)")
    else:
        for index, file_path in enumerate(files, 1):
            print(f"{index:>3}  {file_path.relative_to(repo_path)}")

    print("------------------------------")
    return files


def ask_file_selection(files: list[Path], prompt: str) -> Path | None:
    if not files:
        print("\n❌ No files available.")
        return None

    while True:
        answer = input(prompt).strip()

        try:
            number = int(answer)
        except ValueError:
            print("❌ Enter a valid file number.")
            continue

        if 1 <= number <= len(files):
            return files[number - 1]

        print(f"❌ Choose a number from 1 to {len(files)}.")


def get_branch(repo_path: Path) -> str:
    code, branch = command_output(
        ["git", "branch", "--show-current"], cwd=repo_path
    )
    if code == 0 and branch:
        return branch

    # Fall back to the model's main branch.
    return DEFAULT_BRANCH


def upload_process() -> None:
    clear_screen()
    print("=" * 58)
    print("              START UPLOADING PROCESS")
    print("=" * 58)

    if not git_available():
        print("\n❌ Git is not installed or not available in PATH.")
        print("Choose option 01 first.")
        pause()
        return

    repo_url = input(
        "\nGive the path of your repository HTTPS ID:\n"
        "Example: https://github.com/saadhinath/github-large-file-uploader.git\n"
        "Repository URL: "
    ).strip()

    repo_url = normalize_repo_url(repo_url)
    if not repo_url:
        print("\n❌ Invalid repository URL.")
        pause()
        return

    repo_path = clone_repository(repo_url)
    if repo_path is None:
        pause()
        return

    print(f"\n📦 Repository: {repo_path.name}")
    print(f"📁 Local path: {repo_path}")

    source_text = input(
        "\nPath of uploading file:\n"
        "Example: /home/kali/Documents/test.apk\n"
        "File path: "
    ).strip().strip('"')

    source = Path(source_text).expanduser()

    if not source.is_file():
        print(f"\n❌ File not found: {source}")
        pause()
        return

    destination = repo_path / source.name

    try:
        if source.resolve() == destination.resolve():
            print("\nℹ️ The selected file is already inside the repository.")
        else:
            shutil.copy2(source, destination)
            print(f"\n📋 Copied: {source.name}")
    except OSError as exc:
        print(f"\n❌ Could not copy file: {exc}")
        pause()
        return

    files = show_repository_files(repo_path)
    selected = ask_file_selection(
        files,
        "\nSelect the file you want to upload:\nExample: 6\nSelection: ",
    )

    if selected is None:
        pause()
        return

    relative = selected.relative_to(repo_path)
    print(f"\nSelected file: {relative}")

    # Git paths should use forward slashes even on Windows.
    git_relative = relative.as_posix()

    add_result = run_command(["git", "add", "--", git_relative], cwd=repo_path)
    if add_result.returncode != 0:
        print("\n❌ Failed to add the file.")
        pause()
        return

    commit_message = f"Add {relative.name}"
    commit_result = run_command(
        ["git", "commit", "-m", commit_message], cwd=repo_path
    )

    if commit_result.returncode != 0:
        print("\n❌ Commit failed.")
        print("If Git says there is nothing to commit, the file may already be committed.")
        pause()
        return

    branch = get_branch(repo_path)

    # The model specifies origin main. If the cloned repository uses another
    # current branch, use that branch to avoid pushing the wrong branch.
    push_result = run_command(
        ["git", "push", "origin", branch],
        cwd=repo_path,
    )

    if push_result.returncode != 0:
        print("\n❌ Upload failed!")
        print("Git returned an error above.")
        print("\nIf GitHub asks for credentials:")
        print("  Username: enter your GitHub username.")
        print("  Password: enter your GitHub Personal Access Token.")
        print("  Do NOT display or share your token.")
        pause()
        return

    show_progress()

    print("\n" + "=" * 58)
    print("✅ File uploaded successfully!")
    print("=" * 58)
    print(f"📄 File: {relative}")
    print(f"📦 Repository: {repo_path.name}")
    print(f"🌿 Branch: {branch}")
    print("=" * 58)

    pause()


def show_progress() -> None:
    """Display a short completion meter after git push succeeds."""
    print("\nUploading...")
    width = 20
    for current in range(width + 1):
        filled = "█" * current
        empty = " " * (width - current)
        percent = current * 100 // width
        print(f"\r[{filled}{empty}] {percent:3d}%", end="", flush=True)
        time.sleep(0.025)
    print()


def delete_github_file() -> None:
    clear_screen()
    print("=" * 58)
    print("                 DELETE GITHUB FILE")
    print("=" * 58)

    if not git_available():
        print("\n❌ Git is not installed or not available in PATH.")
        pause()
        return

    repo_text = input(
        "\nGive the path of your repository:\n"
        "Example: /home/kali/MyProject\n"
        "Repository path: "
    ).strip().strip('"')

    repo_path = Path(repo_text).expanduser()

    if not repo_path.is_dir() or not (repo_path / ".git").is_dir():
        print("\n❌ This is not a valid Git repository.")
        pause()
        return

    files = show_repository_files(repo_path)
    selected = ask_file_selection(
        files,
        "\nSelect the file you want to delete:\nExample: 3\nSelection: ",
    )

    if selected is None:
        pause()
        return

    relative = selected.relative_to(repo_path)
    print(f'\nAre you sure you want to delete "{relative}"?')
    print("\n1  Yes")
    print("2  No")

    confirmation = input("Selection: ").strip().lower()
    if confirmation not in ("1", "y", "yes"):
        print("\nDeletion cancelled.")
        pause()
        return

    git_relative = relative.as_posix()

    result = run_command(["git", "rm", "--", git_relative], cwd=repo_path)
    if result.returncode != 0:
        print("\n❌ Could not remove the file with Git.")
        pause()
        return

    commit_result = run_command(
        ["git", "commit", "-m", f"Delete {relative.name}"],
        cwd=repo_path,
    )
    if commit_result.returncode != 0:
        print("\n❌ Commit failed.")
        pause()
        return

    branch = get_branch(repo_path)
    push_result = run_command(
        ["git", "push", "origin", branch],
        cwd=repo_path,
    )

    if push_result.returncode != 0:
        print("\n❌ Push failed!")
        print("Git returned an error above.")
        pause()
        return

    print("\n" + "=" * 58)
    print("✅ File deleted successfully!")
    print("=" * 58)
    print(f"🗑️ File: {relative}")
    print(f"📦 Repository: {repo_path.name}")
    print(f"🌿 Branch: {branch}")
    print("=" * 58)

    pause()


def information() -> None:
    clear_screen()
    print("=" * 78)
    print("                         INFORMATION")
    print("=" * 78)

    rows = [
        ("🐍 Python", ".py, .pyw, .pyi"),
        ("☕ Java", ".java, .jar, .class"),
        ("🟦 C/C++", ".c, .h, .cpp, .hpp, .cc"),
        ("🟨 JavaScript", ".js, .mjs, .cjs"),
        ("🌐 Web", ".html, .css, .scss, .xml"),
        ("📱 Android", ".kt, .java, .gradle, .aab, .apk*"),
        ("🦀 Rust", ".rs"),
        ("🐹 Go", ".go"),
        ("💎 Ruby", ".rb"),
        ("🐘 PHP", ".php"),
        ("🦘 Dart", ".dart"),
        ("📝 Text", ".txt, .md, .log, .csv"),
        ("⚙️ Config", ".json, .yaml, .yml, .toml, .ini, .env"),
        ("🖼️ Images", ".png, .jpg, .jpeg, .gif, .webp, .svg"),
        ("🎵 Audio", ".mp3, .wav, .ogg, .flac, .m4a"),
        ("🎬 Video", ".mp4, .mkv, .avi, .mov, .webm"),
        ("📦 Archives", ".zip, .tar, .gz, .7z, .rar"),
        ("💿 Disk images", ".iso, .img"),
        ("📄 Documents", ".pdf, .docx, .xlsx, .pptx"),
    ]

    print("+----------------+----------------------------------------------+")
    print("| Category       | Extensions                                   |")
    print("+----------------+----------------------------------------------+")
    for category, extensions in rows:
        print(f"| {category:<14} | {extensions:<44} |")
    print("+----------------+----------------------------------------------+")
    print("\n* GitHub has size/file restrictions; Git LFS may be required for large files.")
    pause()


def main() -> None:
    while True:
        clear_screen()
        print("=" * 58)
        print("       GitHub Easy File Uploader")
        print("                  by saadhinath")
        print("=" * 58)
        print("\n                    MENU\n")
        print("01  Update / Install Package")
        print("02  Start Uploading Process")
        print("03  Delete GitHub File")
        print("04  Information")
        print("05  Exit")
        print("\n--------------------------------------------------")

        try:
            choice = input("\nSelect an option: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\nThank you for using GitHub Easy File Uploader!")
            return

        if choice in ("1", "01"):
            install_update_package()
        elif choice in ("2", "02"):
            upload_process()
        elif choice in ("3", "03"):
            delete_github_file()
        elif choice in ("4", "04"):
            information()
        elif choice in ("5", "05", "q", "quit", "exit"):
            clear_screen()
            print("\nThank you for using GitHub Easy File Uploader!")
            print("=" * 58)
            return
        else:
            print("\n❌ Invalid option.")
            time.sleep(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
GitHub Easy File Uploader
Cross-platform: Windows + Linux
Standard library only (no pip packages required).

Features:
- Windows / Linux menu
- Git and Git LFS check/setup
- Animated programmer-style UI
- File picker with Tkinter, with terminal fallback
- Upload files to a GitHub repository
- Delete files from a GitHub repository
- Repository/file scanning animations
- Colored success/error messages
- Temporary clone is always cleaned up
"""

import os
import sys
import time
import shutil
import subprocess
import tempfile
import platform
from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# Colors / terminal helpers
# ============================================================

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"


def enable_windows_ansi():
    """Enable ANSI escape sequences on modern Windows consoles."""
    if os.name == "nt":
        try:
            os.system("")
        except Exception:
            pass


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="\nPress Enter to continue..."):
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        pass


def safe_input(prompt=""):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def title(text):
    print(f"{C.CYAN}{C.BOLD}{'=' * 58}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}{text.center(58)}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}{'=' * 58}{C.RESET}")


def section(text):
    print(f"\n{C.BLUE}{C.BOLD}┌─ {text}{C.RESET}")
    print(f"{C.BLUE}└{'─' * 56}{C.RESET}")


def error(message):
    print(f"{C.RED}{C.BOLD}❌ {message}{C.RESET}")


def success(message):
    print(f"{C.GREEN}{C.BOLD}✅ {message}{C.RESET}")


def info(message):
    print(f"{C.CYAN}ℹ {message}{C.RESET}")


def warning(message):
    print(f"{C.YELLOW}⚠ {message}{C.RESET}")


def command_preview(command):
    if isinstance(command, (list, tuple)):
        return " ".join(str(x) for x in command)
    return str(command)


# ============================================================
# Animations
# ============================================================

def type_text(text, delay=0.012):
    """Small typewriter effect."""
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def spinner(message, seconds=1.2):
    """Programmer-style spinner."""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end = time.time() + seconds
    i = 0
    while time.time() < end:
        print(
            f"\r{C.CYAN}{frames[i % len(frames)]}{C.RESET} {message}",
            end="",
            flush=True,
        )
        time.sleep(0.08)
        i += 1
    print("\r" + " " * (len(message) + 5) + "\r", end="")


def progress(message, seconds=1.0, width=28):
    """Animated progress bar."""
    steps = width
    delay = seconds / max(steps, 1)
    for i in range(steps + 1):
        filled = "█" * i
        empty = "░" * (steps - i)
        percent = int(i * 100 / steps)
        print(
            f"\r{C.CYAN}{message:<25}{C.RESET} "
            f"[{C.GREEN}{filled}{C.RESET}{C.GRAY}{empty}{C.RESET}] "
            f"{percent:3d}%",
            end="",
            flush=True,
        )
        time.sleep(delay)
    print()


def startup_animation():
    clear()
    print()
    print(f"{C.CYAN}{C.BOLD}")
    type_text(">>> INITIALIZING GITHUB EASY FILE UPLOADER", 0.018)
    print(f"{C.RESET}")
    progress("Loading modules", 0.55, 22)
    progress("Checking terminal", 0.45, 22)
    progress("Preparing interface", 0.45, 22)
    print(f"{C.GREEN}{C.BOLD}SYSTEM READY{C.RESET}\n")
    time.sleep(0.25)


# ============================================================
# Git helpers
# ============================================================

def run_command(args, cwd=None, capture=False, check=False):
    """
    Run a command while keeping stdin attached to the user's terminal.
    This is important because Git may ask for a username or Personal
    Access Token interactively.
    """
    try:
        if capture:
            result = subprocess.run(
                args,
                cwd=cwd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        else:
            result = subprocess.run(
                args,
                cwd=cwd,
                text=True,
                check=False,
            )

        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, args,
                getattr(result, "stdout", ""),
                getattr(result, "stderr", "")
            )
        return result

    except FileNotFoundError:
        error(f"Command not found: {args[0]}")
        return None
    except KeyboardInterrupt:
        print()
        warning("Operation cancelled.")
        return None
    except Exception as exc:
        error(str(exc))
        return None


def command_exists(name):
    return shutil.which(name) is not None


def git_version():
    if not command_exists("git"):
        return None
    result = run_command(["git", "--version"], capture=True)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def git_lfs_version():
    if not command_exists("git"):
        return None
    result = run_command(["git", "lfs", "version"], capture=True)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def validate_github_url(url):
    try:
        parsed = urlparse(url.strip())
        return (
            parsed.scheme in ("http", "https")
            and parsed.netloc.lower() in ("github.com", "www.github.com")
            and parsed.path.strip("/") != ""
        )
    except Exception:
        return False


def repo_name_from_url(url):
    path = urlparse(url).path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return Path(path).name or "repository"


def current_branch(repo):
    result = run_command(
        ["git", "branch", "--show-current"],
        cwd=repo,
        capture=True,
    )
    if result and result.returncode == 0:
        branch = result.stdout.strip()
        return branch or "main"
    return "main"


def clone_repository(url, destination):
    print(f"{C.CYAN}📥 Cloning repository...{C.RESET}")
    result = run_command(["git", "clone", url, str(destination)])
    if result is None or result.returncode != 0:
        error("Repository clone failed.")
        return False
    progress("Clone complete", 0.45, 24)
    return True


def git_lfs_setup():
    """Run git lfs install if Git LFS is available."""
    if not git_lfs_version():
        return False
    result = run_command(["git", "lfs", "install"], capture=True)
    return bool(result and result.returncode == 0)


# ============================================================
# Package / dependency menu
# ============================================================

def update_install_windows():
    clear()
    title("GITHUB EASY FILE UPLOADER - WINDOWS")
    section("UPDATE / INSTALL PACKAGE")

    print(f"{C.CYAN}Checking Git...{C.RESET}")
    gv = git_version()

    if gv:
        success(gv)
    else:
        error("Git is not installed.")
        print()
        print("Install Git for Windows from:")
        print("https://git-scm.com/download/win")
        pause()
        return

    print(f"\n{C.CYAN}Checking Git LFS...{C.RESET}")
    lv = git_lfs_version()

    if lv:
        success(lv)
        if git_lfs_setup():
            success("Git LFS is ready!")
        else:
            warning("Git LFS was detected, but initialization returned an error.")
    else:
        warning("Git LFS is not installed.")
        print()
        print("Install Git LFS from:")
        print("https://git-lfs.com/")
        print()
        print("After installation, run this menu again.")
    pause()


def update_install_linux():
    clear()
    title("GITHUB EASY FILE UPLOADER - LINUX")
    section("UPDATE / INSTALL PACKAGE")

    if not command_exists("git"):
        warning("Git is not installed.")
        print("The Linux setup will try to install Git LFS using apt.")
    else:
        success(git_version() or "Git detected.")

    if command_exists("git") and git_lfs_version():
        success(git_lfs_version())
        if git_lfs_setup():
            success("Git LFS setup completed successfully!")
        pause()
        return

    print()
    print(f"{C.YELLOW}The following commands may ask for your sudo password:{C.RESET}")
    print("  sudo apt update")
    print("  sudo apt install git git-lfs -y")
    print("  git lfs install")
    print()

    if not command_exists("sudo"):
        error("sudo was not found. Install Git/Git LFS manually.")
        pause()
        return

    answer = safe_input("Run the Linux package setup now? [Y/n]: ").strip().lower()
    if answer not in ("", "y", "yes"):
        pause()
        return

    print()
    type_text("$ sudo apt update", 0.015)
    r1 = run_command(["sudo", "apt", "update"])
    if r1 is None or r1.returncode != 0:
        error("apt update failed.")
        pause()
        return

    print()
    type_text("$ sudo apt install git git-lfs -y", 0.015)
    r2 = run_command(["sudo", "apt", "install", "git", "git-lfs", "-y"])
    if r2 is None or r2.returncode != 0:
        error("Git/Git LFS installation failed.")
        pause()
        return

    print()
    type_text("$ git lfs install", 0.015)
    r3 = run_command(["git", "lfs", "install"])
    if r3 and r3.returncode == 0:
        success("Git LFS setup completed successfully!")
    else:
        error("Git LFS initialization failed.")

    pause()


# ============================================================
# File picker
# ============================================================

def choose_file():
    """
    Try a native Tkinter file picker first.
    If Tkinter is unavailable, use a terminal path.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(title="Select file to upload")
        root.destroy()

        if selected:
            return Path(selected).expanduser().resolve()
    except Exception:
        pass

    print()
    warning("Native file picker is unavailable.")
    raw = safe_input("Enter the full path of the file: ").strip().strip('"')
    if raw:
        return Path(raw).expanduser().resolve()
    return None


# ============================================================
# Repository scanning
# ============================================================

def list_repo_files(repo):
    """
    List files excluding the .git directory.
    Git's tracked/untracked working tree is intentionally shown.
    """
    files = []
    repo = Path(repo)

    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        try:
            path.relative_to(repo / ".git")
            continue
        except ValueError:
            pass
        files.append(path)

    files.sort(key=lambda p: str(p).lower())
    return files


def display_files(files, heading="FILES IN REPOSITORY"):
    print()
    print(f"{C.CYAN}{C.BOLD}┌{'─' * 56}┐{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}│ {heading:<54} │{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}└{'─' * 56}┘{C.RESET}")

    if not files:
        print(f"{C.YELLOW}  (no files found){C.RESET}")
        return

    for i, path in enumerate(files, 1):
        print(f"  {C.BLUE}{i:>3}{C.RESET}  {path.name}")
    print()


def choose_repo_file(files, prompt):
    if not files:
        error("No files are available.")
        return None

    while True:
        raw = safe_input(prompt).strip()
        try:
            number = int(raw)
            if 1 <= number <= len(files):
                return files[number - 1]
        except ValueError:
            pass
        error(f"Enter a number from 1 to {len(files)}.")


def scan_animation():
    spinner("Scanning repository...", 1.0)
    progress("Repository scan", 0.75, 28)


# ============================================================
# Upload
# ============================================================

def upload_process():
    clear()
    title("GITHUB EASY FILE UPLOADER")
    print(f"{C.CYAN}{C.BOLD}UPLOAD MODE{C.RESET}\n")

    if not git_version():
        error("Git is not installed or is not available in PATH.")
        pause()
        return

    repo_url = safe_input(
        "Give your repository HTTPS URL:\n> "
    ).strip()

    if not validate_github_url(repo_url):
        error("That does not look like a valid GitHub HTTPS repository URL.")
        print("Example: https://github.com/username/repository.git")
        pause()
        return

    source = choose_file()
    if source is None:
        warning("No file selected.")
        pause()
        return

    if not source.is_file():
        error("Selected path is not a file.")
        pause()
        return

    repo_name = repo_name_from_url(repo_url)

    print(f"\n{C.CYAN}Selected file:{C.RESET} {source.name}")
    print(f"{C.CYAN}Repository:{C.RESET} {repo_name}")
    print()

    temp_root = Path(tempfile.mkdtemp(prefix="github_easy_uploader_"))
    repo_dir = temp_root / repo_name

    try:
        if not clone_repository(repo_url, repo_dir):
            return

        destination = repo_dir / source.name

        if destination.exists():
            warning(f"{source.name} already exists in the repository.")
            choice = safe_input("Replace it? [y/N]: ").strip().lower()
            if choice not in ("y", "yes"):
                warning("Upload cancelled.")
                return

        print(f"{C.CYAN}📁 Copying file...{C.RESET}")
        shutil.copy2(source, destination)
        progress("Copy complete", 0.55, 24)

        scan_animation()
        files = list_repo_files(repo_dir)
        display_files(files)

        # Prefer the copied file by default, but still allow selection.
        copied_index = None
        for i, path in enumerate(files, 1):
            if path.resolve() == destination.resolve():
                copied_index = i
                break

        if copied_index is not None:
            print(
                f"{C.GREEN}Suggested file: {copied_index} → "
                f"{destination.name}{C.RESET}"
            )

        selected = choose_repo_file(
            files,
            "Select the file you want to upload "
            f"[Enter = {copied_index or 1}]: "
        )

        # Enter selects the suggested/copy file.
        if selected is None:
            return

        print(f"{C.GREEN}✓ Selected: {selected.name}{C.RESET}")

        relative = selected.relative_to(repo_dir)
        commit_message = f"Add {relative.as_posix()}"

        print()
        print(f"{C.CYAN}$ git add {relative.as_posix()}{C.RESET}")
        add = run_command(["git", "add", "--", str(relative)], cwd=repo_dir)
        if add is None or add.returncode != 0:
            error("git add failed.")
            pause()
            return

        print(f"{C.CYAN}$ git commit -m \"{commit_message}\"{C.RESET}")
        commit = run_command(
            ["git", "commit", "-m", commit_message],
            cwd=repo_dir,
        )

        if commit is None:
            return

        if commit.returncode != 0:
            # A common safe case: nothing changed.
            error("git commit failed.")
            pause()
            return

        branch = current_branch(repo_dir)
        print()
        print(f"{C.CYAN}$ git push origin {branch}{C.RESET}")
        print(
            f"{C.YELLOW}GitHub may ask for your username and "
            f"Personal Access Token. The token is not displayed by this program.{C.RESET}\n"
        )

        push = run_command(
            ["git", "push", "origin", branch],
            cwd=repo_dir,
        )

        if push is None or push.returncode != 0:
            error("Upload failed!")
            print("Git returned an error. Check the message above.")
            pause()
            return

        progress("Uploading to GitHub", 0.9, 28)

        print()
        print(f"{C.GREEN}{C.BOLD}{'=' * 58}{C.RESET}")
        success("File uploaded successfully!")
        print(f"{C.WHITE}📄 File: {relative}{C.RESET}")
        print(f"{C.WHITE}📦 Repository: {repo_name}{C.RESET}")
        print(f"{C.WHITE}🌿 Branch: {branch}{C.RESET}")
        print(f"{C.YELLOW}Temporary cloned repository will now be deleted.{C.RESET}")
        print(f"{C.GREEN}{C.BOLD}{'=' * 58}{C.RESET}")

    except PermissionError as exc:
        error(f"Permission error: {exc}")
    except OSError as exc:
        error(f"File operation failed: {exc}")
    except Exception as exc:
        error(f"Unexpected error: {exc}")
    finally:
        try:
            shutil.rmtree(temp_root, ignore_errors=True)
        except Exception:
            pass

    pause()


# ============================================================
# Delete
# ============================================================

def delete_process():
    clear()
    title("GITHUB EASY FILE UPLOADER")
    print(f"{C.RED}{C.BOLD}DELETE GITHUB FILE MODE{C.RESET}\n")

    if not git_version():
        error("Git is not installed or is not available in PATH.")
        pause()
        return

    repo_url = safe_input(
        "Give your repository HTTPS URL:\n> "
    ).strip()

    if not validate_github_url(repo_url):
        error("That does not look like a valid GitHub HTTPS repository URL.")
        pause()
        return

    repo_name = repo_name_from_url(repo_url)
    temp_root = Path(tempfile.mkdtemp(prefix="github_easy_delete_"))
    repo_dir = temp_root / repo_name

    try:
        print(f"{C.CYAN}Searching URL...{C.RESET}")
        progress("Repository lookup", 0.75, 28)

        if not clone_repository(repo_url, repo_dir):
            return

        scan_animation()
        files = list_repo_files(repo_dir)
        display_files(files)

        selected = choose_repo_file(
            files,
            "Select the file you want to delete: "
        )
        if selected is None:
            return

        relative = selected.relative_to(repo_dir)

        print()
        print(
            f'{C.YELLOW}Are you sure you want to delete '
            f'"{relative}"?{C.RESET}'
        )
        print(f"{C.RED}1  Yes{C.RESET}")
        print(f"{C.GREEN}2  No{C.RESET}")

        confirm = safe_input("> ").strip()
        if confirm != "1":
            warning("Delete cancelled.")
            pause()
            return

        print(f"\n{C.RED}SELECTED → {relative}{C.RESET}")
        progress("Selection verified", 0.5, 24)

        print(f"{C.CYAN}$ git rm {relative.as_posix()}{C.RESET}")
        rm = run_command(
            ["git", "rm", "--", str(relative)],
            cwd=repo_dir,
        )
        if rm is None or rm.returncode != 0:
            error("git rm failed.")
            pause()
            return

        commit_message = f"Delete {relative.as_posix()}"
        print(f"{C.CYAN}$ git commit -m \"{commit_message}\"{C.RESET}")
        commit = run_command(
            ["git", "commit", "-m", commit_message],
            cwd=repo_dir,
        )

        if commit is None or commit.returncode != 0:
            error("Deletion commit failed.")
            pause()
            return

        branch = current_branch(repo_dir)

        print(f"{C.CYAN}$ git push origin {branch}{C.RESET}")
        print(
            f"{C.YELLOW}GitHub may ask for your username and "
            f"Personal Access Token. The token is not displayed by this program.{C.RESET}\n"
        )

        push = run_command(
            ["git", "push", "origin", branch],
            cwd=repo_dir,
        )

        if push is None or push.returncode != 0:
            error("Delete push failed!")
            pause()
            return

        progress("Deleting from GitHub", 0.9, 28)

        print()
        print(f"{C.GREEN}{C.BOLD}{'=' * 58}{C.RESET}")
        success("File deleted successfully!")
        print(f"{C.WHITE}🗑️  File: {relative}{C.RESET}")
        print(f"{C.WHITE}📦 Repository: {repo_name}{C.RESET}")
        print(f"{C.WHITE}🌿 Branch: {branch}{C.RESET}")
        print(f"{C.YELLOW}Temporary cloned repository will now be deleted.{C.RESET}")
        print(f"{C.GREEN}{C.BOLD}{'=' * 58}{C.RESET}")

    except Exception as exc:
        error(f"Unexpected error: {exc}")
    finally:
        try:
            shutil.rmtree(temp_root, ignore_errors=True)
        except Exception:
            pass

    pause()


# ============================================================
# Information
# ============================================================

SUPPORTED_FORMATS = [
    ("🐍 Python", ".py, .pyw, .pyi"),
    ("☕ Java", ".java, .jar, .class"),
    ("🟦 C/C++", ".c, .h, .cpp, .hpp, .cc"),
    ("🟨 JavaScript", ".js, .mjs, .cjs"),
    ("🌐 Web", ".html, .css, .scss, .xml"),
    ("📱 Android", ".kt, .java, .gradle, .aab, .apk"),
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


def information():
    clear()
    title("SUPPORTED FORMATS")

    print(
        f"{C.CYAN}{'Category':<20} {'Extensions'}{C.RESET}"
    )
    print(f"{C.BLUE}{'-' * 58}{C.RESET}")

    for category, extensions in SUPPORTED_FORMATS:
        print(f"{category:<20} {extensions}")

    print(f"\n{C.GREEN}No extension whitelist is enforced by the uploader.{C.RESET}")
    print(
        f"{C.DIM}The table is an information guide; Git can store many other "
        f"file types as well.{C.RESET}"
    )

    print()
    print(f"{C.YELLOW}GitHub note:{C.RESET}")
    print("Large files may require Git LFS depending on GitHub's file-size limits.")
    print("For HTTPS authentication, use a GitHub Personal Access Token as the password.")
    print("Never paste your token into this program or share it with anyone.")

    pause()


# ============================================================
# Menus
# ============================================================

def windows_menu():
    while True:
        clear()
        title("GITHUB EASY FILE UPLOADER")
        print(f"{C.WHITE}{C.BOLD}WINDOWS{C.RESET}".center(66))
        print(f"{C.DIM}coding by saadhinath{C.RESET}".center(66))
        print()
        print(f"{C.CYAN}01{C.RESET}  Update / Install Package")
        print(f"{C.CYAN}02{C.RESET}  Start Uploading Process")
        print(f"{C.CYAN}03{C.RESET}  Delete GitHub File")
        print(f"{C.CYAN}04{C.RESET}  Information")
        print(f"{C.CYAN}05{C.RESET}  Exit")
        print(f"{C.BLUE}{'─' * 58}{C.RESET}")

        choice = safe_input("> ").strip()

        if choice == "1" or choice == "01":
            update_install_windows()
        elif choice == "2" or choice == "02":
            upload_process()
        elif choice == "3" or choice == "03":
            delete_process()
        elif choice == "4" or choice == "04":
            information()
        elif choice == "5" or choice == "05":
            return
        else:
            error("Invalid option.")
            time.sleep(0.8)


def linux_menu():
    while True:
        clear()
        title("GITHUB EASY FILE UPLOADER")
        print(f"{C.WHITE}{C.BOLD}LINUX{C.RESET}".center(66))
        print(f"{C.DIM}coding by saadhinath{C.RESET}".center(66))
        print()
        print(f"{C.CYAN}01{C.RESET}  Update / Install Package")
        print(f"{C.CYAN}02{C.RESET}  Start Uploading Process")
        print(f"{C.CYAN}03{C.RESET}  Delete GitHub File")
        print(f"{C.CYAN}04{C.RESET}  Information")
        print(f"{C.CYAN}05{C.RESET}  Exit")
        print(f"{C.BLUE}{'─' * 58}{C.RESET}")

        choice = safe_input("> ").strip()

        if choice == "1" or choice == "01":
            update_install_linux()
        elif choice == "2" or choice == "02":
            upload_process()
        elif choice == "3" or choice == "03":
            delete_process()
        elif choice == "4" or choice == "04":
            information()
        elif choice == "5" or choice == "05":
            return
        else:
            error("Invalid option.")
            time.sleep(0.8)


def os_menu():
    while True:
        clear()
        title("GITHUB EASY FILE UPLOADER")
        print(f"{C.DIM}coding by saadhinath{C.RESET}".center(66))
        print()
        print(f"{C.CYAN}01{C.RESET}  Windows")
        print(f"{C.CYAN}02{C.RESET}  Linux")
        print(f"{C.CYAN}03{C.RESET}  Exit")
        print(f"{C.BLUE}{'_' * 58}{C.RESET}")

        choice = safe_input("> ").strip()

        if choice == "1" or choice == "01":
            windows_menu()
        elif choice == "2" or choice == "02":
            linux_menu()
        elif choice == "3" or choice == "03":
            return
        else:
            error("Invalid option.")
            time.sleep(0.8)


def main():
    enable_windows_ansi()
    try:
        startup_animation()
        os_menu()
    except KeyboardInterrupt:
        print()
        warning("Program interrupted by user.")
    finally:
        clear()
        print(f"{C.CYAN}{C.BOLD}{'=' * 58}{C.RESET}")
        print(f"{C.GREEN}{C.BOLD}Thank you for using GitHub Easy File Uploader!{C.RESET}")
        print(f"{C.CYAN}{C.BOLD}{'=' * 58}{C.RESET}")


if __name__ == "__main__":
    main()

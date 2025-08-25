# smart, cross-platform flutter-keys daemon
# Tokens expected from MCU: CLEAN | PUBGET | UPGRADE
# Requirements: pip install -r requirements.txt

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from serial import Serial
from serial.tools import list_ports

# -------- user config (env overrides) --------
PROJECT_DIR = os.environ.get(
    "FLUTTER_KEYS_PROJECT", str(Path.home() / "dev/my_flutter_app")
)
PROJECT_DIR = str(Path(PROJECT_DIR).expanduser())
BAUD = int(os.environ.get("FLUTTER_KEYS_BAUD", "115200"))
PORT = os.environ.get("FLUTTER_KEYS_PORT", "")

TOKENS = {
    "CLEAN": "flutter clean",
    "PUBGET": "flutter pub get",
    "UPGRADE": "flutter upgrade",
}
# --------------------------------------------

IS_WINDOWS = platform.system().lower().startswith("win")


def pick_port(pref: str) -> str:
    """Choose the best serial port when none is specified."""
    if pref:
        return pref
    ports = list(list_ports.comports())
    if not ports:
        return ""
    scored = []
    for p in ports:
        score = 0
        name = (p.device or "").lower()
        desc = (p.description or "").lower()
        if "arduino" in desc:
            score += 5
        if "usbmodem" in name:
            score += 4
        if "usbserial" in name:
            score += 3
        if IS_WINDOWS and name.startswith("com"):
            score += 2
        scored.append((score, p.device))
    scored.sort(reverse=True)
    return scored[0][1]


def shell_run_posix(cmd: str, cwd: str) -> int:
    """
    Run inside an interactive-like shell so user PATH/managers (fvm/rbenv/etc.) are honored.
    Prefer zsh, then bash, then sh.
    """
    shells = ["/bin/zsh", "/usr/bin/zsh", "/bin/bash", "/usr/bin/bash", "/bin/sh"]
    full = f'cd "{cwd}" && {cmd}'
    for sh in shells:
        if Path(sh).exists():
            print(f"▶ {full}  [shell={sh}]")
            p = subprocess.run([sh, "-lc", full])
            print(f"✔ exit {p.returncode}")
            return p.returncode
    # fallback: direct exec (may miss PATH customizations)
    print(f"▶ {full}  [shell=direct]")
    p = subprocess.run(cmd.split(), cwd=cwd)
    print(f"✔ exit {p.returncode}")
    return p.returncode


def shell_run_windows(cmd: str, cwd: str) -> int:
    """Run with PowerShell so PATH/SDK shims are available."""
    ps = f'Set-Location -LiteralPath "{cwd}"; {cmd}'
    print(f"▶ (PS) {ps}")
    p = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps]
    )
    print(f"✔ exit {p.returncode}")
    return p.returncode


def run_cmd(cmd_str: str) -> int:
    """Dispatch command to the appropriate shell."""
    if not Path(PROJECT_DIR).exists():
        print(f"⚠ PROJECT_DIR not found: {PROJECT_DIR}")
        return 1
    return (
        shell_run_windows(cmd_str, PROJECT_DIR)
        if IS_WINDOWS
        else shell_run_posix(cmd_str, PROJECT_DIR)
    )


def check_ready() -> None:
    """Fail fast if project folder or flutter are not available in the target shell."""
    if not Path(PROJECT_DIR).exists():
        print(f"⚠ PROJECT_DIR not found: {PROJECT_DIR}")
        sys.exit(1)
    if IS_WINDOWS:
        test = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "$ErrorActionPreference='SilentlyContinue'; if (Get-Command flutter) { exit 0 } else { exit 1 }",
            ]
        )
    else:
        # use same shell stack as shell_run_posix (prefer zsh)
        test = (
            subprocess.run(["/bin/zsh", "-lc", "command -v flutter >/dev/null"])
            if Path("/bin/zsh").exists()
            else subprocess.run(["/bin/sh", "-lc", "command -v flutter >/dev/null"])
        )
    if test.returncode != 0:
        print(
            "⚠ 'flutter' not found in your shell PATH. Open a terminal and verify 'flutter --version'."
        )
        sys.exit(127)


def main():
    check_ready()
    port = pick_port(PORT)
    if not port:
        print("❌ No serial ports found.")
        sys.exit(2)
    print(f"🔌 {port} @ {BAUD} | project: {PROJECT_DIR}")

    try:
        with Serial(port, BAUD, timeout=1) as ser:
            ser.reset_input_buffer()
            while True:
                line = ser.readline().decode(errors="ignore").strip().upper()
                if not line:
                    time.sleep(0.02)
                    continue
                if line in TOKENS:
                    print(f"📥 {line}")
                    run_cmd(TOKENS[line])
                else:
                    print(f"⚠ ignored: {line}")
    except KeyboardInterrupt:
        print("\n👋 terminated by user")
    except Exception as e:
        print(f"Serial error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()

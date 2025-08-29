from __future__ import annotations
import shutil
import subprocess

def _escape(s: str) -> str:
    return s.replace('"', '\\"')

def notify(title: str, subtitle: str = "", message: str = "", url: str | None = None) -> None:
    """
    macOS notifications. Prefer terminal-notifier if available (best reliability),
    else fall back to AppleScript. No-ops on failure.
    """
    try:
        if shutil.which("terminal-notifier"):
            cmd = ["terminal-notifier", "-title", title[:80]]
            if subtitle:
                cmd += ["-subtitle", subtitle[:120]]
            if message:
                cmd += ["-message", message[:200]]
            if url:
                cmd += ["-open", url]
            # Choose a default sound to make it noticeable
            cmd += ["-sound", "default"]
            subprocess.run(cmd, check=False, capture_output=True, text=True)
            return
    except Exception:
        pass

    # Fallback: AppleScript (works on many systems but can be blocked by OS settings)
    try:
        title_s = _escape(title[:80])
        subtitle_s = _escape(subtitle[:120])
        message_s = _escape(message[:200])
        script = f'display notification "{message_s}" with title "{title_s}"'
        if subtitle_s:
            script += f' subtitle "{subtitle_s}"'
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True, text=True)
    except Exception:
        # Give up silently
        pass

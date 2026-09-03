"""Run the daily update and show a concise Ubuntu desktop notification."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def notify(title: str, body: str, urgency: str = "normal") -> None:
    """Best effort only: a missing GUI session must not fail the update."""
    try:
        subprocess.run(
            ["notify-send", "--app-name=Campus Agent", f"--urgency={urgency}", "--expire-time=20000", title, body[:900]],
            check=False,
        )
    except OSError:
        pass


def main() -> None:
    try:
        sync = subprocess.run([sys.executable, "-m", "campus_agent", "sync", "--all-courses"], text=True, capture_output=True, check=True)
        digest = subprocess.run([sys.executable, "-m", "campus_agent", "digest"], text=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "Unknown error").strip()
        print(details, file=sys.stderr)
        notify("校园信息更新失败", details, "critical")
        raise SystemExit(1) from exc

    print(sync.stdout, end="")
    print(digest.stdout, end="")
    now = datetime.now().astimezone()
    archive = Path("/home/daniel/Desktop/Campus Digests")
    archive.mkdir(parents=True, exist_ok=True)
    digest_file = archive / f"{now.date().isoformat()}.txt"
    digest_file.write_text(
        f"校园信息每日摘要\n日期：{now.date().isoformat()}\n更新时间：{now:%Y-%m-%d %H:%M %Z}\n\n{digest.stdout.strip()}\n",
        encoding="utf-8",
    )
    bullets = [line[2:].strip() for line in digest.stdout.splitlines() if line.startswith("- ")]
    body = "\n".join(bullets[:4]) or "摘要已更新。"
    body += f"\n已保存：{digest_file.name}"
    notify("校园摘要已更新", body)


if __name__ == "__main__":
    main()

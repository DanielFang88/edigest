import re
from typing import Any

KEYWORDS = ("deadline", "due", "exam", "midterm", "final", "schedule", "cancel", "required action", "mandatory", "attendance", "extension", "截止", "考试", "改期", "必需")
STAFF_ROLES = {"admin", "ta", "tutor", "instructor", "staff"}


def candidate_reason(thread: dict[str, Any]) -> str | None:
    if thread.get("type") == "announcement":
        return "announcement"
    users = {u.get("id"): u for u in thread.get("_users", [])}
    author = users.get(thread.get("user_id"), {})
    if str(author.get("course_role", "")).lower() in STAFF_ROLES:
        return "staff author"
    text = " ".join(str(thread.get(x, "")) for x in ("title", "content", "document")).lower()
    matches = [word for word in KEYWORDS if re.search(r"\b" + re.escape(word) + r"\b", text)]
    return "keywords: " + ", ".join(matches) if matches else None


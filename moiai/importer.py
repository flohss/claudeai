"""
File importer — parse WhatsApp, Instagram, Telegram exports and plain text files,
then feed the content to the fact extraction pipeline.
"""

import json
import re
import zipfile
from pathlib import Path

# ── Format detection ───────────────────────────────────────────────────────────

def detect_format(path: Path) -> str:
    """Return one of: 'whatsapp', 'instagram', 'telegram', 'pdf', 'markdown', 'text'."""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return "pdf"

    if suffix in (".md", ".markdown"):
        return "markdown"

    if suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
        if any("messages/inbox" in n for n in names):
            return "instagram_zip"
        if any("result.json" in n for n in names):
            return "telegram_zip"
        return "zip_unknown"

    if suffix == ".json":
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if "messages" in data and "participants" in data:
                    return "instagram"
                if "messages" in data and "type" in data:
                    return "telegram"
            if isinstance(data, list) and data and "messages" in data[0]:
                return "instagram_multi"
        except (json.JSONDecodeError, KeyError):
            pass
        return "json_unknown"

    if suffix == ".txt":
        with open(path, encoding="utf-8", errors="replace") as f:
            sample = f.read(2000)
        # WhatsApp patterns: [DD/MM/YYYY, HH:MM:SS] or DD/MM/YYYY HH:MM -
        if re.search(r"\[\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}", sample):
            return "whatsapp"
        if re.search(r"\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*-\s*\S", sample):
            return "whatsapp"
        return "text"

    return "text"


# ── WhatsApp parser ────────────────────────────────────────────────────────────

_WA_BRACKET = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\]\s*([^:]+):\s*(.+)$"
)
_WA_DASH = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*\d{1,2}:\d{2}\s*(?:AM|PM)?\s*-\s*([^:]+):\s*(.+)$"
)
_SYSTEM_MSGS = re.compile(
    r"(Messages and calls are end-to-end encrypted|"
    r"created group|added|left|changed|deleted this message|"
    r"image omitted|video omitted|audio omitted|sticker omitted|"
    r"document omitted|GIF omitted|<Media omitted>)",
    re.IGNORECASE,
)


def parse_whatsapp(path: Path, user_name: str | None = None) -> tuple[list[str], list[str]]:
    """
    Returns (user_messages, all_senders).
    If user_name is None, returns messages from ALL senders (with attribution).
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    senders: set[str] = set()
    messages_by_sender: dict[str, list[str]] = {}
    current_sender = None
    current_msg: list[str] = []

    def flush():
        if current_sender and current_msg:
            text = " ".join(current_msg).strip()
            if not _SYSTEM_MSGS.search(text) and len(text) > 1:
                messages_by_sender.setdefault(current_sender, []).append(text)

    for line in lines:
        line = line.rstrip("\n")
        m = _WA_BRACKET.match(line) or _WA_DASH.match(line)
        if m:
            flush()
            current_msg = []
            current_sender = m.group(2).strip()
            senders.add(current_sender)
            current_msg.append(m.group(3).strip())
        elif current_sender and line.strip():
            current_msg.append(line.strip())
    flush()

    all_senders = sorted(senders)

    if user_name and user_name in messages_by_sender:
        return messages_by_sender[user_name], all_senders

    if user_name is None and messages_by_sender:
        # Return all messages attributed
        all_msgs = []
        for sender, msgs in messages_by_sender.items():
            for msg in msgs:
                all_msgs.append(f"{sender}: {msg}")
        return all_msgs, all_senders

    # Fallback: return all
    all_msgs = []
    for sender, msgs in messages_by_sender.items():
        for msg in msgs:
            all_msgs.append(f"{sender}: {msg}")
    return all_msgs, all_senders


# ── Instagram parser ───────────────────────────────────────────────────────────

def _load_instagram_json(data: dict, user_name: str | None) -> tuple[list[str], list[str]]:
    participants = [p["name"] for p in data.get("participants", [])]
    messages = data.get("messages", [])
    user_msgs = []
    for msg in messages:
        sender = msg.get("sender_name", "")
        content = msg.get("content", "")
        if not content:
            continue
        if user_name:
            if sender == user_name:
                user_msgs.append(content)
        else:
            user_msgs.append(f"{sender}: {content}")
    return user_msgs, participants


def parse_instagram(path: Path, user_name: str | None = None) -> tuple[list[str], list[str]]:
    with open(path, encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    return _load_instagram_json(data, user_name)


def parse_instagram_zip(path: Path, user_name: str | None = None) -> tuple[list[str], list[str]]:
    all_msgs: list[str] = []
    all_participants: set[str] = set()
    with zipfile.ZipFile(path) as z:
        json_files = [n for n in z.namelist() if n.endswith(".json") and "messages/inbox" in n]
        for name in json_files:
            with z.open(name) as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue
            msgs, parts = _load_instagram_json(data, user_name)
            all_msgs.extend(msgs)
            all_participants.update(parts)
    return all_msgs, sorted(all_participants)


# ── Telegram parser ────────────────────────────────────────────────────────────

def parse_telegram(path: Path, user_name: str | None = None) -> tuple[list[str], list[str]]:
    with open(path, encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    senders: set[str] = set()
    user_msgs: list[str] = []

    for msg in messages:
        if msg.get("type") != "message":
            continue
        sender = msg.get("from", "") or msg.get("actor", "")
        senders.add(sender)
        # Text can be a string or a list of text entities
        raw = msg.get("text", "")
        if isinstance(raw, list):
            text = "".join(
                part if isinstance(part, str) else part.get("text", "")
                for part in raw
            )
        else:
            text = str(raw)
        text = text.strip()
        if not text:
            continue
        if user_name:
            if sender == user_name:
                user_msgs.append(text)
        else:
            user_msgs.append(f"{sender}: {text}")

    return user_msgs, sorted(senders)


def parse_telegram_zip(path: Path, user_name: str | None = None) -> tuple[list[str], list[str]]:
    with zipfile.ZipFile(path) as z:
        json_files = [n for n in z.namelist() if n.endswith("result.json")]
        if not json_files:
            return [], []
        with z.open(json_files[0]) as f:
            data = json.load(f)
    # Write to temp and reuse parser logic inline
    messages = data.get("messages", [])
    senders: set[str] = set()
    user_msgs: list[str] = []
    for msg in messages:
        if msg.get("type") != "message":
            continue
        sender = msg.get("from", "") or msg.get("actor", "")
        senders.add(sender)
        raw = msg.get("text", "")
        if isinstance(raw, list):
            text = "".join(p if isinstance(p, str) else p.get("text", "") for p in raw)
        else:
            text = str(raw)
        text = text.strip()
        if not text:
            continue
        if user_name:
            if sender == user_name:
                user_msgs.append(text)
        else:
            user_msgs.append(f"{sender}: {text}")
    return user_msgs, sorted(senders)


# ── Plain text parser ──────────────────────────────────────────────────────────

def parse_plain_text(path: Path) -> tuple[list[str], list[str]]:
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", content) if p.strip()]
    return paragraphs, []


def parse_markdown(path: Path) -> tuple[list[str], list[str]]:
    """Parse a Markdown file (journal, Obsidian note, etc.) into paragraphs."""
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    # Strip code blocks (not personal info)
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"`[^`]+`", "", content)
    # Split by heading or double newline
    paragraphs = [p.strip() for p in re.split(r"\n{2,}|(?=\n#{1,3} )", content) if p.strip()]
    return paragraphs, []


def parse_pdf(path: Path) -> tuple[list[str], list[str]]:
    """Extract text from a PDF using pypdf (pure Python, no system deps)."""
    try:
        import pypdf
    except ImportError:
        raise ImportError(
            "pypdf n'est pas installé. Lance : pip install pypdf"
        )

    reader = pypdf.PdfReader(str(path))
    paragraphs: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for para in re.split(r"\n{2,}", text):
            para = para.strip()
            if para and len(para) > 20:
                paragraphs.append(para)
    return paragraphs, []


# ── Main entry point ───────────────────────────────────────────────────────────

def load_file(path: Path, user_name: str | None = None) -> tuple[list[str], list[str], str]:
    """
    Parse any supported file.
    Returns (messages, senders_found, format_name).
    """
    fmt = detect_format(path)

    if fmt == "whatsapp":
        msgs, senders = parse_whatsapp(path, user_name)
    elif fmt == "instagram":
        msgs, senders = parse_instagram(path, user_name)
    elif fmt == "instagram_zip":
        msgs, senders = parse_instagram_zip(path, user_name)
    elif fmt == "instagram_multi":
        with open(path, encoding="utf-8", errors="replace") as f:
            items = json.load(f)
        msgs, senders = [], []
        for item in items:
            m, s = _load_instagram_json(item, user_name)
            msgs.extend(m)
            senders.extend(s)
    elif fmt == "telegram":
        msgs, senders = parse_telegram(path, user_name)
    elif fmt == "telegram_zip":
        msgs, senders = parse_telegram_zip(path, user_name)
    elif fmt == "pdf":
        msgs, senders = parse_pdf(path)
    elif fmt == "markdown":
        msgs, senders = parse_markdown(path)
    else:
        msgs, senders = parse_plain_text(path)
        fmt = "text"

    return msgs, senders, fmt

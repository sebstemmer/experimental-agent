import email
import email.policy
import re
import sqlite3
from html.parser import HTMLParser
from pathlib import Path

EMAIL_DIR = Path("data/emails")
DB_PATH = Path("data/emails.db")


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    text = "".join(s.parts)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def extract_body(msg: email.message.EmailMessage) -> str:
    plain = msg.get_body(preferencelist=("plain",))
    if plain is not None:
        return plain.get_content().strip()
    html = msg.get_body(preferencelist=("html",))
    if html is not None:
        return html_to_text(html.get_content())
    return ""


def parse_eml(path: Path) -> dict:
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)
    return {
        "message_id": (msg["Message-ID"] or path.name).strip(),
        "from_addr": str(msg["From"] or ""),
        "to_addr": str(msg["To"] or ""),
        "subject": str(msg["Subject"] or ""),
        "date": str(msg["Date"] or ""),
        "body": extract_body(msg),
        "path": str(path),
    }


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            message_id TEXT PRIMARY KEY,
            from_addr  TEXT,
            to_addr    TEXT,
            subject    TEXT,
            date       TEXT,
            body       TEXT,
            path       TEXT
        )
    """)
    conn.commit()


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    files = sorted(EMAIL_DIR.glob("*.eml"))
    inserted = skipped = failed = 0

    for path in files:
        try:
            rec = parse_eml(path)
        except Exception as e:
            print(f"FAIL {path.name}: {e}")
            failed += 1
            continue

        cur = conn.execute(
            "INSERT OR IGNORE INTO emails "
            "(message_id, from_addr, to_addr, subject, date, body, path) "
            "VALUES (:message_id, :from_addr, :to_addr, :subject, :date, :body, :path)",
            rec,
        )
        if cur.rowcount:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    conn.close()
    print(f"inserted={inserted} skipped={skipped} failed={failed} total={len(files)}")


if __name__ == "__main__":
    main()

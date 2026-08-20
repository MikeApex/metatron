"""
tests/test_attachment_endpoints.py — /upload, /attachments/{id}, and the exchange
record that carries them, against the real FastAPI app.

No model call: the WebSocket `send` path runs a full pipeline turn, so what is
exercised here is everything around it — the two HTTP endpoints, the auth gate, the
persona scoping, and the database round-trip that redraws an attachment chip after a
reload. The model-facing half is covered by tests/test_attachments.py.

Both the database and the persona data tree are redirected into a temp directory, so
this never reads or writes real conversation history.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_attachment_endpoints.py

Exits 0 if every check passes, 1 otherwise.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password")
os.environ.setdefault("METATRON_PERSONA", "danny_park")

from fastapi.testclient import TestClient              # noqa: E402

import core.attachments as att                         # noqa: E402
import core.server as server                           # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"\x00" * 64
EXE = b"MZ\x90\x00" + b"\x00" * 64

_tmpdir = tempfile.mkdtemp(prefix="metatron-attach-api-")
_root = Path(_tmpdir)

# Redirect storage before anything touches it.
server.DB_PATH = _root / "conversations" / "metatron.db"
att.persona_data_dir = lambda persona=None: _root / "personas" / (persona or "x")

_client = TestClient(server.app)
_token: str | None = None


def _auth() -> dict:
    global _token
    if _token is None:
        res = _client.post("/auth/login", json={"password": "test-password"})
        assert res.status_code == 200, res.text
        _token = res.json()["token"]
    return {"Authorization": f"Bearer {_token}"}


def _upload(data: bytes, name: str, content_type: str, persona: str = "danny_park"):
    return _client.post(
        f"/upload?persona={persona}",
        files={"file": (name, data, content_type)},
        headers=_auth(),
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def check_upload_requires_authentication():
    # Deliberately no header: /upload must not be reachable before login. The gate is
    # a middleware precisely so a newly added route cannot be forgotten.
    res = _client.post("/upload", files={"file": ("a.png", PNG, "image/png")})
    assert res.status_code == 401, res.status_code


def check_upload_accepts_an_image_and_returns_its_id():
    res = _upload(PNG, "dog.png", "image/png")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mime"] == "image/png"
    assert body["name"] == "dog.png"
    assert body["size"] == len(PNG)
    assert body["id"]
    # The path is server-side only — a client is never told where the file lives.
    assert "path" not in body, body


def check_upload_trusts_the_bytes_over_the_content_type():
    res = _upload(PDF, "not-really.png", "image/png")
    assert res.status_code == 200, res.text
    assert res.json()["mime"] == "application/pdf", res.json()


def check_upload_refuses_an_unsupported_type():
    res = _upload(EXE, "payload.png", "image/png")
    assert res.status_code == 415, res.status_code


def check_upload_refuses_an_empty_file():
    res = _upload(b"", "nothing.png", "image/png")
    assert res.status_code == 415, res.status_code


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def check_stored_file_comes_back_byte_for_byte():
    up = _upload(PNG, "dog.png", "image/png").json()
    res = _client.get(f"/attachments/{up['id']}?persona=danny_park", headers=_auth())
    assert res.status_code == 200, res.status_code
    assert res.content == PNG
    assert res.headers["content-type"].startswith("image/png")


def check_another_persona_cannot_read_the_file():
    # Personas are separate users' universes. An id from one is simply not found in
    # another, rather than being refused in a way that confirms it exists.
    up = _upload(PNG, "private.png", "image/png", persona="danny_park").json()
    res = _client.get(f"/attachments/{up['id']}?persona=maya_torres", headers=_auth())
    assert res.status_code == 404, res.status_code


def check_unknown_id_is_a_404_not_a_crash():
    res = _client.get("/attachments/deadbeef?persona=danny_park", headers=_auth())
    assert res.status_code == 404, res.status_code


def check_download_requires_authentication():
    up = _upload(PNG, "dog.png", "image/png").json()
    res = _client.get(f"/attachments/{up['id']}?persona=danny_park")
    assert res.status_code == 401, res.status_code


def check_a_deleted_file_reports_gone_rather_than_500():
    up = _upload(PNG, "vanishing.png", "image/png").json()
    record = asyncio.run(server._get_attachment(up["id"], "danny_park"))
    Path(record["path"]).unlink()
    res = _client.get(f"/attachments/{up['id']}?persona=danny_park", headers=_auth())
    assert res.status_code == 410, res.status_code


# ---------------------------------------------------------------------------
# The send frame and the stored exchange
# ---------------------------------------------------------------------------

def check_send_ids_resolve_and_unknown_ones_are_dropped():
    good = _upload(PNG, "real.png", "image/png").json()
    resolved = asyncio.run(
        server._resolve_attachments([good["id"], "not-an-id", 12345], "danny_park")
    )
    assert [r["id"] for r in resolved] == [good["id"]], resolved
    # The resolved record carries the on-disk path — that is what the model reads.
    assert Path(resolved[0]["path"]).exists()


def check_send_ids_are_capped_per_message():
    ids = [_upload(PNG, f"f{i}.png", "image/png").json()["id"] for i in range(6)]
    resolved = asyncio.run(server._resolve_attachments(ids, "danny_park"))
    assert len(resolved) == att.MAX_FILES_PER_MESSAGE, len(resolved)


def check_another_personas_id_cannot_be_attached_to_this_ones_message():
    stolen = _upload(PNG, "theirs.png", "image/png", persona="danny_park").json()
    resolved = asyncio.run(server._resolve_attachments([stolen["id"]], "maya_torres"))
    assert resolved == [], resolved


def check_history_carries_attachments_after_a_reload():
    """The chip has to redraw from the database, not from the live socket."""
    up = _upload(PNG, "receipt.png", "image/png").json()
    record = asyncio.run(server._get_attachment(up["id"], "danny_park"))

    asyncio.run(server._save_exchange(
        "danny_park", "exch-1", "what is this?", "A receipt.",
        attachments=[record],
    ))
    asyncio.run(server._bind_attachments([up["id"]], "exch-1"))

    rows = asyncio.run(server._get_recent_exchanges("danny_park"))
    row = [r for r in rows if r["exchange_id"] == "exch-1"][0]
    assert len(row["attachments"]) == 1, row
    assert row["attachments"][0]["id"] == up["id"]
    assert row["attachments"][0]["name"] == "receipt.png"
    # Still no path on the wire.
    assert "path" not in row["attachments"][0], row["attachments"][0]

    # And the file now knows which exchange it belonged to.
    bound = asyncio.run(server._get_attachment(up["id"], "danny_park"))
    assert bound["exchange_id"] == "exch-1", bound


def check_an_exchange_without_attachments_reports_an_empty_list():
    asyncio.run(server._save_exchange("danny_park", "exch-2", "hello", "hi"))
    rows = asyncio.run(server._get_recent_exchanges("danny_park"))
    row = [r for r in rows if r["exchange_id"] == "exch-2"][0]
    assert row["attachments"] == [], row


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS = [fn for name, fn in sorted(globals().items()) if name.startswith("check_")]


def main() -> int:
    asyncio.run(server._init_db())
    failed = 0
    for fn in CHECKS:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"  ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
    shutil.rmtree(_tmpdir, ignore_errors=True)
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

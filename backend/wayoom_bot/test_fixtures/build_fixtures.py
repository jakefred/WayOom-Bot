"""Build minimal .apkg test fixtures.

Run this script once (or any time the fixture format needs to change) to
regenerate the .apkg files used by ApkgImportTests.  The generated files are
committed alongside the tests so CI does not need to regenerate them.

Usage:
    python backend/wayoom_bot/test_fixtures/build_fixtures.py
"""

import io
import json
import os
import sqlite3
import tempfile
import time
import zipfile

FIXTURES_DIR = os.path.dirname(__file__)

# Collection creation timestamp: 2024-01-01 00:00:00 UTC
_CRT = 1704067200


def _make_col_row(models_dict: dict, decks_dict: dict) -> dict:
    return {
        "id": 1,
        "crt": _CRT,
        "mod": _CRT,
        "scm": _CRT,
        "ver": 11,
        "dty": 0,
        "usn": 0,
        "ls": 0,
        "conf": "{}",
        "models": json.dumps(models_dict),
        "decks": json.dumps(decks_dict),
        "dconf": "{}",
        "tags": "{}",
    }


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE col (
            id      INTEGER PRIMARY KEY,
            crt     INTEGER NOT NULL,
            mod     INTEGER NOT NULL,
            scm     INTEGER NOT NULL,
            ver     INTEGER NOT NULL,
            dty     INTEGER NOT NULL,
            usn     INTEGER NOT NULL,
            ls      INTEGER NOT NULL,
            conf    TEXT NOT NULL,
            models  TEXT NOT NULL,
            decks   TEXT NOT NULL,
            dconf   TEXT NOT NULL,
            tags    TEXT NOT NULL
        );
        CREATE TABLE notes (
            id      INTEGER PRIMARY KEY,
            guid    TEXT NOT NULL,
            mid     INTEGER NOT NULL,
            mod     INTEGER NOT NULL,
            usn     INTEGER NOT NULL,
            tags    TEXT NOT NULL,
            flds    TEXT NOT NULL,
            sfld    TEXT NOT NULL,
            csum    INTEGER NOT NULL,
            flags   INTEGER NOT NULL,
            data    TEXT NOT NULL
        );
        CREATE TABLE cards (
            id      INTEGER PRIMARY KEY,
            nid     INTEGER NOT NULL,
            did     INTEGER NOT NULL,
            ord     INTEGER NOT NULL,
            mod     INTEGER NOT NULL,
            usn     INTEGER NOT NULL,
            type    INTEGER NOT NULL,
            queue   INTEGER NOT NULL,
            due     INTEGER NOT NULL,
            ivl     INTEGER NOT NULL,
            factor  INTEGER NOT NULL,
            reps    INTEGER NOT NULL,
            lapses  INTEGER NOT NULL,
            left    INTEGER NOT NULL,
            odue    INTEGER NOT NULL,
            odid    INTEGER NOT NULL,
            flags   INTEGER NOT NULL,
            data    TEXT NOT NULL
        );
        CREATE TABLE revlog (
            id      INTEGER PRIMARY KEY,
            cid     INTEGER NOT NULL,
            usn     INTEGER NOT NULL,
            ease    INTEGER NOT NULL,
            ivl     INTEGER NOT NULL,
            lastIvl INTEGER NOT NULL,
            factor  INTEGER NOT NULL,
            time    INTEGER NOT NULL,
            type    INTEGER NOT NULL
        );
        CREATE TABLE graves (
            usn     INTEGER NOT NULL,
            oid     INTEGER NOT NULL,
            type    INTEGER NOT NULL
        );
    """)


def _insert_col(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        "INSERT INTO col VALUES (:id,:crt,:mod,:scm,:ver,:dty,:usn,:ls,"
        ":conf,:models,:decks,:dconf,:tags)",
        row,
    )


def _insert_note(conn: sqlite3.Connection, note_id: int, guid: str, mid: int,
                 flds: list[str], tags: str = "") -> None:
    conn.execute(
        "INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (note_id, guid, mid, _CRT, 0, tags, "\x1f".join(flds), flds[0], 0, 0, ""),
    )


def _insert_card(conn: sqlite3.Connection, card_id: int, nid: int, did: int,
                 ord_: int = 0, card_type: int = 2, queue: int = 2,
                 due: int = 1, ivl: int = 10, factor: int = 2500,
                 reps: int = 3, lapses: int = 0, flags: int = 0) -> None:
    conn.execute(
        "INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (card_id, nid, did, ord_, _CRT, 0, card_type, queue, due, ivl,
         factor, reps, lapses, 0, 0, 0, flags, ""),
    )


def _build_zip(sqlite_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("collection.anki21", sqlite_bytes)
        zf.writestr("media", "{}")
    return buf.getvalue()


def _db_bytes(conn: sqlite3.Connection) -> bytes:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    try:
        backup_conn = sqlite3.connect(tmp.name)
        conn.backup(backup_conn)
        backup_conn.close()
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Fixture 1: basic_deck.apkg
# One deck, two basic cards, tags, SR fields, one flagged card.
# ---------------------------------------------------------------------------

def build_basic_deck():
    model_id = 1000000001
    deck_id = 2000000001

    models = {
        str(model_id): {
            "id": model_id,
            "name": "Basic",
            "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
            "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": "{{Front}}", "afmt": "{{Back}}"}],
        }
    }
    decks = {
        str(deck_id): {"id": deck_id, "name": "Test Deck"},
    }

    conn = sqlite3.connect(":memory:")
    _init_schema(conn)
    _insert_col(conn, _make_col_row(models, decks))

    # Note 1: review card, tagged, extra field, flag=2 (orange)
    _insert_note(conn, 1001, "guid0001", model_id, ["What is Python?", "A programming language", "Extra info"], tags=" python programming ")
    _insert_card(conn, 2001, 1001, deck_id, ord_=0, card_type=2, queue=2, due=100, ivl=10, factor=2500, reps=5, lapses=1, flags=2)

    # Note 2: new card, no tags
    _insert_note(conn, 1002, "guid0002", model_id, ["What is Django?", "A web framework"])
    _insert_card(conn, 2002, 1002, deck_id, ord_=0, card_type=0, queue=0, due=5, ivl=0, factor=0, reps=0, lapses=0, flags=0)

    apkg = _build_zip(_db_bytes(conn))
    conn.close()

    path = os.path.join(FIXTURES_DIR, "basic_deck.apkg")
    with open(path, "wb") as f:
        f.write(apkg)
    print(f"Written: {path} ({len(apkg):,} bytes)")


# ---------------------------------------------------------------------------
# Fixture 2: multi_deck.apkg
# Two decks (simulating A::B nested naming), one card each.
# ---------------------------------------------------------------------------

def build_multi_deck():
    model_id = 1000000002
    deck_id_a = 2000000002
    deck_id_b = 2000000003

    models = {
        str(model_id): {
            "id": model_id,
            "name": "Basic",
            "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
            "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": "{{Front}}", "afmt": "{{Back}}"}],
        }
    }
    decks = {
        str(deck_id_a): {"id": deck_id_a, "name": "Languages::Python"},
        str(deck_id_b): {"id": deck_id_b, "name": "Languages::Java"},
    }

    conn = sqlite3.connect(":memory:")
    _init_schema(conn)
    _insert_col(conn, _make_col_row(models, decks))

    _insert_note(conn, 1003, "guid0003", model_id, ["Python question", "Python answer"])
    _insert_card(conn, 2003, 1003, deck_id_a)

    _insert_note(conn, 1004, "guid0004", model_id, ["Java question", "Java answer"])
    _insert_card(conn, 2004, 1004, deck_id_b)

    apkg = _build_zip(_db_bytes(conn))
    conn.close()

    path = os.path.join(FIXTURES_DIR, "multi_deck.apkg")
    with open(path, "wb") as f:
        f.write(apkg)
    print(f"Written: {path} ({len(apkg):,} bytes)")


# ---------------------------------------------------------------------------
# Fixture 3: card_types.apkg
# Three note types: basic, basic_reversed (2 templates), cloze.
# ---------------------------------------------------------------------------

def build_card_types():
    mid_basic = 1000000010
    mid_reversed = 1000000011
    mid_cloze = 1000000012
    deck_id = 2000000010

    models = {
        str(mid_basic): {
            "id": mid_basic,
            "name": "Basic",
            "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
            "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": "{{Front}}", "afmt": "{{Back}}"}],
        },
        str(mid_reversed): {
            "id": mid_reversed,
            "name": "Basic (and reversed card)",
            "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
            "tmpls": [
                {"name": "Card 1", "ord": 0, "qfmt": "{{Front}}", "afmt": "{{Back}}"},
                {"name": "Card 2", "ord": 1, "qfmt": "{{Back}}", "afmt": "{{Front}}"},
            ],
        },
        str(mid_cloze): {
            "id": mid_cloze,
            "name": "Cloze",
            "flds": [{"name": "Text", "ord": 0}, {"name": "Extra", "ord": 1}],
            "tmpls": [{"name": "Cloze", "ord": 0, "qfmt": "{{cloze:Text}}", "afmt": "{{cloze:Text}}{{Extra}}"}],
        },
    }
    decks = {str(deck_id): {"id": deck_id, "name": "Card Types"}}

    conn = sqlite3.connect(":memory:")
    _init_schema(conn)
    _insert_col(conn, _make_col_row(models, decks))

    # Basic note → 1 card (ord=0)
    _insert_note(conn, 1010, "guid0010", mid_basic, ["Basic front", "Basic back"])
    _insert_card(conn, 2010, 1010, deck_id, ord_=0)

    # Reversed note → 2 cards (ord=0 and ord=1)
    _insert_note(conn, 1011, "guid0011", mid_reversed, ["Rev front", "Rev back"])
    _insert_card(conn, 2011, 1011, deck_id, ord_=0)
    _insert_card(conn, 2012, 1011, deck_id, ord_=1)

    # Cloze note → 1 card
    _insert_note(conn, 1012, "guid0012", mid_cloze, ["The {{c1::capital}} of France is Paris.", ""])
    _insert_card(conn, 2013, 1012, deck_id, ord_=0)

    apkg = _build_zip(_db_bytes(conn))
    conn.close()

    path = os.path.join(FIXTURES_DIR, "card_types.apkg")
    with open(path, "wb") as f:
        f.write(apkg)
    print(f"Written: {path} ({len(apkg):,} bytes)")


if __name__ == "__main__":
    build_basic_deck()
    build_multi_deck()
    build_card_types()
    print("All fixtures built.")

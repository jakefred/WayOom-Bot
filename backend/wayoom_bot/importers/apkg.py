"""Anki .apkg importer for WayOom Bot.

Converts an Anki package file into WayOom Deck and Card model kwargs.
The caller is responsible for saving the returned objects inside a transaction.

Supported Anki formats:
  - .anki2  (Anki 2.0, schema v11 — JSON metadata in col table)
  - .anki21 (Anki 2.1, schema v11 — JSON metadata in col table)
  - .anki21b (Anki 2.1.50+, schema v18 — separate notetypes/decks tables,
              Protobuf config blobs, zstandard-compressed SQLite)

Public API:
  parse_apkg(file_bytes) -> ParseResult
"""

import io
import json
import sqlite3
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

# zstandard is only needed for .anki21b files; import lazily so a missing
# dependency produces a clear error only when that format is encountered.


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Stable WayOom namespace UUID — used as the namespace for all UUID v5
# generation.  Must never change; changing it would invalidate all existing
# dedup keys and re-import every card on the next sync.
_WAYOOM_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# Anki stores ease_factor as an integer (e.g. 2500 = 2.5×). We divide by 1000.
_ANKI_EASE_DIVISOR = 1000

# Maximum number of extra (non-front, non-back) fields to store as extra_notes.
_MAX_EXTRA_FIELDS = 20

# Anki card-type integers (cards.type column).
_ANKI_TYPE_NEW = 0
_ANKI_TYPE_LEARNING = 1
_ANKI_TYPE_REVIEW = 2
_ANKI_TYPE_RELEARN = 3  # treat as learning

# Anki card-queue integers (cards.queue column).
_ANKI_QUEUE_NEW = 0
_ANKI_QUEUE_LEARNING = 1
_ANKI_QUEUE_REVIEW = 2
_ANKI_QUEUE_DAY_LEARN = 3
_ANKI_QUEUE_SUSPENDED = -1
_ANKI_QUEUE_BURIED_SCHED = -2
_ANKI_QUEUE_BURIED_USER = -3


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    """Output of parse_apkg().

    decks  — list of dicts with Deck field kwargs (no 'id' or 'user' — caller sets those).
    cards  — list of dicts with Card field kwargs, plus '_deck_anki_id' for
             the caller to resolve to a Deck FK.
    errors — list of human-readable strings describing skipped items.
    """

    decks: list[dict[str, Any]] = field(default_factory=list)
    cards: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # Each entry: {"original_filename": str, "file_bytes": bytes}
    # Media is deck-scoped in Anki (any card can reference any file), so the
    # view associates each media file with every deck in the import.
    media: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# UUID helpers
# ---------------------------------------------------------------------------

def _anki_card_uuid(anki_guid: str, card_ord: int) -> uuid.UUID:
    """Return a deterministic UUID v5 for an Anki card.

    Uses the Anki note GUID and the card ordinal (template index) so that
    one note with multiple cards (e.g. Basic+Reversed) produces distinct UUIDs.
    The same GUID+ord always maps to the same UUID, enabling PK-based dedup
    via bulk_create(ignore_conflicts=True).
    """
    name = f"{anki_guid}:{card_ord}"
    return uuid.uuid5(_WAYOOM_NAMESPACE, name)


def _anki_deck_uuid(anki_deck_id: int, user_id: Any) -> uuid.UUID:
    """Return a deterministic UUID v5 for an Anki deck scoped to a user.

    Scoping to user_id ensures two users importing the same shared deck each
    get their own Deck object rather than colliding on a shared PK.
    """
    name = f"deck:{anki_deck_id}:user:{user_id}"
    return uuid.uuid5(_WAYOOM_NAMESPACE, name)


# ---------------------------------------------------------------------------
# Format detection and SQLite extraction
# ---------------------------------------------------------------------------

_FORMAT_ANKI21B = "anki21b"
_FORMAT_LEGACY = "legacy"


def _detect_format(zip_file: zipfile.ZipFile) -> tuple[bytes, str]:
    """Return the raw SQLite bytes and format identifier from the Anki archive.

    Returns:
        (sqlite_bytes, format_tag) where format_tag is "anki21b" or "legacy".
    """
    names = zip_file.namelist()

    if "collection.anki21b" in names:
        compressed = zip_file.read("collection.anki21b")
        try:
            import zstandard  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "The zstandard package is required to import .anki21b files. "
                "Install it with: pip install zstandard"
            ) from exc
        # Use stream_reader — Anki's zstd frames may omit the content-size
        # header, which causes dctx.decompress() to fail.
        dctx = zstandard.ZstdDecompressor()
        reader = dctx.stream_reader(io.BytesIO(compressed))
        sqlite_bytes = reader.read()
        reader.close()
        return sqlite_bytes, _FORMAT_ANKI21B

    if "collection.anki21" in names:
        return zip_file.read("collection.anki21"), _FORMAT_LEGACY

    if "collection.anki2" in names:
        return zip_file.read("collection.anki2"), _FORMAT_LEGACY

    raise ValueError(
        "Unrecognised .apkg format: archive does not contain "
        "collection.anki21b, collection.anki21, or collection.anki2."
    )


# ---------------------------------------------------------------------------
# Collection metadata — schema v11 (legacy .anki2 / .anki21)
# ---------------------------------------------------------------------------

def _parse_col_meta_v11(cursor: sqlite3.Cursor) -> tuple[dict, dict]:
    """Read models and decks from the legacy col table (schema v11).

    Returns:
        models_by_id  — {model_id_str: model_dict}
        decks_by_id   — {deck_id_str: deck_dict}
    """
    row = cursor.execute("SELECT models, decks FROM col LIMIT 1").fetchone()
    if row is None:
        raise ValueError("Anki collection table is empty.")
    models_json = row["models"]
    decks_json = row["decks"]
    if not models_json or not decks_json:
        raise ValueError("col.models or col.decks is empty (schema v18?).")
    models_by_id: dict[str, dict] = json.loads(models_json)
    decks_by_id: dict[str, dict] = json.loads(decks_json)
    return models_by_id, decks_by_id


# ---------------------------------------------------------------------------
# Collection metadata — schema v18 (.anki21b)
# ---------------------------------------------------------------------------

def _parse_col_meta_v18(cursor: sqlite3.Cursor) -> tuple[dict, dict]:
    """Read models and decks from the schema v18 tables.

    In schema v18, models live in the `notetypes` table and decks in the
    `decks` table. The `config` column is a Protobuf blob, but the `name`
    column is plain text. For note-type detection we also need the field
    and template definitions which live in separate tables.

    Returns:
        models_by_id  — {model_id_str: model_dict} with 'tmpls' and 'flds'
        decks_by_id   — {deck_id_str: deck_dict} with 'name'
    """
    # --- Note types ---
    models_by_id: dict[str, dict] = {}
    notetypes = cursor.execute("SELECT id, name FROM notetypes").fetchall()
    for nt in notetypes:
        nt_id = str(nt["id"])
        models_by_id[nt_id] = {"id": nt["id"], "name": nt["name"], "flds": [], "tmpls": []}

    # Read fields for each note type.
    fields_rows = cursor.execute("SELECT ntid, ord, name FROM fields ORDER BY ntid, ord").fetchall()
    for fr in fields_rows:
        nt_id = str(fr["ntid"])
        if nt_id in models_by_id:
            models_by_id[nt_id]["flds"].append({"name": fr["name"], "ord": fr["ord"]})

    # Read templates for each note type — we need qfmt for cloze detection.
    templates_rows = cursor.execute(
        "SELECT ntid, ord, name, config FROM templates ORDER BY ntid, ord"
    ).fetchall()
    for tr in templates_rows:
        nt_id = str(tr["ntid"])
        if nt_id in models_by_id:
            # In v18 the template text (qfmt/afmt) is inside the Protobuf config blob.
            # We extract what we can; for cloze detection we check the notetype name
            # as a fallback since the qfmt is in Protobuf.
            qfmt = _extract_template_qfmt(tr["config"]) if tr["config"] else ""
            models_by_id[nt_id]["tmpls"].append({
                "name": tr["name"],
                "ord": tr["ord"],
                "qfmt": qfmt,
            })

    # --- Decks ---
    decks_by_id: dict[str, dict] = {}
    deck_rows = cursor.execute("SELECT id, name FROM decks").fetchall()
    for dr in deck_rows:
        decks_by_id[str(dr["id"])] = {"id": dr["id"], "name": dr["name"]}

    return models_by_id, decks_by_id


def _extract_template_qfmt(config_blob: bytes) -> str:
    """Best-effort extraction of qfmt from a Protobuf template config blob.

    The Protobuf schema for CardTemplate has qfmt at field 2 (wire type 2 =
    length-delimited string). We scan for printable UTF-8 strings that look
    like Anki template syntax (contain '{{') rather than fully parsing Protobuf,
    since we only need this for cloze detection.

    Falls back to empty string if extraction fails.
    """
    try:
        # Walk through the blob looking for length-delimited fields.
        # Protobuf field 2 (qfmt) = tag byte 0x12 (field 2, wire type 2).
        pos = 0
        while pos < len(config_blob):
            if config_blob[pos] == 0x12:  # field 2, wire type 2
                pos += 1
                # Read varint length
                length, pos = _read_varint(config_blob, pos)
                if pos + length <= len(config_blob):
                    candidate = config_blob[pos:pos + length]
                    try:
                        text = candidate.decode("utf-8")
                        if "{{" in text:
                            return text
                    except UnicodeDecodeError:
                        pass
                pos += length
            else:
                # Skip this field
                pos = _skip_protobuf_field(config_blob, pos)
                if pos is None:
                    break
    except Exception:
        pass
    return ""


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Read a Protobuf varint starting at pos. Returns (value, new_pos)."""
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos


def _skip_protobuf_field(data: bytes, pos: int) -> int | None:
    """Skip a single Protobuf field starting at the tag byte. Returns new pos or None."""
    if pos >= len(data):
        return None
    tag = data[pos]
    wire_type = tag & 0x07
    pos += 1
    if wire_type == 0:  # varint
        _, pos = _read_varint(data, pos)
        return pos
    if wire_type == 1:  # 64-bit
        return pos + 8
    if wire_type == 2:  # length-delimited
        length, pos = _read_varint(data, pos)
        return pos + length
    if wire_type == 5:  # 32-bit
        return pos + 4
    return None


# ---------------------------------------------------------------------------
# Type / status mapping
# ---------------------------------------------------------------------------

def _map_note_type(model_dict: dict) -> str:
    """Map an Anki model dict to a WayOom CardType string.

    Detection logic:
      - If any template's qfmt contains '{{cloze:' → 'cloze'
      - If the model name contains 'cloze' (case-insensitive) → 'cloze'
        (fallback for v18 where qfmt may not be extractable from Protobuf)
      - If the model has exactly 2 templates → 'basic_reversed'
      - Otherwise → 'basic'
    """
    templates = model_dict.get("tmpls", [])

    for tmpl in templates:
        qfmt = tmpl.get("qfmt", "")
        if "{{cloze:" in qfmt:
            return "cloze"

    # Fallback: check the notetype name for "cloze" — covers v18 models
    # where the Protobuf qfmt extraction may have failed.
    name = model_dict.get("name", "").lower()
    if "cloze" in name:
        return "cloze"

    if len(templates) == 2:
        return "basic_reversed"

    return "basic"


def _map_card_status(anki_card_type: int, anki_queue: int) -> str:
    """Map Anki type/queue integers to a WayOom CardStatus string.

    Anki queue takes priority for suspended/buried states; otherwise use type.
    """
    if anki_queue == _ANKI_QUEUE_SUSPENDED:
        return "suspended"
    if anki_queue in (_ANKI_QUEUE_BURIED_SCHED, _ANKI_QUEUE_BURIED_USER):
        return "buried"
    if anki_card_type == _ANKI_TYPE_NEW:
        return "new"
    if anki_card_type in (_ANKI_TYPE_LEARNING, _ANKI_TYPE_RELEARN):
        return "learning"
    if anki_card_type == _ANKI_TYPE_REVIEW:
        return "review"
    # Fallback for unknown values.
    return "new"


def _convert_due_date(
    due: int,
    anki_queue: int,
    collection_creation_timestamp: int,
) -> datetime | None:
    """Convert Anki's due field to an absolute UTC datetime, or None.

    The meaning of due depends on the card's *queue*, not type:
      - Queue 2 (review) or 3 (day-learn): days since collection creation.
      - Queue 1 (learning): absolute Unix timestamp in seconds.
      - Queue 0 (new): position integer, not a date.
      - Queue <0 (suspended/buried): preserved but not meaningful.
    """
    if anki_queue in (_ANKI_QUEUE_REVIEW, _ANKI_QUEUE_DAY_LEARN):
        # days since collection creation → absolute datetime
        crt_dt = datetime.fromtimestamp(collection_creation_timestamp, tz=timezone.utc)
        return crt_dt + timedelta(days=due)

    if anki_queue == _ANKI_QUEUE_LEARNING:
        # absolute Unix timestamp (seconds)
        try:
            return datetime.fromtimestamp(due, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    # New / suspended / buried: due is not a date.
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_apkg(file_bytes: bytes) -> ParseResult:
    """Parse an Anki .apkg file and return unsaved model kwargs.

    Args:
        file_bytes: Raw bytes of the .apkg file.

    Returns:
        ParseResult with lists of deck kwargs, card kwargs, media entries, and
        error strings.  Card kwargs include '_deck_anki_id' (int) so the caller
        can resolve the correct Deck FK after creating decks.  Media entries
        are deck-scoped (Anki media is shared across all cards in a collection),
        so the view associates each media file with every deck in the import.

    Raises:
        ValueError: If the file is not a valid zip archive or .apkg.
    """
    # --- Open the zip archive ---
    try:
        zip_buf = io.BytesIO(file_bytes)
        zf = zipfile.ZipFile(zip_buf, "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("File is not a valid .apkg archive (bad zip).") from exc

    with zf:
        # --- Extract and open the SQLite database ---
        try:
            sqlite_bytes, fmt = _detect_format(zf)
        except (ValueError, ImportError):
            raise

        # Write SQLite bytes to a temp file — sqlite3 requires a real file path.
        # Use delete=False because on Windows the file cannot be opened by
        # sqlite3 while the NamedTemporaryFile handle holds a lock on it.
        import os as _os
        tmp = tempfile.NamedTemporaryFile(suffix=".anki.db", delete=False)
        try:
            tmp.write(sqlite_bytes)
            tmp.close()
            conn = sqlite3.connect(tmp.name)
            try:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                result = _parse_collection(cursor, fmt)
            finally:
                conn.close()
        finally:
            _os.unlink(tmp.name)

        # --- Extract media files from the zip ---
        # The 'media' file is a JSON object mapping numbered keys to original
        # filenames: {"0": "cat.jpg", "1": "pronunciation.mp3", ...}.
        # The actual file bytes live under the corresponding numbered entries.
        _extract_media(zf, result)

    return result


def _extract_media(zf: zipfile.ZipFile, result: ParseResult) -> None:
    """Read the Anki media manifest and extract file bytes into result.media.

    Anki media is collection-level, not deck-level: any card can reference any
    file.  We store the bytes here; the view will associate each file with every
    deck in the import.

    Silently skips the media section if the manifest is missing or malformed,
    and records per-file errors rather than aborting the whole import.
    """
    if "media" not in zf.namelist():
        return

    try:
        manifest: dict[str, str] = json.loads(zf.read("media"))
    except (json.JSONDecodeError, KeyError):
        result.errors.append("Could not read media manifest — media files skipped.")
        return

    for numbered_key, original_filename in manifest.items():
        if not original_filename or not numbered_key:
            continue
        try:
            file_bytes = zf.read(numbered_key)
        except KeyError:
            result.errors.append(
                f"Media file {original_filename!r} listed in manifest but missing from archive — skipped."
            )
            continue
        result.media.append(
            {
                "original_filename": original_filename,
                "file_bytes": file_bytes,
            }
        )


def _parse_collection(cursor: sqlite3.Cursor, fmt: str) -> ParseResult:
    """Do all the parsing work once we have a live cursor into the collection DB."""
    result = ParseResult()

    # --- Read collection-level metadata (format-dependent) ---
    try:
        if fmt == _FORMAT_ANKI21B:
            models_by_id, decks_by_id = _parse_col_meta_v18(cursor)
        else:
            models_by_id, decks_by_id = _parse_col_meta_v11(cursor)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read Anki collection metadata: {exc}") from exc

    # Read collection creation timestamp (used for review due-date conversion).
    crt_row = cursor.execute("SELECT crt FROM col LIMIT 1").fetchone()
    collection_crt: int = crt_row["crt"] if crt_row else 0

    # Track which anki_deck_ids have cards so we skip empty decks.
    anki_deck_ids: set[int] = set()

    # --- Join notes + cards to get full card data ---
    rows = cursor.execute(
        """
        SELECT
            n.guid         AS note_guid,
            n.mid          AS model_id,
            n.flds         AS fields,
            n.tags         AS tags_raw,
            c.id           AS card_id,
            c.did          AS deck_id,
            c.ord          AS card_ord,
            c.type         AS card_type,
            c.queue        AS card_queue,
            c.due          AS due,
            c.ivl          AS interval,
            c.factor       AS ease_factor,
            c.reps         AS review_count,
            c.lapses       AS lapse_count,
            c.flags        AS flags
        FROM cards c
        JOIN notes n ON n.id = c.nid
        ORDER BY c.id
        """
    ).fetchall()

    for row in rows:
        try:
            card_kwargs = _build_card_kwargs(row, models_by_id, collection_crt)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(
                f"Skipped card (note_guid={row['note_guid']!r}, "
                f"ord={row['card_ord']}): {exc}"
            )
            continue

        anki_deck_ids.add(row["deck_id"])
        result.cards.append(card_kwargs)

    # --- Build deck kwargs for every deck that actually has cards ---
    for deck_id_str, deck_dict in decks_by_id.items():
        try:
            anki_id = int(deck_id_str)
        except ValueError:
            continue
        if anki_id not in anki_deck_ids:
            continue  # skip empty decks

        deck_name: str = deck_dict.get("name", f"Imported Deck {anki_id}")
        result.decks.append(
            {
                "_anki_id": anki_id,
                "name": deck_name,
            }
        )

    return result


def _build_card_kwargs(
    row: sqlite3.Row,
    models_by_id: dict[str, dict],
    collection_crt: int,
) -> dict[str, Any]:
    """Convert a single joined note+card row into Card model kwargs."""
    note_guid: str = row["note_guid"]
    model_id: int = row["model_id"]
    card_ord: int = row["card_ord"]
    anki_card_type: int = row["card_type"]
    anki_queue: int = row["card_queue"]

    # --- Resolve model / note type ---
    model = models_by_id.get(str(model_id))
    if model is None:
        raise ValueError(f"Unknown model id {model_id}")

    card_type = _map_note_type(model)

    # --- Parse fields (0x1F unit-separator delimited in Anki) ---
    raw_fields = row["fields"].split("\x1f")

    front = raw_fields[0] if len(raw_fields) > 0 else ""
    back = raw_fields[1] if len(raw_fields) > 1 else ""

    # Remaining fields go into extra_notes (capped at _MAX_EXTRA_FIELDS).
    extra_notes = [f for f in raw_fields[2:] if f]
    extra_notes = extra_notes[:_MAX_EXTRA_FIELDS]

    # --- Tags: Anki stores space-separated, with leading/trailing spaces ---
    tags_raw: str = row["tags_raw"]
    tags = [t for t in tags_raw.strip().split() if t]

    # --- Spaced repetition fields ---
    status = _map_card_status(anki_card_type, anki_queue)
    due_date = _convert_due_date(row["due"], anki_queue, collection_crt)
    interval = max(0, row["interval"])  # can be negative in learning steps
    ease_factor = row["ease_factor"] / _ANKI_EASE_DIVISOR
    review_count = max(0, row["review_count"])
    lapse_count = max(0, row["lapse_count"])

    # --- Flag: low 3 bits of the flags column (0–7) ---
    flag = row["flags"] & 0x07

    # --- Deterministic UUID from GUID + ordinal ---
    card_uuid = _anki_card_uuid(note_guid, card_ord)

    return {
        "id": card_uuid,
        "_deck_anki_id": row["deck_id"],
        "card_type": card_type,
        "front": front,
        "back": back,
        "extra_notes": extra_notes,
        "tags": tags,
        "status": status,
        "due_date": due_date,
        "interval": interval,
        "ease_factor": ease_factor,
        "review_count": review_count,
        "lapse_count": lapse_count,
        "flag": flag,
        "position": None,
    }

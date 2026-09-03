"""
tools/contacts_import.py — bulk contact import into the CRM: Google Contacts pull
and conventional file import (vCard, CSV).

[DB-0810-17] Answers the two pieces of the "external CRM bridge" backlog item that
turned out to be the actual requirement once the per-vendor-API framing was dropped:
there is no CRM to integrate against, only two ways contact data arrives — a pull
from the Google account already wired up read-only in tools/google_contacts.py, and
a file a user exports from wherever they already keep contacts (any CRM, Outlook,
a phone). Both paths land in the same store tools/crm.py already owns.

This module is built entirely on tools/crm.py's public functions (list_contacts,
write_contact, merge_contacts) — it never reads or writes contacts.json directly,
and it does not modify tools/crm.py's matching logic.

Dedup is the point, not a nice-to-have (a bulk import is exactly where duplicate
records get created at volume — see [DB-0815-07] in tools/crm.py). Two layers:

  1. Identity match (email, then phone, then exact case-insensitive name) is
     treated as "this is the same record" and updates it in place via write_contact's
     contact_id path — this is what makes re-running an import idempotent.
  2. Anything softer — a name that merely resembles an existing one — is left to
     write_contact's own _dedup_candidates surfacing (tools/crm.py). This module
     never calls merge_contacts itself; it collects and reports what write_contact
     already surfaced as evidence, same "evidence, not a verdict" pattern the CRM
     uses everywhere else. A human (or the calling agent, with the user) decides
     whether to fold two records together.

vCard parsing is hand-rolled rather than a dependency: the fields this import path
needs (FN, N, EMAIL, TEL, ORG, NOTE) are a small, stable slice of RFC 6350, and the
project has no existing vCard use elsewhere to justify a new third-party package for
it. CSV uses the stdlib csv module with tolerant, substring-based header matching
so a Google Contacts export ("E-mail 1 - Value") and an Outlook export ("E-mail
Address") both land on the same canonical field, and any column that doesn't match
a known field is preserved in notes rather than silently dropped.

Google Contacts write-back stays out of scope — deliberately, per the backlog item;
nothing here writes to the Google side.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import tools.crm as crm

# ---------------------------------------------------------------------------
# Shared plumbing
# ---------------------------------------------------------------------------


def _normalize_phone(phone: str) -> str:
    """Digits only, so '(415) 555-0100' and '415-555-0100' compare equal."""
    return re.sub(r"\D", "", phone or "")


def _find_exact_contact(contacts: list[dict], name: str, emails: list[str], phones: list[str]) -> dict | None:
    """
    Identity match for import idempotence — distinct from tools/crm.py's
    _dedup_candidates, which finds *soft* name resemblance for a human to weigh.
    This is deliberately narrower and returns at most one record: an email match,
    then a phone match, then an exact (case-insensitive) name match. Any of these
    is treated as "this is the same contact arriving again," so re-running an
    import updates the existing record via write_contact's contact_id path
    instead of creating a new one each time.
    """
    emails_l = {e.strip().lower() for e in emails if e}
    phones_n = {_normalize_phone(p) for p in phones if p}

    if emails_l:
        for c in contacts:
            c_email = str((c.get("contact_info") or {}).get("email", "")).strip().lower()
            if c_email and c_email in emails_l:
                return c

    if phones_n:
        for c in contacts:
            c_phone = _normalize_phone(str((c.get("contact_info") or {}).get("phone", "")))
            if c_phone and c_phone in phones_n:
                return c

    name_l = name.strip().lower()
    if name_l:
        for c in contacts:
            if c.get("name", "").strip().lower() == name_l:
                return c

    return None


def _strip_placeholder_fields(contact_info: dict) -> tuple[dict, list[str]]:
    """
    Drop known-placeholder values from contact_info, returning the cleaned dict and
    a reason line per dropped field.

    write_contact refuses the WHOLE record when any single field is a placeholder
    ([DB-0815-06]) — correct for a model inventing a contact one field at a time,
    wrong for a bulk import, where it silently costs a real person their record over
    one junk field they had saved in Google Contacts years ago. On an import path the
    person is the thing worth keeping and the field is not: a missing phone is
    recoverable from the user, a missing person is not, because nothing afterwards
    knows they were dropped.

    So the guard is not weakened — it still refuses these values — it is applied one
    level finer, per field instead of per record, and every drop is reported rather
    than swallowed. A placeholder NAME is deliberately not stripped here: it is the
    record's only anchor, so that record really is skipped, by write_contact.
    """
    cleaned = dict(contact_info)
    dropped: list[str] = []

    given_email = str(cleaned.get("email", "")).strip().lower()
    if given_email and "@" in given_email:
        if crm._is_placeholder_email_domain(given_email.rsplit("@", 1)[-1]):
            cleaned.pop("email", None)
            dropped.append(f"dropped placeholder email '{given_email}'")

    given_phone = str(cleaned.get("phone", "")).strip()
    if given_phone:
        reason = crm._is_placeholder_phone(given_phone)
        if reason:
            cleaned.pop("phone", None)
            dropped.append(f"dropped placeholder phone '{given_phone}' ({reason})")

    given_address = str(cleaned.get("address", "")).strip()
    if given_address:
        reason = crm._is_placeholder_address(given_address)
        if reason:
            cleaned.pop("address", None)
            dropped.append(f"dropped placeholder address '{given_address}' ({reason})")

    social = cleaned.get("social")
    if isinstance(social, dict):
        kept_social = {}
        for platform, handle in social.items():
            reason = crm._is_placeholder_social_handle(str(handle))
            if reason:
                dropped.append(f"dropped placeholder {platform} handle '{handle}'")
            else:
                kept_social[platform] = handle
        if kept_social:
            cleaned["social"] = kept_social
        else:
            cleaned.pop("social", None)

    return cleaned, dropped


def _import_batch(raw_contacts: list[dict], source_label: str) -> str:
    """
    Write a list of normalized contact dicts (name, first_name, last_name,
    emails, phones, organization, notes — all optional except name) into the CRM
    via tools/crm.py's public write_contact, deduping on the way in.

    Returns a human-readable report: created/updated/skipped counts, plus any
    near-match evidence write_contact surfaced (not auto-merged) and any
    placeholder field dropped to keep an otherwise-real contact.
    """
    created, updated, skipped = 0, 0, 0
    warnings: list[str] = []

    for rc in raw_contacts:
        name = (rc.get("name") or "").strip()
        if not name:
            skipped += 1
            continue

        emails = [e for e in rc.get("emails", []) if e]
        phones = [p for p in rc.get("phones", []) if p]
        contact_info: dict = {}
        if emails:
            contact_info["email"] = emails[0]
        if phones:
            contact_info["phone"] = phones[0]

        contact_info, dropped_fields = _strip_placeholder_fields(contact_info)
        if dropped_fields:
            warnings.append(f"{name}: " + "; ".join(dropped_fields))

        # Placeholder values must also leave the identity-matching lists, not just
        # contact_info. Two unrelated people who both had "555-0100" saved would
        # otherwise match each other on it and silently collapse into one record —
        # a bulk import is precisely where that happens at volume.
        emails = [
            e for e in emails
            if not ("@" in e and crm._is_placeholder_email_domain(e.strip().lower().rsplit("@", 1)[-1]))
        ]
        phones = [p for p in phones if not crm._is_placeholder_phone(p)]

        write_kwargs = dict(
            name=name,
            first_name=rc.get("first_name", ""),
            last_name=rc.get("last_name", ""),
            employer=rc.get("organization", ""),
            notes=rc.get("notes", ""),
            contact_info=contact_info or None,
        )

        contacts = json.loads(crm.list_contacts())
        match = _find_exact_contact(contacts, name, emails, phones)

        # _bulk on BOTH branches: an import reports near-match evidence at batch level
        # rather than raising one blocking confirmation per record. See the gates in
        # tools/crm.py. The update branch needs it too as of 2026-08-26, when a rename
        # of an existing record became a gated act — a phone-matched contact whose name
        # differs from the CRM's is an ordinary import outcome, not a silent rename by
        # a model, and 200 of them would be 200 ten-minute confirmations.
        # _verified_source: these details came out of the user's own Google address
        # book, not out of a conversation — so a later in-conversation correction to
        # one of them asks once before replacing it ([DB-0818-08]). This is the only
        # caller that marks anything today; a header or invite reader would be the
        # next. It rides alongside _bulk deliberately: _bulk suppresses the CARDS an
        # import would otherwise raise 200 of, and marking is not a card.
        if match:
            outcome = crm.write_contact(contact_id=match["id"], _bulk=True,
                                        _verified_source="google_contacts", **write_kwargs)
        else:
            outcome = crm.write_contact(_bulk=True,
                                        _verified_source="google_contacts", **write_kwargs)

        if outcome.startswith("Error:"):
            skipped += 1
            warnings.append(f"{name}: {outcome}")
            continue

        if match:
            updated += 1
        else:
            created += 1
            if "Possible existing match" in outcome:
                note = "\n".join(outcome.splitlines()[1:]).strip()
                if note:
                    warnings.append(f"{name}: {note}")

    summary = f"{source_label}: {created} created, {updated} updated, {skipped} skipped."
    if warnings:
        summary += (
            "\n\nEvidence surfaced during import (not auto-merged — review and call "
            "merge_contacts if these are the same person):\n"
        )
        summary += "\n".join(f"- {w}" for w in warnings)
    return summary


# ---------------------------------------------------------------------------
# Google Contacts pull
# ---------------------------------------------------------------------------


def import_google_contacts(query: str = "") -> str:
    """
    Pull contacts from the persona's connected Google account
    (tools/google_contacts.py's read_google_contacts) and write or update them in
    the CRM (tools/crm.py).

    Args:
        query: Optional substring passed through to read_google_contacts to limit
            the pull to matching name/email. Omit to pull everything.

    Idempotent: re-running with the same source data updates the same records
    (matched by email, then phone, then exact name) rather than creating
    duplicates. A name that merely resembles an existing contact, without a
    matching email/phone/exact-name, is left to write_contact's own dedup
    evidence rather than merged automatically — see _import_batch.

    Returns a human-readable report (counts + any near-match evidence), or an
    Error string if the persona hasn't completed Google Contacts authorization
    (scripts/google_contacts_authorize.py).
    """
    from tools.google_contacts import read_google_contacts

    result = read_google_contacts(query)
    if "error" in result:
        return f"Error: {result['error']}"

    raw_contacts = [
        {
            "name": gc.get("name", ""),
            "first_name": "",
            "last_name": "",
            "emails": gc.get("emails", []),
            "phones": gc.get("phones", []),
            "organization": "",
            "notes": "",
        }
        for gc in result.get("contacts", [])
    ]
    return _import_batch(raw_contacts, source_label="Google Contacts import")


# ---------------------------------------------------------------------------
# vCard (.vcf) parsing — hand-rolled, see module docstring for why
# ---------------------------------------------------------------------------


def _unescape_vcard(value: str) -> str:
    """RFC 6350 §3.4 backslash escaping — only the handful of sequences this
    module's field set (FN, N, EMAIL, TEL, ORG, NOTE) actually produces."""
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def _parse_vcard(text: str) -> list[dict]:
    """
    Minimal RFC 6350 parser covering the fields a contact record needs: FN
    (display name), N (structured name), EMAIL, TEL, ORG, NOTE. Unfolds
    continuation lines (a line starting with a space or tab extends the
    previous line) before parsing, per RFC 6350 §3.2.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded: list[str] = []
    for line in lines:
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)

    contacts: list[dict] = []
    current: dict | None = None

    for line in unfolded:
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if upper == "BEGIN:VCARD":
            current = {
                "name": "", "first_name": "", "last_name": "",
                "emails": [], "phones": [], "organization": "", "notes": "",
            }
            continue
        if upper == "END:VCARD":
            if current is not None:
                if not current["name"]:
                    current["name"] = " ".join(
                        p for p in (current["first_name"], current["last_name"]) if p
                    ).strip()
                contacts.append(current)
            current = None
            continue
        if current is None or ":" not in stripped:
            continue

        key_part, value = stripped.split(":", 1)
        key = key_part.split(";")[0].upper()

        if key == "FN":
            current["name"] = _unescape_vcard(value).strip()
        elif key == "N":
            parts = value.split(";")
            current["last_name"] = _unescape_vcard(parts[0]).strip() if len(parts) > 0 else ""
            current["first_name"] = _unescape_vcard(parts[1]).strip() if len(parts) > 1 else ""
        elif key == "EMAIL":
            v = _unescape_vcard(value).strip()
            if v:
                current["emails"].append(v)
        elif key == "TEL":
            v = _unescape_vcard(value).strip()
            if v:
                current["phones"].append(v)
        elif key == "ORG":
            current["organization"] = _unescape_vcard(value.split(";")[0]).strip()
        elif key == "NOTE":
            current["notes"] = _unescape_vcard(value).strip()

    return contacts


# ---------------------------------------------------------------------------
# CSV parsing — tolerant header mapping
# ---------------------------------------------------------------------------


def _classify_header(header: str) -> str | None:
    """
    Map a CSV column header onto a canonical field, tolerant of the common
    Google Contacts export ("E-mail 1 - Value", "Phone 1 - Value") and Outlook
    export ("E-mail Address", "Business Phone") header shapes. Returns None for
    a header that doesn't match any known field — the caller preserves that
    column's value in notes rather than dropping it.
    """
    h = header.strip().lower()
    if "e-mail" in h or "email" in h:
        return "email"
    if "phone" in h:
        return "phone"
    if h in ("first name", "given name"):
        return "first_name"
    if h in ("last name", "family name", "surname"):
        return "last_name"
    if h in ("name", "full name", "display name"):
        return "name"
    if "organization" in h or "company" in h:
        return "organization"
    if "note" in h:
        return "notes"
    return None


def _parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    contacts: list[dict] = []

    for row in reader:
        c = {
            "name": "", "first_name": "", "last_name": "",
            "emails": [], "phones": [], "organization": "", "notes": "",
        }
        extras: list[str] = []

        for header, value in row.items():
            if not isinstance(header, str) or value is None:
                continue
            if isinstance(value, list):
                value = " ".join(v for v in value if v)
            value = value.strip()
            if not value:
                continue

            field = _classify_header(header)
            if field == "email":
                c["emails"].append(value)
            elif field == "phone":
                c["phones"].append(value)
            elif field == "first_name":
                c["first_name"] = value
            elif field == "last_name":
                c["last_name"] = value
            elif field == "name":
                c["name"] = value
            elif field == "organization":
                c["organization"] = value
            elif field == "notes":
                c["notes"] = f"{c['notes']}\n{value}" if c["notes"] else value
            else:
                # Unrecognized column — kept, not dropped.
                extras.append(f"{header.strip()}: {value}")

        if not c["name"]:
            c["name"] = " ".join(p for p in (c["first_name"], c["last_name"]) if p).strip()
        if extras:
            extra_text = "Imported fields not otherwise mapped: " + "; ".join(extras)
            c["notes"] = f"{c['notes']}\n\n{extra_text}" if c["notes"] else extra_text
        if c["name"] or c["emails"] or c["phones"]:
            contacts.append(c)

    return contacts


# ---------------------------------------------------------------------------
# File import entry point
# ---------------------------------------------------------------------------


def import_contacts_file(path: str, source_format: str = "auto") -> str:
    """
    Import contacts from a vCard (.vcf) or CSV file into the CRM.

    Args:
        path: Path to the file.
        source_format: "vcard", "csv", or "auto" (default — chosen from the file
            extension; anything not ending in .vcf is treated as CSV).

    Same dedup and idempotence behavior as import_google_contacts (see
    _import_batch): matched by email, then phone, then exact name; a softer
    name resemblance is surfaced as evidence, not auto-merged.

    Returns a human-readable report, or an Error string if the file is missing
    or the format is unrecognized.
    """
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"

    fmt = source_format.strip().lower()
    if fmt == "auto":
        fmt = "vcard" if p.suffix.lower() == ".vcf" else "csv"

    if fmt == "vcard":
        raw_contacts = _parse_vcard(p.read_text(encoding="utf-8", errors="replace"))
    elif fmt == "csv":
        raw_contacts = _parse_csv(p.read_text(encoding="utf-8-sig", errors="replace"))
    else:
        return f"Error: unsupported source_format '{source_format}' (use 'vcard', 'csv', or 'auto')"

    return _import_batch(raw_contacts, source_label=f"File import ({p.name})")


# ---------------------------------------------------------------------------
# Tool schemas — NOT registered here. The coordinator wires these into
# core/orchestrator.py's register_tools() and grants them in routing — see
# archive/handoffs/2026-08-15-contacts-import.md.
# ---------------------------------------------------------------------------

IMPORT_GOOGLE_CONTACTS_SCHEMA = {
    "name": "import_google_contacts",
    "description": (
        "Pull contacts from the user's connected Google account and write or update "
        "them in the CRM. Idempotent — re-running matches existing records by email, "
        "phone, or exact name and updates them rather than creating duplicates. A "
        "softer name resemblance to an existing contact is reported as evidence, not "
        "auto-merged; use merge_contacts if it turns out to be the same person. "
        "Requires the persona to have completed Google Contacts authorization "
        "(scripts/google_contacts_authorize.py) — returns an Error string, not an "
        "empty result, if that hasn't happened."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Optional name or email substring to limit the pull. Omit to pull everything.",
            },
        },
        "required": [],
    },
}

IMPORT_CONTACTS_FILE_SCHEMA = {
    "name": "import_contacts_file",
    "description": (
        "Import contacts from a vCard (.vcf) or CSV file (Google Contacts export, "
        "Outlook export, or similar) into the CRM. Idempotent and dedup-aware in the "
        "same way as import_google_contacts. Any CSV column that doesn't map to a "
        "known field is preserved in the contact's notes rather than dropped."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the .vcf or .csv file to import.",
            },
            "source_format": {
                "type": "string",
                "description": "One of: vcard, csv, auto. Defaults to auto (chosen from the file extension).",
            },
        },
        "required": ["path"],
    },
}

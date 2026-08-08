#!/usr/bin/env python3
"""
scripts/import_vcard_contacts.py — bulk-import contacts from a vCard (.vcf) export
into the local CRM (tools/crm.py).

Replaces the Google Contacts OAuth path (built and reversed 2026-08-07/08 — see
DEV_BACKLOG.md [DB-0808-01]) with the portable version of the same need: vCard is the
actual interchange standard (Google, Apple, and Outlook all export to it), so this works
identically regardless of which ecosystem the contacts came from, needs no OAuth, no
token to keep fresh, and no third-party account.

Export a .vcf from Google Contacts (or Apple Contacts, or Outlook) and run:

    python3 scripts/import_vcard_contacts.py --persona mike --file contacts.vcf
    python3 scripts/import_vcard_contacts.py --persona mike --file contacts.vcf --dry-run

Every write goes through write_contact(), so the misattribution guardrail applies
automatically — a card matching the user's own email/phone (common: "My Contacts"
exports frequently include yourself) is refused, not silently imported. A near-match is
flagged in the summary. Existing contacts (matched by email) are skipped, not
overwritten, so a rerun after manually refining a contact in conversation doesn't clobber
that work — a repeat import is safe to run.
"""

import argparse
import sys
from pathlib import Path

import vobject

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.persona import persona_scope
from tools.crm import _load_contacts, write_contact


def _existing_emails(contacts: list[dict]) -> set[str]:
    out = set()
    for c in contacts:
        email = (c.get("contact_info") or {}).get("email", "")
        if email:
            out.add(email.strip().lower())
    return out


def _extract(card) -> dict:
    name = card.fn.value if hasattr(card, "fn") else ""
    first_name, last_name = "", ""
    if hasattr(card, "n"):
        n = card.n.value
        first_name, last_name = getattr(n, "given", "") or "", getattr(n, "family", "") or ""

    email = ""
    if hasattr(card, "email_list") and card.email_list:
        email = card.email_list[0].value

    phone = ""
    if hasattr(card, "tel_list") and card.tel_list:
        phone = card.tel_list[0].value

    employer = ""
    if hasattr(card, "org"):
        org_value = card.org.value
        employer = org_value[0] if isinstance(org_value, list) and org_value else str(org_value or "")

    return {
        "name": name or f"{first_name} {last_name}".strip() or "(no name)",
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "employer": employer,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", required=True)
    parser.add_argument("--file", required=True, help="Path to the .vcf export.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    args = parser.parse_args()

    vcf_path = Path(args.file)
    if not vcf_path.exists():
        print(f"File not found: {vcf_path}", file=sys.stderr)
        sys.exit(1)

    imported, skipped_duplicate, refused, flagged = [], [], [], []

    with persona_scope(args.persona):
        existing = _existing_emails(_load_contacts())

        with open(vcf_path, encoding="utf-8") as f:
            cards = list(vobject.readComponents(f.read()))

        print(f"Found {len(cards)} card(s) in {vcf_path}.")

        for card in cards:
            info = _extract(card)
            key = info["email"].strip().lower()

            if key and key in existing:
                skipped_duplicate.append(info["name"])
                continue

            if args.dry_run:
                imported.append(info["name"])
                continue

            contact_info = {}
            if info["email"]:
                contact_info["email"] = info["email"]
            if info["phone"]:
                contact_info["phone"] = info["phone"]

            result = write_contact(
                name=info["name"],
                first_name=info["first_name"],
                last_name=info["last_name"],
                employer=info["employer"],
                contact_info=contact_info or None,
            )

            if result.startswith("Error: not saved"):
                refused.append((info["name"], result))
            elif "Warning:" in result:
                flagged.append((info["name"], result))
                imported.append(info["name"])
            else:
                imported.append(info["name"])

    mode = "Would import" if args.dry_run else "Imported"
    print(f"\n{mode}: {len(imported)}")
    for name in imported:
        print(f"  + {name}")
    print(f"\nSkipped (already in CRM): {len(skipped_duplicate)}")
    for name in skipped_duplicate:
        print(f"  = {name}")
    if refused:
        print(f"\nRefused (matches the user's own identity — likely your own card in the export): {len(refused)}")
        for name, reason in refused:
            print(f"  ! {name}: {reason.splitlines()[0]}")
    if flagged:
        print(f"\nFlagged for review (close to the user's own identity, saved anyway): {len(flagged)}")
        for name, reason in flagged:
            print(f"  ? {name}")


if __name__ == "__main__":
    main()

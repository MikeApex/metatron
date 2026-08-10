#!/usr/bin/env bash
# scripts/new_persona.sh — provision a new persona from templates.
#
# Every persona owns a complete universe: an identity file, a config directory
# for tiers 1-3 and settings, and (created lazily on first write) a data
# directory. This creates the config side; data directories appear by themselves.
#
# Usage:
#   ./scripts/new_persona.sh alex
#
# Settings files are gitignored — they hold personal data and credentials.
# Nothing is overwritten: existing files are left untouched and reported.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:-}"

if [[ -z "$NAME" ]]; then
    echo "usage: $0 <persona-name>" >&2
    echo "  name must match ^[a-z0-9][a-z0-9_]{0,39}\$ (lowercase, digits, underscores)" >&2
    exit 1
fi

# Same rule the resolver enforces — fail here rather than at runtime.
if ! [[ "$NAME" =~ ^[a-z0-9][a-z0-9_]{0,39}$ ]]; then
    echo "error: '$NAME' is not a valid persona name." >&2
    echo "  must match ^[a-z0-9][a-z0-9_]{0,39}\$ — lowercase letters, digits and" >&2
    echo "  underscores only. Persona names become filesystem paths." >&2
    exit 1
fi

CONFIG_DIR="$ROOT/config/personas/$NAME"
IDENTITY="$ROOT/config/personas/$NAME.md"
TEMPLATES="$ROOT/config/templates"

mkdir -p "$CONFIG_DIR"

created=0
skipped=0

if [[ -f "$IDENTITY" ]]; then
    echo "  exists   config/personas/$NAME.md"
    skipped=$((skipped + 1))
else
    cat > "$IDENTITY" <<EOF
# User: $NAME

Primary user of this system. Address them as "$NAME" in every response.

## Interaction Preferences

<!-- Filled in as preferences emerge, or written by the write_persona tool
     when the user states one explicitly. -->
EOF
    echo "  created  config/personas/$NAME.md"
    created=$((created + 1))
fi

for tier in prime_directive.md mission.md; do
    if [[ -f "$CONFIG_DIR/$tier" ]]; then
        echo "  exists   config/personas/$NAME/$tier"
        skipped=$((skipped + 1))
    else
        echo "<!-- Populated by the Goals Interview. Do not fill in speculatively. -->" \
            > "$CONFIG_DIR/$tier"
        echo "  created  config/personas/$NAME/$tier"
        created=$((created + 1))
    fi
done

if [[ -f "$CONFIG_DIR/goals.yaml" ]]; then
    echo "  exists   config/personas/$NAME/goals.yaml"
    skipped=$((skipped + 1))
else
    printf 'quarterly: []\nweekly: []\ndaily: []\n' > "$CONFIG_DIR/goals.yaml"
    echo "  created  config/personas/$NAME/goals.yaml"
    created=$((created + 1))
fi

for f in profile.yaml scheduler.yaml caldav.yaml email.yaml; do
    if [[ -f "$CONFIG_DIR/$f" ]]; then
        echo "  exists   config/personas/$NAME/$f"
        skipped=$((skipped + 1))
    elif [[ -f "$TEMPLATES/$f" ]]; then
        cp "$TEMPLATES/$f" "$CONFIG_DIR/$f"
        echo "  created  config/personas/$NAME/$f  (from template)"
        created=$((created + 1))
    else
        echo "  WARNING  no template for $f — skipped" >&2
    fi
done

chmod 600 "$CONFIG_DIR"/* "$IDENTITY" 2>/dev/null || true

echo
echo "Persona '$NAME' provisioned: $created created, $skipped already existed."
echo
echo "Next:"
echo "  1. Fill in config/personas/$NAME/profile.yaml (name, city, timezone)"
echo "  2. Run the Goals Interview to populate prime_directive, mission and goals:"
echo "       python core/orchestrator.py --agent goals_interviewer --persona $NAME"
echo "  3. Verify:  python scripts/check_personas.py"
echo
echo "Note: settings files are gitignored. To deploy this persona to the VM,"
echo "copy them across manually — a git deploy will not carry them."

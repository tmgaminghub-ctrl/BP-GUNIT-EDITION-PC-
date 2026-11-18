#!/bin/sh
# Create the GitHub repository and push this tree, in one step.
#
# One-time prerequisites:
#   1. Install the GitHub CLI:  https://cli.github.com/
#   2. Authenticate:            gh auth login
#
# Then, from the repository root:
#   sh scripts/push-to-github.sh [owner/]repo-name [--private]
#
# Examples:
#   sh scripts/push-to-github.sh bulletproof-pc
#   sh scripts/push-to-github.sh myname/bulletproof-pc --private
#
# Nothing here uploads game data: the tree is checked first and the push is
# refused if the source-only guard fails.
set -eu
cd "$(dirname "$0")/.."

NAME="${1:-bulletproof-pc}"
shift 2>/dev/null || true
VISIBILITY="--public"
for arg in "$@"; do
    case "$arg" in
        --private) VISIBILITY="--private" ;;
        --public)  VISIBILITY="--public" ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

if ! command -v gh >/dev/null 2>&1; then
    echo "GitHub CLI (gh) is not installed. Either install it, or create the repo in the web UI and run:" >&2
    echo "  git remote add origin git@github.com:YOUR-NAME/$NAME.git && git push -u origin main" >&2
    exit 1
fi
gh auth status >/dev/null 2>&1 || { echo "Run 'gh auth login' first." >&2; exit 1; }

python3 scripts/check_source_only.py
python3 scripts/check_docs.py
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Not a git repository." >&2; exit 1; }

if git remote get-url origin >/dev/null 2>&1; then
    echo "Pushing to the existing 'origin'..."
    git push -u origin HEAD
else
    echo "Creating $NAME ($VISIBILITY) and pushing..."
    gh repo create "$NAME" "$VISIBILITY" --source=. --remote=origin --push \
        --description "Unofficial offline PC campaign player for 50 Cent: Bulletproof - G-Unit Edition (PSP, ULUS10128 v1.02): hybrid static recompilation + PPSSPP runtime. No game data included."
fi

echo
echo "Done. Next steps in the GitHub web UI:"
echo "  * Settings > General > Topics: psp static-recompilation ppsspp reverse-engineering emulation"
echo "  * Releases > Draft a new release: attach the player ZIP built by rebuild/package.py and its SHA-256"

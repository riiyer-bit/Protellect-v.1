#!/bin/bash
# Protellect — push all files to GitHub in one command
# Usage: bash push_to_github.sh YOUR_GITHUB_TOKEN YOUR_GITHUB_USERNAME

TOKEN=$1
USER=$2
REPO="Protellect-v.1"
BRANCH="main"
API="https://api.github.com/repos/$USER/$REPO/contents"

if [ -z "$TOKEN" ] || [ -z "$USER" ]; then
  echo "Usage: bash push_to_github.sh GITHUB_TOKEN USERNAME"
  echo "Get a token at: https://github.com/settings/tokens → Generate new token (classic) → check 'repo'"
  exit 1
fi

push_file() {
  local FILE_PATH=$1
  local GITHUB_PATH=$2
  echo "→ Pushing $GITHUB_PATH..."

  # Get current SHA if file exists (needed to update)
  SHA=$(curl -s -H "Authorization: token $TOKEN" "$API/$GITHUB_PATH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null)

  # Encode file as base64
  CONTENT=$(base64 -w 0 "$FILE_PATH")

  # Build JSON payload
  if [ -n "$SHA" ]; then
    PAYLOAD="{\"message\":\"Update $GITHUB_PATH via Protellect deploy script\",\"content\":\"$CONTENT\",\"sha\":\"$SHA\",\"branch\":\"$BRANCH\"}"
  else
    PAYLOAD="{\"message\":\"Add $GITHUB_PATH via Protellect deploy script\",\"content\":\"$CONTENT\",\"branch\":\"$BRANCH\"}"
  fi

  RESULT=$(curl -s -X PUT -H "Authorization: token $TOKEN" -H "Content-Type: application/json" -d "$PAYLOAD" "$API/$GITHUB_PATH")
  
  if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'content' in d else 1)" 2>/dev/null; then
    echo "  ✓ $GITHUB_PATH updated"
  else
    echo "  ✗ Failed: $(echo $RESULT | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("message","unknown error"))' 2>/dev/null)"
  fi
}

echo ""
echo "Protellect → GitHub: $USER/$REPO"
echo "============================================"

# Push all core files
push_file "app.py"              "app.py"
push_file "scorer.py"           "scorer.py"
push_file "hypothesis_lab.py"   "hypothesis_lab.py"
push_file "protein_explorer.py" "protein_explorer.py"
push_file "structure_loader.py" "structure_loader.py"
push_file "requirements.txt"    "requirements.txt"
push_file "sample_data/example.csv" "sample_data/example.csv"

echo ""
echo "============================================"
echo "Done! Streamlit Cloud will redeploy in ~30s"
echo "Check: https://protellect.streamlit.app"

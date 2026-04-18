#!/bin/bash
set -e

# ================= helpers =================
has() { command -v "$1" >/dev/null 2>&1; }

# ---- detect shell RC file ----
if [ -n "$ZSH_VERSION" ] || [[ "$SHELL" == */zsh ]]; then
  RC_FILE="$HOME/.zshrc"
else
  RC_FILE="$HOME/.bashrc"
fi

# ---- ensure ~/.local/bin is in PATH ----
export PATH="$HOME/.local/bin:$PATH"
grep -q '.local/bin' "$RC_FILE" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC_FILE"

# ================= Claude ==================
if ! has claude; then
  curl -fsSL https://claude.ai/install.sh | bash
  echo "✅ Claude installed"
fi

# ================= uv ======================
if ! has uv; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  echo "✅ uv installed"
fi

# ================= paths ===================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ================= cds CLI (global) ========
uv tool install --force --editable "$PROJECT_ROOT/cli"
# CDS_ROOT not needed — config.py auto-detects coding-scripts/ via __file__
# Only set it if explicitly overriding the default location
echo "✅ cds installed globally"

# ================= GitHub CLI ===============
if ! has gh; then
  if [[ "$(uname)" == "Darwin" ]]; then
    brew install gh
  else
    GH_VERSION="2.63.2"
    curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" | \
      sudo tar -xz -C /usr/local --strip-components=1
  fi
  echo "✅ GitHub CLI installed"
fi

# ================= git identity =============
IDENTITY_FILE="$PROJECT_ROOT/private/identity.yml"
if [ -f "$IDENTITY_FILE" ]; then
  GIT_EMAIL=$(grep 'email:' "$IDENTITY_FILE" | cut -d: -f2 | tr -d ' ')
  GIT_NAME=$(grep 'github_owner:' "$IDENTITY_FILE" | cut -d: -f2 | tr -d ' ')
  git config --global user.email "$GIT_EMAIL"
  git config --global user.name "$GIT_NAME"
else
  echo "Note: Set git identity with: git config --global user.email/user.name"
fi

# ================= gh auth ==================
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  echo "Enter your GitHub personal access token:"
  read -s GITHUB_TOKEN
  printf "%s\n" "$GITHUB_TOKEN" | gh auth login \
    --with-token \
    --hostname github.com \
    --git-protocol https
  echo
  echo "✅ GitHub authenticated"
fi

# ================= git credential helper ======
# Use gh CLI as credential helper so git uses gh's stored credentials
git config --global credential.helper '!gh auth git-credential'

# ================= done =====================
echo "🎉 Setup complete"
echo "• cds available everywhere"
echo "• safe to re-run anytime"

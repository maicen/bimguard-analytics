#!/usr/bin/env bash
# =============================================================================
# BIMGUARD AI — GitHub Repository Setup Script
# =============================================================================
# Run this ONCE from inside the bimguard-analytics/ folder.
# It will:
#   1. Check prerequisites (git, gh CLI)
#   2. Authenticate with GitHub if not already logged in
#   3. Initialise local git repo
#   4. Create the private GitHub repo via GitHub CLI
#   5. Make the initial commit
#   6. Create dev, staging branches
#   7. Set branch protection rules on main
#   8. Print next steps
#
# Usage:
#   chmod +x setup_github_repo.sh
#   ./setup_github_repo.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — edit these before running
# ---------------------------------------------------------------------------
REPO_NAME="bimguard-analytics"
REPO_DESCRIPTION="BIMGUARD AI — OpenBIM corrosion compliance analytics. Power BI star schema, BCF issue tracking, GC-001/CC-001 engines."
GITHUB_ORG="maicen"     # Leave blank to create under your personal account.
                        # Set to your org name e.g. "zigurat-group5" to create under an org.
REPO_VISIBILITY="private"   # private | public
DEFAULT_BRANCH="main"

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

step()  { echo -e "\n${CYAN}${BOLD}▶ $1${RESET}"; }
ok()    { echo -e "  ${GREEN}✓ $1${RESET}"; }
warn()  { echo -e "  ${YELLOW}⚠ $1${RESET}"; }
fail()  { echo -e "  ${RED}✗ $1${RESET}"; exit 1; }

# ---------------------------------------------------------------------------
# Step 1 — Prerequisites
# ---------------------------------------------------------------------------
step "Checking prerequisites"

command -v git >/dev/null 2>&1 || fail "git is not installed. Install from https://git-scm.com"
ok "git $(git --version | awk '{print $3}')"

command -v gh >/dev/null 2>&1 || {
    warn "GitHub CLI (gh) not found."
    echo ""
    echo "  Install it first:"
    echo "    macOS:   brew install gh"
    echo "    Windows: winget install GitHub.cli"
    echo "    Linux:   https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
    echo ""
    fail "Please install gh and re-run this script."
}
ok "gh $(gh --version | head -1 | awk '{print $3}')"

# ---------------------------------------------------------------------------
# Step 2 — GitHub authentication
# ---------------------------------------------------------------------------
step "Checking GitHub authentication"

if ! gh auth status >/dev/null 2>&1; then
    warn "Not authenticated with GitHub. Launching login flow..."
    echo ""
    gh auth login --git-protocol https --web
else
    GITHUB_USER=$(gh api user --jq '.login')
    ok "Authenticated as: ${GITHUB_USER}"
fi

GITHUB_USER=$(gh api user --jq '.login')

# ---------------------------------------------------------------------------
# Step 3 — Determine repo owner
# ---------------------------------------------------------------------------
if [[ -n "$GITHUB_ORG" ]]; then
    REPO_OWNER="$GITHUB_ORG"
else
    REPO_OWNER="$GITHUB_USER"
fi
REPO_FULL="${REPO_OWNER}/${REPO_NAME}"

step "Repository will be created as: ${REPO_FULL} (${REPO_VISIBILITY})"

# ---------------------------------------------------------------------------
# Step 4 — Initialise local git
# ---------------------------------------------------------------------------
step "Initialising local git repository"

if [[ -d ".git" ]]; then
    warn ".git already exists — skipping git init"
else
    git init -b "$DEFAULT_BRANCH"
    ok "Initialised git repo with default branch: ${DEFAULT_BRANCH}"
fi

# Configure git identity if not set
if [[ -z "$(git config user.email)" ]]; then
    GH_EMAIL=$(gh api user/emails --jq '.[0].email' 2>/dev/null || echo "")
    GH_NAME=$(gh api user --jq '.name // .login')
    git config user.email "${GH_EMAIL}"
    git config user.name  "${GH_NAME}"
    ok "Git identity set to: ${GH_NAME} <${GH_EMAIL}>"
fi

# ---------------------------------------------------------------------------
# Step 5 — Create GitHub remote repo
# ---------------------------------------------------------------------------
step "Creating GitHub repository: ${REPO_FULL}"

if gh repo view "$REPO_FULL" >/dev/null 2>&1; then
    warn "Repository ${REPO_FULL} already exists — skipping creation"
else
    if [[ -n "$GITHUB_ORG" ]]; then
        gh repo create "$REPO_FULL" \
            --description "$REPO_DESCRIPTION" \
            --"$REPO_VISIBILITY" \
           
    else
        gh repo create "$REPO_NAME" \
            --description "$REPO_DESCRIPTION" \
            --"$REPO_VISIBILITY" \
           
    fi
    ok "Repository created: https://github.com/${REPO_FULL}"
fi

# ---------------------------------------------------------------------------
# Step 6 — Add remote origin
# ---------------------------------------------------------------------------
step "Setting remote origin"

if git remote get-url origin >/dev/null 2>&1; then
    warn "Remote 'origin' already set — verifying URL"
    CURRENT_REMOTE=$(git remote get-url origin)
    ok "origin = ${CURRENT_REMOTE}"
else
    git remote add origin "https://github.com/${REPO_FULL}.git"
    ok "origin = https://github.com/${REPO_FULL}.git"
fi

# ---------------------------------------------------------------------------
# Step 7 — Initial commit and push main
# ---------------------------------------------------------------------------
step "Creating initial commit on main"

git add --all
git commit -m "chore: initial BIMGUARD AI analytics repository structure

- Power BI PBIP project scaffold (SemanticModel + Report)
- Analytics data contract (schema v1.0.0)
- Sample dimension CSVs
- GitHub Actions workflows (validate-model, sync-data)
- Branch protection and PR templates
- docs: dashboard blueprint and data contract specification

BIMGUARD AI — GC-001 / CC-001 corrosion compliance
OpenBIM | IFC ISO 16739-1 | BCF 2.1 | Python + Streamlit
" 2>/dev/null || warn "Nothing new to commit — working tree clean"

git push -u origin "$DEFAULT_BRANCH"
ok "Pushed to origin/${DEFAULT_BRANCH}"

# ---------------------------------------------------------------------------
# Step 8 — Create dev and staging branches
# ---------------------------------------------------------------------------
step "Creating branch structure"

for BRANCH in dev staging; do
    if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
        warn "Branch '${BRANCH}' already exists on remote"
    else
        git checkout -b "$BRANCH"
        git push -u origin "$BRANCH"
        git checkout "$DEFAULT_BRANCH"
        ok "Created and pushed: ${BRANCH}"
    fi
done

# ---------------------------------------------------------------------------
# Step 9 — Branch protection rules
# ---------------------------------------------------------------------------
step "Applying branch protection rules on main"

# Requires GitHub Pro/Team/Enterprise for private repos.
# For free personal private repos, this section will warn but not fail.

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${REPO_FULL}/branches/${DEFAULT_BRANCH}/protection" \
  --input - <<'EOF' 2>/dev/null && ok "Branch protection set on main" || \
  warn "Branch protection requires GitHub Pro/Team — skipping (set manually in Settings > Branches)"
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

# ---------------------------------------------------------------------------
# Step 10 — Set repo topics
# ---------------------------------------------------------------------------
step "Tagging repository with topics"

gh api \
  --method PUT \
  "/repos/${REPO_FULL}/topics" \
  -f "names[]=bim" \
  -f "names[]=ifc" \
  -f "names[]=openBIM" \
  -f "names[]=corrosion" \
  -f "names[]=power-bi" \
  -f "names[]=mep" \
  -f "names[]=streamlit" \
  -f "names[]=compliance" >/dev/null 2>/dev/null && ok "Topics applied" || warn "Could not set topics"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  BIMGUARD AI — Repository Setup Complete               ${RESET}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════${RESET}"
echo ""
echo -e "  Repository : ${CYAN}https://github.com/${REPO_FULL}${RESET}"
echo ""
echo -e "  Branches:"
echo -e "    ${BOLD}main${RESET}     → production (protected)"
echo -e "    ${BOLD}dev${RESET}      → integration (merge feature branches here first)"
echo -e "    ${BOLD}staging${RESET}  → pre-production review"
echo ""
echo -e "  Next steps:"
echo -e "    1. Copy your BIMGUARD AI Python files into bimguard_app/"
echo -e "    2. Copy analytics_export.py into bimguard_app/modules/"
echo -e "    3. Run: git add . && git commit -m 'feat: add compliance engines'"
echo -e "    4. git push origin dev → open PR to main"
echo -e "    5. Open Power BI Desktop → open powerbi/BIMGuardAnalytics.pbip"
echo -e "    6. Set DataFolderPath parameter to your local analytics_export/ folder"
echo ""
echo -e "  To connect Power BI Service to this repo:"
echo -e "    Workspace Settings → Git integration → connect to ${REPO_FULL}"
echo -e "    Branch: main | Folder: /powerbi"
echo ""

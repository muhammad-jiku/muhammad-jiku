#!/usr/bin/env bash
# Refreshes three auto-generated sections of README.md:
#   1. PROJECTS-START/END         - most recently active public, non-fork repos owned by GH_USERNAME
#   2. CONTRIBUTIONS-START/END    - merged/closed PRs authored by GH_USERNAME on repos owned by someone else
#      (evidence of collaborative / client work living outside this account)
#   3. PRIVATE-PROJECTS-START/END - private, non-fork repos owned by GH_USERNAME, listed by name only
#      (no link, no description — just proof-of-work without exposing client code).
#      Requires PRIVATE_REPOS_TOKEN (a token with read access to your private repos); if unset,
#      this section is skipped gracefully.
set -euo pipefail

USERNAME="${GH_USERNAME:-muhammad-jiku}"

AUTH_HEADER=()
if [ -n "${GITHUB_TOKEN:-}" ]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
fi

# --- 1. Latest owned public projects ------------------------------------------
repos_json=$(curl -sf "${AUTH_HEADER[@]}" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/users/${USERNAME}/repos?sort=pushed&direction=desc&per_page=100")

projects_md=$(echo "$repos_json" | jq -r --arg user "$USERNAME" '
  [ .[] | select(.fork == false) | select(.archived == false) | select(.name != $user) ]
  | sort_by(.pushed_at) | reverse | .[0:6]
  | .[]
  | "- **[\(.name)](\(.html_url))**"
    + (if .description and .description != "" then " — \(.description)" else "" end)
    + (if .language and .language != "" then "  ·  `\(.language)`" else "" end)
    + "  ·  updated \(.pushed_at[0:10])"
')

if [ -z "$projects_md" ]; then
  projects_md="_No public projects found yet — check back soon._"
fi

# --- 2. External collaborative / client contributions (PRs on others' repos) --
prs_json=$(curl -sf "${AUTH_HEADER[@]}" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/issues?q=author:${USERNAME}+type:pr&per_page=100" || echo '{"items":[]}')

contributions_md=$(echo "$prs_json" | jq -r --arg user "$USERNAME" '
  [ .items[]
    | select((.repository_url | split("/")[-2]) != $user)
    | { owner: (.repository_url | split("/")[-2]),
        repo: (.repository_url | split("/")[-1]),
        html_url,
        state: (if .pull_request.merged_at then "merged" else .state end) }
  ]
  | group_by(.owner + "/" + .repo)
  | map({
      owner: .[0].owner,
      repo: .[0].repo,
      count: length,
      repo_url: ("https://github.com/" + .[0].owner + "/" + .[0].repo),
      merged: (map(select(.state == "merged")) | length)
    })
  | sort_by(-.count)
  | .[]
  | "- **[\(.owner)/\(.repo)](\(.repo_url))** — \(.count) pull request" + (if .count > 1 then "s" else "" end)
    + (if .merged > 0 then " (\(.merged) merged)" else "" end)
')

if [ -z "$contributions_md" ]; then
  contributions_md="_No external pull requests found via the GitHub API yet._"
fi

# --- 3. Private / client projects (name + language only, no link, no description) --
private_projects_md=""
if [ -n "${PRIVATE_REPOS_TOKEN:-}" ]; then
  private_repos_json=$(curl -sf -H "Authorization: Bearer ${PRIVATE_REPOS_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/user/repos?visibility=private&affiliation=owner&sort=pushed&direction=desc&per_page=100" || echo '[]')

  private_projects_md=$(echo "$private_repos_json" | jq -r --arg user "$USERNAME" '
    [ .[] | select(.fork == false) | select(.archived == false) | select(.name != $user) ]
    | sort_by(.pushed_at) | reverse | .[0:6]
    | .[]
    | "- 🔒 **\(.name)**"
      + (if .language and .language != "" then "  ·  `\(.language)`" else "" end)
      + "  ·  updated \(.pushed_at[0:10])  ·  _private, code not public_"
  ')
fi

if [ -z "$private_projects_md" ]; then
  private_projects_md="_No private-repo token configured yet, or no private projects found._"
fi

python3 - "$projects_md" "$contributions_md" "$private_projects_md" <<'PYEOF'
import re
import sys

projects_md, contributions_md, private_projects_md = sys.argv[1], sys.argv[2], sys.argv[3]

with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

def replace_section(text, start, end, body):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    return pattern.sub(f"{start}\n{body}\n{end}", text, count=1)

content = replace_section(content, "<!-- PROJECTS-START -->", "<!-- PROJECTS-END -->", projects_md)
content = replace_section(content, "<!-- CONTRIBUTIONS-START -->", "<!-- CONTRIBUTIONS-END -->", contributions_md)
content = replace_section(content, "<!-- PRIVATE-PROJECTS-START -->", "<!-- PRIVATE-PROJECTS-END -->", private_projects_md)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(content)
PYEOF

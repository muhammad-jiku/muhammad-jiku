#!/usr/bin/env bash
# Refreshes three auto-generated sections of README.md:
#   1. PROJECTS-START/END         - most recently active public, non-fork repos owned by GH_USERNAME
#   2. CONTRIBUTIONS-START/END    - merged/closed PRs authored by GH_USERNAME on repos owned by someone else,
#      plus (appended below them) owned-but-private repos whose name doesn't start with "jikmunn-" —
#      those read as collaborative/client work rather than personal projects, so they're routed here
#      instead of PRIVATE-PROJECTS-START/END even though the data source is the same API call.
#   3. PRIVATE-PROJECTS-START/END - private, non-fork repos owned by GH_USERNAME whose name starts with
#      "jikmunn-", listed by name only (no link, no description — just proof-of-work without exposing
#      client code).
#      Both 2's owned-private entries and 3 require PRIVATE_REPOS_TOKEN (a token with read access to
#      your private repos); if unset, both are skipped gracefully.
#
# A manually maintained entry for peptides-apps/peptides-platform (an org-owned private repo this
# account collaborates on but doesn't own, and isn't authorized for API/token access to) lives as a
# plain line in README.md just after CONTRIBUTIONS-END, outside these markers — this script never
# touches it.
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

pr_contributions_md=$(echo "$prs_json" | jq -r --arg user "$USERNAME" '
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

# --- 3. Private repos owned by this account (name + language only, no link, no description) --
# Split by name: a "jikmunn-" prefix means personal/own-brand work (-> PRIVATE-PROJECTS section);
# anything else reads as collaborative/client work done under this account (-> appended to
# CONTRIBUTIONS section above, alongside the PR-based entries).
private_projects_md=""
other_private_md=""
if [ -n "${PRIVATE_REPOS_TOKEN:-}" ]; then
  private_repos_json=$(curl -sf -H "Authorization: Bearer ${PRIVATE_REPOS_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/user/repos?visibility=private&affiliation=owner&sort=pushed&direction=desc&per_page=100" || echo '[]')

  private_projects_md=$(echo "$private_repos_json" | jq -r --arg user "$USERNAME" '
    [ .[] | select(.fork == false) | select(.archived == false) | select(.name != $user)
      | select(.name | startswith("jikmunn-")) ]
    | sort_by(.pushed_at) | reverse | .[0:6]
    | .[]
    | "- 🔒 **\(.name)**"
      + (if .language and .language != "" then "  ·  `\(.language)`" else "" end)
      + "  ·  updated \(.pushed_at[0:10])  ·  _private, code not public_"
  ')

  other_private_md=$(echo "$private_repos_json" | jq -r --arg user "$USERNAME" '
    [ .[] | select(.fork == false) | select(.archived == false) | select(.name != $user)
      | select(.name | startswith("jikmunn-") | not) ]
    | sort_by(.pushed_at) | reverse | .[0:6]
    | .[]
    | "- 🔒 **\(.name)**"
      + (if .language and .language != "" then "  ·  `\(.language)`" else "" end)
      + "  ·  updated \(.pushed_at[0:10])  ·  _private, code not public_"
  ')
fi

if [ -z "$private_projects_md" ]; then
  private_projects_md="_No private-repo token configured yet, or no private jikmunn- projects found._"
fi

# Merge PR-based contributions with owned-but-non-jikmunn- private repos, in that order.
contributions_md="${pr_contributions_md}"
if [ -n "$other_private_md" ]; then
  if [ -n "$contributions_md" ]; then
    contributions_md="${contributions_md}
${other_private_md}"
  else
    contributions_md="${other_private_md}"
  fi
fi

if [ -z "$contributions_md" ]; then
  contributions_md="_No external pull requests found via the GitHub API yet._"
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

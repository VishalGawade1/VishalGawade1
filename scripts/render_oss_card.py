#!/usr/bin/env python3
"""Render the "Open Source" bento card SVG from GitHub PR search JSON.

Pure rendering — NO network. Reads the JSON body of
  GET /search/issues?q=type:pr author:VishalGawade1
from a file path (argv[1]) or stdin, and writes the animated card SVG to
assets/open-source.svg.

Classification: a PR is MERGED if pull_request.merged_at is set, OPEN if its
state is "open", otherwise CLOSED (not shown). Most-recent PRs are shown first,
so newly merged work appears automatically. The header counts reflect TRUE
totals across all matched PRs (after the denylist), not just the rows shown.
"""
import sys, os, json, re, html

# ---- design tokens (kept in sync with gen_bento.py) ----
CARD, CARD2, BORDER = "#161b22", "#1c2230", "#272e3a"
T1, T2, T3 = "#e6edf3", "#9aa5b1", "#6e7681"
ACCENT, GREEN, CYAN = "#7c83ff", "#3fb950", "#56d4dd"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,Helvetica,Arial,sans-serif"
EASE = 'calcMode="spline" keyTimes="0;1" keySplines="0.2 0.8 0.2 1"'

W = 488
MERGED_SHOWN = 5      # cap rows; most recent shown first
OPEN_SHOWN = 3

# Repos to ignore entirely (trivial / non-substantive PRs).
DENYLIST = {
    "github-education-resources/GitHubGraduation-2021",
}

# Curated one-line descriptions for known PRs (keeps the card sharp). Anything
# not listed falls back to the auto-tidied PR title. Keyed by "owner/repo".
OVERRIDES = {
    "scrapy/scrapy": "Deprecate ScrapyCommand.help()",
    "google/osv-scanner": "Smarter retry on server-side errors",
    "microsoft/AI-Engineering-Coach": "Context files (skills/, AGENTS.md)",
    "shlokc9/kubernetes-module": "Clearer, comprehensive setup docs",
    "hashicorp/vault": "Agent cache self-healing channels",
    "pandas-dev/pandas": "isocalendar() pyarrow index fix",
    "facebook/sapling": "export --email patch format",
}

PREFIX_RE = re.compile(r"^[A-Za-z]+(\([^)]*\))?!?:\s*")  # strip feat: / fix(x): / BUG: etc.

def esc(s): return html.escape(str(s), quote=True)

def tidy(title, limit=46):
    t = PREFIX_RE.sub("", title).strip()
    t = t[0:1].upper() + t[1:] if t else t
    if len(t) > limit:
        t = t[: limit - 1].rstrip() + "…"
    return t

def repo_of(item):
    return item.get("repository_url", "").split("/repos/")[-1]

def classify(item):
    pr = item.get("pull_request") or {}
    if pr.get("merged_at"):
        return "merged"
    if item.get("state") == "open":
        return "open"
    return "closed"

def load_items():
    raw = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    data = json.loads(raw)
    return data.get("items", data if isinstance(data, list) else [])

def main():
    items = [it for it in load_items() if repo_of(it) not in DENYLIST]
    merged, opened = [], []
    for it in items:
        c = classify(it)
        if c == "merged":
            merged.append(it)
        elif c == "open":
            opened.append(it)
    # most recent first
    merged.sort(key=lambda it: (it.get("pull_request") or {}).get("merged_at") or "", reverse=True)
    opened.sort(key=lambda it: it.get("created_at") or "", reverse=True)

    rows = []
    for it in merged[:MERGED_SHOWN]:
        rows.append((repo_of(it), "merged"))
    for it in opened[:OPEN_SHOWN]:
        rows.append((repo_of(it), "open"))

    desc_by_repo = {}
    for it in items:
        r = repo_of(it)
        if r not in desc_by_repo:
            desc_by_repo[r] = OVERRIDES.get(r) or tidy(it.get("title", ""))

    n = max(len(rows), 1)
    h = 90 + (n - 1) * 45 + 19 + 24            # baseline geometry + bottom padding

    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
         f'viewBox="0 0 {W} {h}" fill="none" role="img">')
    # one-time fade/slide entrance, matching the other cards' stagger
    s += ('<g opacity="0">'
          '<animate attributeName="opacity" from="0" to="1" begin="0.28s" dur="0.75s" fill="freeze"/>'
          f'<animateTransform attributeName="transform" type="translate" from="0 8" to="0 0" begin="0.28s" dur="0.75s" fill="freeze" {EASE}/>')
    s += f'<rect x="0.5" y="0.5" width="{W-1}" height="{h-1}" rx="16" fill="{CARD}" stroke="{BORDER}" stroke-width="1"/>'
    s += f'<text x="30" y="50" font-family="{MONO}" font-size="13" fill="{ACCENT}" letter-spacing="2">OPEN SOURCE</text>'
    s += (f'<text x="{W-30}" y="50" text-anchor="end" font-family="{FONT}" font-size="14" fill="{T3}">'
          f'{len(merged)} merged &#183; {len(opened)} in&#8209;flight</text>')

    y = 90
    for repo, st in rows:
        col, label = (GREEN, "merged") if st == "merged" else (CYAN, "open")
        s += f'<text x="30" y="{y}" font-family="{MONO}" font-size="15.5" font-weight="600" fill="{T1}">{esc(repo)}</text>'
        pill_w = 62 if st == "merged" else 50
        s += f'<rect x="{W-30-pill_w}" y="{y-15}" width="{pill_w}" height="20" rx="10" fill="{col}" fill-opacity="0.15" stroke="{col}" stroke-opacity="0.5"/>'
        s += f'<text x="{W-30-pill_w/2}" y="{y}" text-anchor="middle" font-family="{MONO}" font-size="11.5" fill="{col}">{label}</text>'
        s += f'<text x="30" y="{y+19}" font-family="{FONT}" font-size="13.5" fill="{T3}">{esc(desc_by_repo.get(repo, ""))}</text>'
        y += 45

    s += '</g></svg>'

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "open-source.svg")
    with open(out, "w") as f:
        f.write(s)
    print(f"wrote {out} :: {len(merged)} merged, {len(opened)} open, {len(rows)} rows, h={h}", file=sys.stderr)

if __name__ == "__main__":
    main()

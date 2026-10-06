#!/usr/bin/env python3
"""Add one episode to the site, or re-render scripts. Standard library only.

Add an episode (run from the repository root):
  python3 tools/add_episode.py --entry entry.json --mp3 ep.mp3 --script script.md

entry.json:
  {"date": "YYYY-MM-DD", "published_at": "YYYY-MM-DD_HHMM",
   "window_start": "YYYY-MM-DD", "window_end": "YYYY-MM-DD",
   "title": "...", "duration": "m:ss",
   "sections": [{"area": "...", "items": [{"name": "...", "date": "YYYY-MM-DD", "url": "https://..."}]}]}

script.md: paragraphs separated by blank lines, "## Heading" lines for segments,
"- [Title](https://url)" lines for sources, inline [text](url) links allowed.

Render a script page only:
  python3 tools/add_episode.py --render-script STAMP script.md "Title" YYYY-MM-DD
"""
import argparse, datetime, html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP_AUDIO_DAYS = 31
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{4}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · The Ten-Day Diff</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#f5f6f3;--fg:#1d2320;--muted:#5d6862;--line:#dde2dd;--accent:#1f6f5c;
--display:"Fraunces",Georgia,serif;--body:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121614;--fg:#e4e9e5;--muted:#9aa6a0;--line:#2b3430;--accent:#5cc2a4;color-scheme:dark}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 var(--body);padding:32px 16px 64px}}
main{{max-width:660px;margin:0 auto}}
.label{{font:500 11px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
h1{{font:600 clamp(26px,6vw,36px)/1.15 var(--display);margin:8px 0 6px;text-wrap:balance}}
.meta{{font:400 13px/1.4 var(--mono);color:var(--muted);margin:0 0 28px}}
h2{{font:600 21px/1.3 var(--display);margin:36px 0 8px;padding-top:20px;border-top:1px solid var(--line)}}
p{{margin:0 0 16px}}
ul{{padding-left:20px}} li{{margin:4px 0;font-size:15px}}
a{{color:var(--accent);text-underline-offset:3px}}
.back{{font:500 13px var(--body);text-decoration:none}}
</style>
</head>
<body>
<main>
<a class="back" href="../">← All episodes</a>
<p class="label" style="margin-top:24px">The Ten-Day Diff · script</p>
<h1>{title}</h1>
<p class="meta">{meta}</p>
{body}
</main>
</body>
</html>
"""


def nice(d):
    y, m, dd = (int(x) for x in d.split("-"))
    return "%s %d" % (MON[m - 1], dd)


def inline(text):
    out, pos = [], 0
    for m in re.finditer(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", text):
        out.append(html.escape(text[pos:m.start()]))
        out.append('<a href="%s">%s</a>' % (html.escape(m.group(2), quote=True), html.escape(m.group(1))))
        pos = m.end()
    out.append(html.escape(text[pos:]))
    s = "".join(out)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)


def md_to_html(md):
    blocks, para, items = [], [], []

    def flush():
        nonlocal para, items
        if para:
            blocks.append("<p>%s</p>" % inline(" ".join(para)))
            para = []
        if items:
            blocks.append("<ul>\n%s\n</ul>" % "\n".join("<li>%s</li>" % inline(i) for i in items))
            items = []

    for raw in md.splitlines():
        line = raw.strip()
        if not line or line in ("---", "##"):
            flush()
        elif line.startswith("# ") and not blocks and not para:
            continue  # the page prints its own title
        elif line.startswith("#"):
            flush()
            blocks.append("<h2>%s</h2>" % inline(line.lstrip("#").strip()))
        elif line.startswith(("- ", "* ")):
            if para:
                flush()
            items.append(line[2:].strip())
        else:
            if items:
                flush()
            para.append(line)
    flush()
    return "\n".join(blocks)


def render_script(stamp, md_path, title, date, window=""):
    with open(md_path, encoding="utf-8") as f:
        body = md_to_html(f.read())
    y, m, d = (int(x) for x in date.split("-"))
    meta = "%s %d, %d" % (MON[m - 1], d, y) + (" · covers " + window if window else "")
    os.makedirs(os.path.join(ROOT, "scripts"), exist_ok=True)
    rel = "scripts/%s.html" % stamp
    with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as f:
        f.write(PAGE.format(title=html.escape(title), meta=html.escape(meta), body=body))
    return rel


def fail(msg):
    sys.exit("add_episode: " + msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry")
    ap.add_argument("--mp3")
    ap.add_argument("--script")
    ap.add_argument("--render-script", nargs=4, metavar=("STAMP", "MD", "TITLE", "DATE"))
    a = ap.parse_args()

    if a.render_script:
        print(render_script(*a.render_script))
        return
    if not (a.entry and a.mp3 and a.script):
        fail("need --entry, --mp3 and --script")

    with open(a.entry, encoding="utf-8") as f:
        e = json.load(f)
    stamp = e.get("published_at", "")
    if not STAMP_RE.match(stamp):
        fail("published_at must look like 2026-10-06_0559")
    for k in ("date", "window_start", "window_end"):
        if not DATE_RE.match(str(e.get(k, ""))):
            fail("%s must be YYYY-MM-DD" % k)
    if not e.get("title") or not re.match(r"^\d+:\d\d$", str(e.get("duration", ""))):
        fail("title and duration (m:ss) are required")
    if not e.get("sections"):
        fail("sections are required")
    for s in e["sections"]:
        if not s.get("area"):
            fail("every section needs an area")
        for i in s.get("items", []):
            if not i.get("name") or not DATE_RE.match(str(i.get("date", ""))) or not str(i.get("url", "")).startswith("http"):
                fail("item needs name, date YYYY-MM-DD and url: %r" % i)
    if os.path.getsize(a.mp3) < 100000:
        fail("mp3 looks too small")

    path = os.path.join(ROOT, "episodes.json")
    with open(path, encoding="utf-8") as f:
        eps = json.load(f)
    if any(x.get("published_at") == stamp for x in eps):
        fail("an episode with published_at %s already exists" % stamp)
    before = len(eps)

    window = "%s to %s" % (nice(e["window_start"]), nice(e["window_end"]))
    os.makedirs(os.path.join(ROOT, "episodes"), exist_ok=True)
    shutil.copyfile(a.mp3, os.path.join(ROOT, "episodes", stamp + ".mp3"))
    script_url = render_script(stamp, a.script, e["title"], e["date"], window)
    eps.append({
        "date": e["date"], "published_at": stamp, "window": window,
        "title": e["title"], "duration": e["duration"],
        "audio_url": "episodes/%s.mp3" % stamp, "script_url": script_url,
        "sections": [{"area": s["area"], "items": [{"name": i["name"], "date": i["date"], "url": i["url"]} for i in s.get("items", [])]} for s in e["sections"]],
    })

    # Drop audio older than KEEP_AUDIO_DAYS; the topic list and script stay.
    today = datetime.date.fromisoformat(e["date"])
    removed = []
    for x in eps:
        old = (today - datetime.date.fromisoformat(x["date"])).days > KEEP_AUDIO_DAYS
        if old and x.get("audio_url"):
            p = os.path.join(ROOT, x["audio_url"])
            if os.path.exists(p):
                os.remove(p)
            removed.append(x["audio_url"])
            x["audio_url"] = ""

    assert len(eps) == before + 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(eps, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("added %s (%d episodes); script %s; audio removed: %s" % (stamp, len(eps), script_url, removed or "none"))


if __name__ == "__main__":
    main()

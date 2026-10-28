"""Translate Markdown blog posts into Arabic with Claude, without breaking the page.

Code blocks, inline code, links, images, HTML tags and glossary terms are swapped for
placeholders before translation and restored afterwards; the result is checked before saving.

Usage:
  python localize.py examples/post.md                # writes examples/post.ar.md
  python localize.py posts/*.md --glossary glossary.txt --model claude-haiku-4-5
"""
import argparse
import os
import re
import sys

PROTECT = [
    re.compile(r"```.*?```", re.S),              # fenced code
    re.compile(r"`[^`\n]+`"),                     # inline code
    re.compile(r"!?\[[^\]]*\]\([^)]+\)"),        # images and links (translated separately below)
    re.compile(r"<[^>\n]+>"),                     # html tags
    re.compile(r"https?://\S+"),                  # bare urls
]
LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)]+)\)")
FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TRANSLATE_KEYS = ("title", "description", "excerpt")

SYSTEM = (
    "You translate gaming and esports blog content from English into natural Modern Standard Arabic "
    "for readers in the Gulf and MENA. Keep tokens like ⟦0⟧ exactly as they are and in the same order. "
    "Keep Markdown symbols (#, -, *, >, |) and line breaks. Keep game names, ranks, maps and brand names "
    "in Latin script. Output only the translation."
)


def protect(text, glossary):
    """Replace untouchable spans with ⟦n⟧ tokens. Link text is kept translatable."""
    store = []

    def keep(s):
        store.append(s)
        return f"⟦{len(store) - 1}⟧"

    def link(m):
        bang, label, url = m.groups()
        return f"{keep(bang + '[')}{label}{keep('](' + url + ')')}" if label and not bang else keep(m.group(0))

    text = LINK.sub(link, text)
    for rx in [PROTECT[0], PROTECT[1], PROTECT[3], PROTECT[4]]:
        text = rx.sub(lambda m: keep(m.group(0)), text)
    for term in sorted(glossary, key=len, reverse=True):
        text = re.sub(rf"(?<![\w⟦]){re.escape(term)}(?![\w⟧])", lambda m: keep(m.group(0)), text)
    return text, store


def restore(text, store):
    return re.sub(r"⟦(\d+)⟧", lambda m: store[int(m.group(1))], text)


def check(src_tokens, out):
    problems = []
    found = re.findall(r"⟦\d+⟧", out)
    if sorted(found) != sorted(src_tokens):
        problems.append(f"placeholders changed ({len(src_tokens)} expected, {len(found)} found)")
    letters = re.findall(r"[^\W\d_]", re.sub(r"⟦\d+⟧", "", out))
    arabic = sum(1 for c in letters if "؀" <= c <= "ۿ")
    if letters and arabic / len(letters) < 0.6:
        problems.append(f"only {arabic * 100 // len(letters)}% Arabic letters")
    return problems


def chunks(body, size=3500):
    """Split on blank lines so paragraphs and tables stay whole."""
    out, cur = [], ""
    for block in re.split(r"(\n\s*\n)", body):
        if len(cur) + len(block) > size and cur.strip():
            out.append(cur)
            cur = ""
        cur += block
    return out + ([cur] if cur.strip() else [])


def translate(client, model, text):
    msg = client.messages.create(model=model, max_tokens=8000, system=SYSTEM,
                                 messages=[{"role": "user", "content": text}])
    return "".join(b.text for b in msg.content if b.type == "text")


def localize(md, client, model, glossary):
    front, body = "", md
    m = FRONT.match(md)
    if m:
        lines = []
        for line in m.group(1).splitlines():
            key, _, val = line.partition(":")
            if key.strip() in TRANSLATE_KEYS and val.strip():
                q = val.strip().strip('"')
                line = f'{key}: "{translate(client, model, q).strip()}"'
            lines.append(line)
        lines.append('lang: ar\ndir: rtl')
        front, body = "---\n" + "\n".join(lines) + "\n---\n", md[m.end():]

    out = []
    for part in chunks(body):
        safe, store = protect(part, glossary)
        tokens = re.findall(r"⟦\d+⟧", safe)
        result = translate(client, model, safe)
        problems = check(tokens, result)
        if problems:  # one retry with the problems spelled out
            result = translate(client, model, f"{safe}\n\n(Previous attempt failed: {'; '.join(problems)}.)")
            problems = check(tokens, result)
        if problems:
            raise ValueError("; ".join(problems))
        out.append(restore(result, store))
    return front + "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--glossary", help="one term per line to keep untranslated")
    ap.add_argument("--model", default=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5"))
    a = ap.parse_args()
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY (see .env.example).")
    import anthropic
    client = anthropic.Anthropic()
    glossary = [l.strip() for l in open(a.glossary, encoding="utf-8") if l.strip()] if a.glossary else []
    for path in a.files:
        target = re.sub(r"\.md$", ".ar.md", path)
        try:
            with open(path, encoding="utf-8") as f:
                result = localize(f.read(), client, a.model, glossary)
            with open(target, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"OK    {path} -> {target}")
        except Exception as e:  # keep going with the other posts
            print(f"FAIL  {path}: {e}")


if __name__ == "__main__":
    main()

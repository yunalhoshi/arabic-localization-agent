import re
from localize import protect, restore, check, chunks, localize

def test_protect_roundtrip():
    src = "Use `code` and [patch notes](https://x.com/a) in VALORANT <br> https://example.com"
    safe, store = protect(src, ["VALORANT"])
    assert "patch notes" in safe and "`code`" not in safe and "VALORANT" not in safe
    assert restore(safe, store) == src

def test_check_flags_missing_tokens_and_english():
    assert check(["⟦0⟧"], "hello there ⟦0⟧")[0].startswith("only")
    assert "placeholders" in check(["⟦0⟧", "⟦1⟧"], "مرحبا ⟦0⟧")[0]
    assert check(["⟦0⟧"], "مرحبا بكم ⟦0⟧") == []

def test_chunks_keep_paragraphs():
    body = "\n\n".join(["a" * 100] * 50)
    assert all(len(c) <= 3700 for c in chunks(body))
    assert "".join(chunks(body)) == body

class Fake:
    """Pretends to translate: replaces each English word with an Arabic word, keeps tokens."""
    class messages:
        @staticmethod
        def create(model, max_tokens, system, messages):
            text = re.sub(r"(?<!⟦)\b[A-Za-z]+\b(?!⟧)", "كلمة", messages[0]["content"])
            return type("M", (), {"content": [type("B", (), {"type": "text", "text": text})()]})()

def test_localize_end_to_end_with_fake_model():
    md = open("examples/post.md", encoding="utf-8").read()
    out = localize(md, Fake(), "fake", ["VALORANT", "Gold", "VOD"])
    assert "dir: rtl" in out and "slug: gold-to-platinum" in out
    assert "(https://playvalorant.com/news)" in out and "`crosshair code`" in out
    assert "![rank chart](images/ranks.png)" in out and "**Gold**" in out

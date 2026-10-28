# Arabic Localization Agent

Translates Markdown blog posts from English into **Modern Standard Arabic** with Claude, and makes sure the page still works afterwards: code, links, images, HTML and brand or game terms come back exactly as they were.

> **About this repository:** the original agent was built for a company blog's Arabic launch and is not published. This is a short, standalone rewrite of the core idea.

## How it works

1. **Front matter:** only `title`, `description` and `excerpt` are translated; `slug` and other keys are kept; `lang: ar` and `dir: rtl` are added.
2. **Protection:** fenced code, inline code, URLs, HTML tags, link targets, images and glossary terms (game names, ranks, maps, brands) are replaced with `⟦n⟧` tokens. Link *text* stays translatable.
3. **Chunking:** the body is split on blank lines so paragraphs and tables are never cut in half.
4. **Translation:** each chunk goes to Claude with a system prompt for natural MSA aimed at Gulf and MENA gamers.
5. **Validation:** every token must come back once, and at least 60% of the letters must be Arabic. On failure it retries once with the problem spelled out, then reports the file as failed instead of saving a broken page.
6. **Batch mode:** many files in one run; one failure does not stop the rest.

## Run

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python localize.py examples/post.md --glossary examples/glossary.txt   # writes examples/post.ar.md
python -m pytest -q        # offline tests, including an end-to-end run with a fake model
```

## Tech stack

Python 3 · Claude API · pytest

---

© 2026 yunalhoshi. All rights reserved. See [NOTICE](NOTICE).

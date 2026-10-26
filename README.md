# 15-122 Study Buddy

## What it does and why I chose it
This is a study tool for 15-122 that finds relevant lecture notes, uses them to explain things I’m confused about, and tracks topics I need to practice. I chose it because I’m taking 122 and wanted to build something I would actually use.

## What’s stored
The database contains 1,115 chunks from the 26 public lecture PDFs at cs.cmu.edu/~15122, plus any personal notes I add. Each chunk contains about 180 words from one page with 40 words of overlap, keeping passages short enough for the embedding model’s roughly 256-word-piece limit. Each item includes its lecture, title, page, and source type (lecture or my_note).

## How to add and search
Choose menu option 2 and paste a note to make it searchable right away. Choose option 1 to ask a question in plain English and search the notes. Option 3 creates a study plan based on the questions you’ve asked.

## My two test queries
“why is adding to the end of my growable list cheap on average if it sometimes has to copy everything” retrieved lecture 11-uba, page 10, about amortized analysis, with a reported distance of 1.28. “how can I look up a student's grade by their name instantly instead of scanning everyone” retrieved lecture 12-hashing, page 2, with reported distances of 1.25–1.29 across runs. Keyword search could miss these relevant passages because the questions don’t contain the terms “amortized,” “unbounded array,” “hash,” or “table.”

## How I used AI
I used Claude Code to help find the data source, write and test the code, and choose the retrieval distance cutoff. The app also uses Claude to generate explanations and study plans.

---

## Setup and running (AI-generated documentation)

**Requirements:** Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python download_notes.py   # downloads 26 lecture PDFs (~10 MB) into data/lectures/
python ingest.py           # chunks and embeds them into ./chroma_store (~30 s)
python app.py
```

**Optional LLM:** to get Claude's explanations and study plans, create a `.env` file containing
`ANTHROPIC_API_KEY=sk-ant-...`. `.env` is git-ignored. Without a key, the app still searches,
shows the best-matching passage, and lists the lectures to reread. Set `TUTOR_MODEL` to change
the model (default `claude-sonnet-5-5`).

**Data source:** public lecture notes from https://www.cs.cmu.edu/~15122/ (`handouts/lectures/*.pdf`).
The raw PDFs and the Chroma store are not committed. Both are rebuilt by the two commands above.

**Vector DB and embeddings:** ChromaDB 1.5.9 with `PersistentClient` and its default embedding
model, `all-MiniLM-L6-v2` (ONNX). The model (~80 MB) downloads automatically on first use to
`~/.cache/chroma/`.

**Files**
- `download_notes.py`: fetches the lecture PDFs
- `ingest.py`: PDF → page text → 180-word overlapping chunks → `upsert` in batches of 100
- `store.py`: the persistent client and the two collections (`notes_122` for lecture chunks and
  your notes, `struggles` for every question you ask)
- `app.py`: the CLI menu

**Menu**
1. **Ask:** semantic search over the lecture notes and your notes. Rejects off-topic questions
   (best distance > 1.45, a cutoff picked from observed distances), logs the question, and Claude
   explains it from the retrieved excerpts with `[lecture pN]` citations. You can keep asking
   follow-ups on the same topic (Claude remembers the conversation) until you type `exit`.
2. **Add a note:** stored immediately and searchable on the next question. Warns if it's a
   near-duplicate of a note you already have.
3. **What should I study?:** groups your logged questions by lecture, shows a count per lecture,
   and Claude writes a prioritized study plan.
4. **Show what's stored:** counts and your notes.

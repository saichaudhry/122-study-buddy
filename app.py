"""15-122 study buddy: ask questions about the lecture notes, add your own notes,
and get a study plan built from what you've been struggling with."""
import os
import uuid
from collections import Counter
from datetime import datetime

from dotenv import load_dotenv

from store import get_collection, get_struggles

load_dotenv()

MODEL = os.environ.get("TUTOR_MODEL", "claude-sonnet-5-5")
N_RESULTS = 5
# From looking at real distances: on-topic questions land around 1.0-1.35,
# nonsense like "best pizza in pittsburgh" lands around 1.55+.
NO_MATCH_DISTANCE = 1.45

TUTOR_SYSTEM = """You are a patient tutor for CMU 15-122 (Principles of Imperative Computation).
Answer the student's question using ONLY the course excerpts provided. Teach, don't just define:
start with the intuition, then the precise idea, then a tiny example in C0 if it helps.
Cite excerpts inline like [11-uba p10]. If the excerpts don't cover something, say so.
Finish with one short check-your-understanding question. Keep it under 300 words."""

PLAN_SYSTEM = """You are a study coach for CMU 15-122. You'll get a student's recent questions,
grouped by the lecture each one matched. Spot the patterns in what they're confused about
(including connections between topics), then give a short, prioritized study plan:
which lectures to reread first and why, and one concrete practice task per topic.
Be specific and brief (under 250 words)."""


def llm():
    """Return an Anthropic client, or None if no key is configured."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic
    return anthropic.Anthropic()


def ask_claude(system, user_text, history=None):
    """Send one message, optionally continuing an earlier conversation (list of messages)."""
    client = llm()
    if client is None:
        return None
    print("\nAsking Claude (this takes a few seconds)...", flush=True)
    messages = (history or []) + [{"role": "user", "content": user_text}]
    resp = client.messages.create(
        model=MODEL, max_tokens=4096, system=system, messages=messages,
    )
    # The response can start with thinking blocks; keep only the text the model wrote for the user.
    return "".join(block.text for block in resp.content if block.type == "text")


def cite(meta):
    if meta["source"] == "lecture":
        return f"{meta['lecture']} p{meta['page']}"
    return f"my note {meta['added'][:10]}"


def search(question):
    """Return [(distance, metadata, document), ...] closest first."""
    r = get_collection().query(query_texts=[question], n_results=N_RESULTS)
    # Chroma returns lists of lists: one inner list per query text.
    return list(zip(r["distances"][0], r["metadatas"][0], r["documents"][0]))


def ask():
    topic = input("\nWhat are you stuck on? ").strip()
    if not topic:
        return
    history = []  # the conversation with Claude so far, so follow-ups have context
    question = topic
    while True:
        # Search on the original topic plus the follow-up, so short follow-ups like
        # "can you show an example?" still pull material about the same topic.
        query = question if question == topic else f"{topic} {question}"
        hits = search(query)
        if hits[0][0] > NO_MATCH_DISTANCE:
            print(f"\nNothing in the notes looks related (closest distance {hits[0][0]:.2f}). "
                  "Try rephrasing, or add a note about it first.")
            if not history:
                return
        else:
            hits = [h for h in hits if h[0] <= NO_MATCH_DISTANCE]  # drop weak matches from the context
            log_struggle(question, hits)

            print("\nMost relevant material:")
            for dist, meta, _ in hits:
                print(f"  [{cite(meta)}] {meta.get('title', '')}  (distance {dist:.2f})")

            excerpts = "\n\n".join(f"[{cite(m)}] {doc}" for _, m, doc in hits)
            prompt = f"Course excerpts:\n{excerpts}\n\nStudent question: {question}"
            answer = ask_claude(TUTOR_SYSTEM, prompt, history)
            if answer is None:
                print("\n(No ANTHROPIC_API_KEY set, so here is the best-matching passage instead.)\n")
                print(hits[0][2])
            else:
                print("\n" + answer)
                history += [{"role": "user", "content": prompt},
                            {"role": "assistant", "content": answer}]

        question = input("\nFollow-up question (or type 'exit' for the menu): ").strip()
        if not question or question.lower() in ("exit", "quit", "q"):
            return


def log_struggle(question, hits):
    """Remember what the user asked so the study plan can find patterns later."""
    lectures = [m["lecture"] for _, m, _ in hits if m["source"] == "lecture"]
    get_struggles().add(
        ids=[str(uuid.uuid4())],
        documents=[question],
        metadatas=[{"asked": datetime.now().isoformat(timespec="seconds"),
                    "lecture": lectures[0] if lectures else "my-notes"}],
    )


def add_note():
    print("\nPaste your note (finish with an empty line):")
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    text = " ".join(lines).strip()
    if not text:
        return
    # Warn if this note is nearly identical to one already stored.
    existing = get_collection().query(query_texts=[text], n_results=1, where={"source": "my_note"})
    if existing["distances"][0] and existing["distances"][0][0] < 0.3:
        print(f"Heads up, this looks like a note you already have: \"{existing['documents'][0][0][:80]}...\"")
        if input("Add it anyway? (y/n) ").strip().lower() != "y":
            return
    get_collection().add(
        ids=[f"note-{uuid.uuid4()}"],  # unique ids, since add() silently ignores reused ones
        documents=[text],
        metadatas=[{"source": "my_note", "title": "My note",
                    "added": datetime.now().isoformat(timespec="seconds")}],
    )
    print("Saved. It's searchable right away.")


def study_plan():
    data = get_struggles().get()
    if not data["ids"]:
        print("\nNo questions yet. Ask a few first, then come back for a plan.")
        return
    by_lecture = {}
    for q, m in zip(data["documents"], data["metadatas"]):
        by_lecture.setdefault(m["lecture"], []).append(q)
    counts = Counter({lec: len(qs) for lec, qs in by_lecture.items()})

    print("\nWhere your questions have been landing:")
    for lec, n in counts.most_common():
        print(f"  {lec:<16} {'#' * n} ({n})")

    summary = "\n".join(f"{lec}:\n" + "\n".join(f"  - {q}" for q in by_lecture[lec])
                        for lec, _ in counts.most_common())
    plan = ask_claude(PLAN_SYSTEM, summary)
    if plan is None:
        print("\n(No ANTHROPIC_API_KEY set.) Reread these first: "
              + ", ".join(lec for lec, _ in counts.most_common(3)))
    else:
        print("\n" + plan)


def show_stats():
    col = get_collection()
    notes = col.get(where={"source": "my_note"})
    print(f"\n{col.count()} items stored ({len(notes['ids'])} of them are your notes).")
    print(f"{get_struggles().count()} questions logged.")
    for doc, meta in zip(notes["documents"], notes["metadatas"]):
        print(f"  [{meta['added'][:10]}] {doc[:90]}")


def main():
    if get_collection().count() == 0:
        print("The database is empty. Run: python download_notes.py && python ingest.py")
        return
    actions = {"1": ask, "2": add_note, "3": study_plan, "4": show_stats}
    while True:
        print("\n--- 15-122 Study Buddy ---\n"
              "1. Ask about something I'm stuck on\n"
              "2. Add my own note\n"
              "3. What should I study? (plan from my questions)\n"
              "4. Show what's stored\n"
              "5. Quit")
        choice = input("Choose an option: ").strip()
        if choice == "5":
            break
        if choice in actions:
            actions[choice]()
            if choice != "1":  # ask() has its own follow-up loop and exits on 'exit'
                # Keep the result on screen until the user is done reading it.
                input("\nPress Enter to return to the menu...")


if __name__ == "__main__":
    main()

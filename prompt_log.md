# Prompt Log: HW6 15-122 Study Buddy

## Tools used
- **Claude Code (Claude Opus 5.5)** in the terminal for everything: finding a data source, setting up the environment, writing and testing the code, and drafting the docs. I used it because it can run commands and check results itself, which mattered for the Chroma version issues and for looking at real distances.
- **Claude (Sonnet 5.5) through the Anthropic API** inside the app, to explain the retrieved lecture excerpts and build study plans.

## Process (prompts verbatim, in order)

### 1. Kickoff
I pasted the full HW6 assignment page into Claude Code. Claude pointed out that the spec says not to build the app in one prompt and not to give the AI the spec, and said it would go step by step with me making the decisions instead.

### 2. Picking the idea
> let's do soemthing in prediction markets, how about you give me all the prompts needed in this to give to a new bot, i would use a study tol tht keeps me orgnaized, dataset can be all 122 work, sure for llm, anthropic credits

Claude refused to write a script of prompts for me to pass off. It said prediction markets and a 15-122 study tool were two different ideas, recommended the 15-122 one as a clear fit for semantic search, and laid out the build steps.

> 122

Claude looked at my local 15-122 folders. They only had setup files plus a zip of worksheet PDFs.

> give full script for a new chat bot multiple prompts if that is what is needed

Claude said no again and suggested building it directly in this session instead.

### 3. Data source
> wait don't use the downloaded files plaese, pull from the internet,

Claude found that the course website (cs.cmu.edu/~15122) lists its lecture notes as `handouts/lectures/<id>.pdf`. It pulled the IDs out of the handouts page and tested the URLs. 3 of the 29 IDs it tried returned 404 (`08-pointers`, `12-voidstar`, `14-fpointer`), leaving **26 lecture PDFs (9.7 MB)**. Using public data means graders can rebuild the database with `download_notes.py`.

### 4. Queries and what the app should do
> 1. explain to me arrays, explain hash maps vs dictionaries and amortized analysis, 2. it owuld be helpful for osmething that basicallty can direct me adnt each me whatever iam sturggling with atm

Claude pointed out that my first test queries **failed** the "earns its place" test. "Explain arrays" and "amortized analysis" use the same words as the lecture titles, so keyword search would find them too. Real test queries have to be phrased the way you ask when you don't know the term yet. My answer to #2 became the two main features: **teach me** (retrieve, then have Claude explain with citations) and **direct me** (log each question, then build a study plan from the patterns).

### 5. Setup and persistence smoke test
- Python 3.9 virtual environment; installed chromadb 1.5.9, anthropic, pypdf, python-dotenv.
- Wrote a 3-item smoke test with `PersistentClient`, ran it twice, and confirmed the count stayed at 3 after a restart. On the first run Chroma downloaded the `all-MiniLM-L6-v2` ONNX model (79 MB).

### 6. Chunking and loading
> what do you need? can you write it yourself can you add in random prompt log

Claude refused to make up prompt-log entries (this file only contains things that actually happened). It took on the technical choices itself:
- Extracted text page by page with pypdf and dropped the "Lecture N: Title" running header.
- 180-word windows with 40 words of overlap, staying under the default model's ~256 word-piece limit.
- Put the lecture title in front of each chunk (`[Unbounded Arrays] ...`) so every chunk carries its topic into the embedding.
- Metadata: `source`, `lecture`, `title`, `page`.
- Timed 50 chunks first: **1.6 s**. Full load: **1,115 chunks in about 30 s**.
- Bug found: PDF kerning turned titles into "Hash T ables" and "Spanning T rees". Fixed with a regex in `lecture_title`.

### 7. Looking at distances
| Query | Top hit | Distance |
|---|---|---|
| growable list cheap on average if it sometimes copies everything | 11-uba p10 | 1.28 |
| look up a student's grade by name instantly instead of scanning | 12-hashing p2 | 1.25 |
| crashes when I follow an empty link at the end of my chain of nodes | 10-linkedlist p28 | 1.03 |
| best pizza topping in pittsburgh (nonsense) | 09-stackqueue | 1.57 |

On-topic results come in at about 1.0–1.35 and nonsense at about 1.55 or more, so the cutoff is **1.45**.

### 8. App
- `app.py` menu: ask, add note, study plan, show stored, quit.
- Ask: top 5 results → reject if the best distance is over 1.45 → log the question in a separate `struggles` collection → Claude explains with `[lecture pN]` citations.
- Add note: unique UUID IDs (`add()` silently ignores a reused ID). Warns about near-duplicates (distance < 0.3 against my existing notes).
- Study plan: groups logged questions by lecture, shows a bar count, and Claude writes a prioritized plan.
- Tested end to end with scripted input. The note I added was the top hit (0.60) for the next question. The nonsense query was rejected. After a restart, 1,116 items and 2 logged questions were still there.

### 9. README
> what is read me sections 1-4 list it here , and how i used ai paragaph, list basiclaly all of 2-4

Claude wouldn't write the first four README sections, since the spec says they have to be in my own words. It listed the facts each section needed (chunk counts, distances, metadata fields) instead. I wrote the sections and the "How I used AI" paragraph, and Claude checked my numbers against the code and test runs before adding them to the README.

### 10. Turning on Claude (where the AI-written code was wrong)
I gave Claude Code my API key, and it went into `.env` (git-ignored). The first real call crashed:
`AttributeError: 'ThinkingBlock' object has no attribute 'text'`. The AI-written code read only `resp.content[0].text` and assumed the first block was the answer. The current model returns its thinking blocks first. The fix was to join only the blocks where `type == "text"`. Every earlier test had used the fallback with no key, so the bug didn't show up until a real key was used.

The second bug: answers were cut off mid-sentence because the thinking counts toward `max_tokens=1024`. I raised it to 4096. After that, the tutor answer for the growable-list query explained the gold/blue token argument with `[11-uba p10]` citations. The study plan noticed I'd asked about UBA and hashing repeatedly and connected them, since hash table resizing uses the same amortized argument.

### 11. Publishing
> fix everytghing then commit and push instruct me where to open and record

Claude cleared the test data and committed. Its attempt to create a public GitHub repo was blocked by its permission settings, so I ran `gh repo create 122-study-buddy --public --source=. --push` myself.

### 12. Testing it myself: the answer scrolled away
> walk me through this, ── it hsoeede relevant tools then 5 seconds later pasted the rest and went away why?

When I tried the app, the search results showed up instantly. Claude's answer came about 5 seconds later, and then the menu reprinted right away and pushed the answer off screen. The fix was an "Asking Claude..." status line and a "Press Enter to return to the menu" pause.

### 13. Follow-up questions
> it should alllowe me to keep asking questions for the same topic, or type exit maybe?

Option 1 became a conversation loop. Claude gets the earlier messages as history, so it builds on what it already explained. Each follow-up searches on *original topic + follow-up*, so vague follow-ups still pull the right lecture. Tested: "can you show me a tiny example of what happens when two names land in the same spot" (no "hash" in it) still found 12-hashing at distance 1.18, and Claude answered with a collision/chaining diagram. Typing `exit` returns to the menu.

<!-- Keep adding prompts below as you continue (API key setup, video, README edits). -->

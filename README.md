# The Unofficial Guide — Project 1

---

## Setup & Running the App

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A free [Groq API key](https://console.groq.com) (no credit card required)

### 1. Install dependencies

```bash
uv pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
```

Open `.env` and replace `your_key_here` with your Groq API key:

```
GROQ_API_KEY=gsk_...
```

### 3. Build the vector index

This embeds all documents in `documents/` and stores them in `chroma_db/`. Run once, and re-run whenever you add or change documents.

```bash
uv run embed.py
```

### 4. Launch the web UI

```bash
uv run app.py
```

Then open **http://localhost:7860** in your browser.

### Running the CLI test instead

To test grounded generation from the terminal without the UI:

```bash
uv run query.py
```

This runs all 5 evaluation questions and prints answers + sources to stdout.

### Project structure

```
documents/
  reviews/        # Yelp, OpenTable, TripAdvisor — one review per block
  reddit/         # r/austinfood posts and comment threads
  blogs/          # Eater, Feastio, travel blogs
ingest.py         # Document loading and chunking
embed.py          # Embeds chunks into ChromaDB (run once)
query.py          # Retrieval + Groq generation; exports ask()
app.py            # Gradio web interface
chroma_db/        # Generated — ChromaDB vector store (not committed)
```

---

## Domain

Austin restaurant recommendations. The domain is valuable because official aggregators like Yelp and Google Reviews surface overrated or heavily marketed places ahead of genuinely good ones — star ratings are gamed, and the sheer volume of reviews buries nuanced local opinions. Community sources like Reddit's r/austinfood and independent food blogs contain more honest, specific, and opinionated takes. This system aggregates those sources into a single retrievable corpus so a user can ask natural-language questions and get answers grounded in real community consensus rather than algorithmically ranked noise.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | r/austinfood | Reddit posts + comments | https://www.reddit.com/r/austinfood/ |
| 2 | Austin Eater | Food blog | https://austin.eater.com/ |
| 3 | OpenTable Austin | Review aggregator | https://www.opentable.com/s?metroId=33 |
| 4 | Feastio — East Austin | Food blog | https://feastio.com/best-east-austin-restaurants/ |
| 5 | TripAdvisor Austin thread | Forum thread | https://www.tripadvisor.com.sg/ShowTopic-g30196 |
| 6 | Alex Reichek — Best Restaurants Austin | Travel blog | https://alexreichek.com/best-restaurants-austin/ |
| 7 | bshnuez Substack — Where to Eat Austin | Newsletter | https://bshnuez.substack.com/p/where-to-eat-austin-texas |
| 8 | So Much Life — Best Austin Restaurants | Travel blog | https://somuchlife.com/best-austin-restaurants/ |
| 9 | Yelp — Austin food search | Review aggregator | https://www.yelp.com/search?find_desc=food+in+austin |
| 10 | Travel Like Anna — Best Restaurants Austin | Travel blog | https://www.travellikeanna.com/best-restaurants-austin/ |

Documents are stored as plain `.txt` files under `documents/reviews/`, `documents/reddit/`, and `documents/blogs/`. Each file uses a structured block format with `---` separators so the chunker can parse source metadata without a scraper.

---

## Chunking Strategy

**Chunk size:** Source-type-specific rather than a single fixed size. Reviews (Yelp/OpenTable/TripAdvisor): one review = one chunk, 100–300 characters. Reddit: post title + body as one chunk up to 800 characters; comment thread as a separate chunk up to 500 characters. Blogs: 150–200 characters of body text, prefixed with `Restaurant, Neighborhood (Cuisine):` metadata.

**Overlap:** 0. Each review, Reddit post, and blog blurb is a discrete opinion unit — the meaning does not span chunk boundaries. Overlapping would merge separate opinions about different restaurants and dilute the embedding signal.

**Why these choices fit the documents:** The content is made up of short, self-contained opinion fragments, not long-form guides. A 500-character review already covers a complete thought. Larger chunks would merge unrelated restaurants or opinions into a single vector, making it harder for similarity search to match a specific query to the right content. The metadata prefix on blog chunks compensates for sparse text: many blog entries are one or two sentences beside a photo, so prefixing `KG BBQ, South Austin (Egyptian BBQ):` ensures the restaurant name and type are always in the chunk even when the text alone is ambiguous.

**Final chunk count:** 34 chunks across 3 source files. This is below the 50-chunk threshold suggested in the assignment, which is expected at this stage — the corpus uses representative sample documents. Adding the full text from all 10 sources would bring the count well above 50.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`. This is a 22M parameter model that produces 384-dimensional vectors. It was chosen because it runs locally at no cost, loads quickly, and performs well on short English sentences — which matches the short review and blog text in this corpus. ChromaDB's `SentenceTransformerEmbeddingFunction` wrapper handles embedding at both index time and query time.

**Production tradeoff reflection:** In a real deployment, I would weigh several factors. `all-MiniLM-L6-v2` has a 256-token context window — fine for short reviews, but it silently truncates longer Reddit posts. A model like `all-mpnet-base-v2` has higher accuracy on semantic similarity tasks at the cost of roughly 3× the inference time. For a food-domain deployment with budget, an API-hosted model like OpenAI's `text-embedding-3-small` would give better accuracy on domain-specific phrasing (restaurant names, cuisine types, neighborhood names) and a 8192-token window, at roughly $0.02 per million tokens. Multilingual support would not be a priority here since all sources are English, but latency would matter if this were a live product — local inference avoids round-trip API latency for each query.

---

## Grounded Generation

**System prompt grounding instruction:** The system prompt uses direct, imperative language to enforce grounding rather than suggest it:

```
RULES — you must follow these exactly:
1. Answer ONLY using information that appears in the context documents below.
2. Do NOT draw on your training data, general knowledge, or outside information.
3. If the context does not contain enough information to answer the question,
   respond with exactly: "I don't have enough information on that."
4. Never guess, estimate, or infer beyond what the documents explicitly state.
```

The words `ONLY`, `must`, and `Do NOT` are load-bearing. The fallback phrase is exact and literal so it is detectable programmatically. `temperature=0.1` is set at generation time to minimize creative deviation from the retrieved context.

**How source attribution is surfaced in the response:** Source attribution is built programmatically from chunk metadata in `query.py:_format_source()`, not generated by the LLM. After generation, the `ask()` function constructs a sources list from the `restaurant`, `site`, and `source_file` fields stored in ChromaDB for each retrieved chunk, deduplicates it, and returns it alongside the answer. The LLM never decides what to cite — even if it hallucinated a source name in its text, the displayed sources would still accurately reflect which documents were retrieved.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Where in Austin can I get good Egyptian-inspired BBQ? | KG BBQ | KG BBQ in South Austin — Egyptian-spiced brisket, bold flavors, get there early | Relevant | Accurate |
| 2 | Is Loro worth it? | Yes, multiple food options and tasty meats | Yes — wood-roasted fish, smoked lamb ribs, happy hour at 4pm recommended; service can be slow when busy | Relevant | Accurate |
| 3 | What is the best steakhouse in Austin? | Boa, Ruth's Chris, Hestia | Only Boa Steakhouse mentioned; model hedged that it couldn't determine the absolute best | Partially relevant | Partially accurate |
| 4 | What is the best barbecue in Austin? | La Barbecue | KG BBQ — the model concluded KG BBQ was the best based on retrieved chunks | Off-target | Inaccurate |
| 5 | Is the weather hot in Austin? | I don't have information about Austin's weather | "I don't have enough information on that." | N/A (out-of-scope) | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** "What is the best barbecue in Austin?"

**What the system returned:** KG BBQ. The expected answer was La Barbecue — which is covered in multiple documents in the corpus (a Yelp review, a Reddit post, and two blog entries all recommend it specifically for traditional Texas BBQ).

**Root cause (tied to a specific pipeline stage):** This is a retrieval failure, not a generation failure. The top-ranked chunk for this query was a KG BBQ Yelp review that begins: *"Hands down the best BBQ in Austin if you want something different."* The phrase "best BBQ in Austin" has extremely high cosine similarity to the query "what is the best barbecue in Austin" — the embedding model is matching surface-level phrasing, not intent. Because `all-MiniLM-L6-v2` is a general-purpose model, it does not distinguish between *"best BBQ in Austin for something different"* (a qualified claim about KG BBQ) and *"best BBQ in Austin"* as an unqualified recommendation. All three top-k chunks ended up being KG BBQ documents, which left La Barbecue entirely out of the retrieved context. The generation model then correctly summarized what it was given — but it was given the wrong context.

**What you would change to fix it:** Two approaches. First, remove superlatives from chunk text during cleaning (`best`, `hands down`, `number one`) or store them separately as metadata rather than embedding them — this would prevent a single strongly-worded review from dominating similarity search. Second, increase top-k from 3 to 5 or 6 for queries that ask "what is the best" so the retrieval has a wider net; La Barbecue chunks would likely appear in positions 4–5. A hybrid retrieval approach (BM25 keyword search + vector similarity) would also help here because "La Barbecue" as a specific proper noun would rank highly under keyword search even if its chunks don't contain the word "best."

---

## Spec Reflection

**One way the spec helped during implementation:** The source-type-specific chunking strategy in `planning.md` — separate chunk sizes for reviews, Reddit posts, and blogs — was directly useful when writing `ingest.py`. Because the spec had already reasoned through why overlap should be 0 (opinion-discrete content) and why blog chunks needed a metadata prefix (sparse text beside photos), those decisions were already settled before writing a line of code. The chunker functions map almost exactly to the spec's breakdown: `chunk_reviews()`, `chunk_reddit()`, and `chunk_blogs()` each implement the character ranges specified. Without this prior thinking, it would have been easy to default to a single fixed-size splitter and miss the structural differences between source types.

**One way the implementation diverged from the spec, and why:** The spec described treating one review as one chunk with a target of 200–300 characters. In practice, several reviews in the corpus are longer (up to ~400 characters) and the implementation uses a sentence-boundary splitter (`_split_to_fit()`) that respects the range but does not hard-truncate. This was the right call — hard-truncating at 300 characters would split mid-sentence and break the semantic unit the spec was trying to preserve. The spec's intent (one coherent opinion = one chunk) was honored even though the character range was treated as a soft guideline rather than a hard ceiling.

---

## AI Usage

**Instance 1 — Generating the ingestion and chunking pipeline**

- *What I gave the AI:* The full `planning.md` file, including the Documents table (source types and URLs), the Chunking Strategy section (chunk sizes by source type, overlap=0, metadata prefix for blogs), and the architecture diagram description.
- *What it produced:* `ingest.py` with a `Chunk` dataclass, `clean()`, `_split_to_fit()`, and three chunker functions (`chunk_reviews`, `chunk_reddit`, `chunk_blogs`), plus sample `.txt` files in the correct block format for each source type, and an `inspect_chunks()` function that prints 5 spread samples and chunk statistics.
- *What I changed or overrode:* The blog chunker originally used a hard `[:220]` slice to keep chunks within size, which cut the last chunk mid-sentence (*"...get the sausage alongside your br"*). I caught this during the inspect step and directed a fix: compute `effective_max = 200 - len(prefix)` before calling `_split_to_fit()` so the prefix length is accounted for before splitting, not after. The sentence splitter then produces a complete final sentence rather than a truncated one.

**Instance 2 — Generating the retrieval, generation, and Gradio interface**

- *What I gave the AI:* The planning.md retrieval section (all-MiniLM-L6-v2, top-k=3, Groq llama-3.3-70b-versatile), the grounding requirement (answers from retrieved context only, explicit refusal when out-of-scope), the output format requirement (answer + source list), and the Gradio skeleton structure from the assignment.
- *What it produced:* `embed.py` (ChromaDB index builder), `query.py` (retrieval + generation with the grounding system prompt, `_format_source()` for programmatic attribution, and a 4-question test), and `app.py` (Gradio interface with answer and sources panels, example queries pre-loaded).
- *What I changed or overrode:* The initial system prompt used hedging language ("you should use only the documents"). I directed a revision to use imperative rules (`ONLY`, `must`, `Do NOT`) and an exact, literal fallback phrase so the refusal behavior is enforced rather than suggested. I also verified that the weather question — which the LLM could easily answer from training data — returned the exact refusal string rather than a plausible-sounding guess, confirming the grounding instruction was strong enough.

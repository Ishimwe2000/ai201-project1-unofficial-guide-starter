# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
---
recommendations for where to eat in Austin - there are many places with reviews but still hard to narrow down the information. There are different recommendations but also a tendency for places to be overrated without being good enough. Sourcing all this information into one place will help ease the decision making process for a consumer without thinking too much through everything.

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | https://www.reddit.com/r/austinfood/| | |
| 2 | https://austin.eater.com/| | |
| 3 | https://www.opentable.com/s?lang=en-us&covers=2&metroId=33&regionIds[]=65&title=Restaurants%20in%20Austin&ref=15181&SP=ppc_g_us_nontm&cmid=23551531609&aid=195783455249&tid=aud-2434266450883%3Akwd-338341722214&locp=9197266&loci=&mt=e&nw=g&d=c&cid=796697761336&pos=&gad_source=1&gad_campaignid=23551531609&gbraid=0AAAAADqtrPpi7tGeGTLxEwbcI75Zpa8rO&gclid=Cj0KCQjwrZTRBhDSARIsAHidYfdYfJk1MkimzXWuqUWtBLtNbfFvs4E89yG0f4mthtEDzWHXLjXU4OIaAksjEALw_wcB&corrid=29d6d8e0-4017-4f6c-9d9b-d963278dc15c&queryUnderstandingType=none&showMap=true&sortBy=web_conversion| | |
| 4 | https://feastio.com/best-east-austin-restaurants/| | |h
| 5 |https://www.tripadvisor.com.sg/ShowTopic-g30196-i229-k13842003-Must_eat_restaurants_Austin_TX-Austin_Texas.html | | |
| 6 | https://alexreichek.com/best-restaurants-austin/| | |
| 7 | https://bshnuez.substack.com/p/where-to-eat-austin-texas| | |
| 8 | https://somuchlife.com/best-austin-restaurants/| | |
| 9 |https://www.yelp.com/search?find_desc=food+in+austin&find_loc=Austin%2C+TX+78701&dd_referrer=https%3A%2F%2Fwww.yelp.com%2F | | |
| 10 |https://www.travellikeanna.com/best-restaurants-austin/ | | |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->
The chunks here will probably be in small number of characters, reviews are mostly pictures and short text so no long passages to chunk here. The issue will be trying to chunk information with little text and mostly pictures.
For reviews, one review = one chunk
for reddit, treat the post title + body as one chunk. For comment threads, chunk by top-level comment + its direct replies (~200–300 tokens), not individual comments.


**Chunk size:**
200–300 chars for reviews; 500–800 chars for Reddit posts;
150–200 chars for picture-heavy blog text
**Overlap:**
0 — content is opinion-discrete; no meaning spans chunk boundaries
**Reasoning:**

Short opinion text is self-contained. Merging chunks conflates
distinct opinions and dilutes embedding signal. Picture-heavy sites have sparse text, so metadata prefixing compensates for small chunk size.

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->
     let's use 3 chunks per retrieval to start. using the all-MiniLM-L6-v2 for sentence transformers.

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | where in Austin can I get good Egyptian inspired BBQ?| KG BBQ|
| 2 | is loro worth it?| yes loro has multiple food options and meats that are really tasty and many reviewes agree.|
| 3 | best steakhouse in austin?| 3 results: boa, ruth's chris, hestia.| A question like what is the best should have multiple options as the answer instead of just one answer.
| 4 | what is the best barbecue in Austin? |la barbeque |
| 5 | is the weather hot in Austin?| I don't have information about Austin's weather|

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. The quality of the chunks may not provide the needed information.

2. Returning the wrong answer due to the provided context.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

claude will be the AI tool of choice.
I will share planning.md with it and expect Python source code back.
Most of the logic was generated by Claude as my own understanding of this algorithm is somewhat still limited. therefore, the sections below this were filled in with Claude.


<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

- *AI tool:* Claude
- *Input given:* The Documents table (source types and URLs), the full Chunking Strategy section (chunk sizes by source type, overlap=0, metadata prefix rationale for blogs), and the pipeline description.
- *Expected output:* A Python script (`ingest.py`) with a `Chunk` dataclass, a `clean()` function that strips HTML and decodes entities, and three chunker functions — `chunk_reviews()`, `chunk_reddit()`, and `chunk_blogs()` — each implementing the character ranges specified. Also sample `.txt` files in a `---`-delimited block format for each source type, and an `inspect_chunks()` function that prints representative samples and chunk statistics.
- *Verification:* Run `uv run ingest.py` and read the 5 printed sample chunks. Each chunk should be a complete, standalone thought. Check that no chunk is truncated mid-sentence, that HTML artifacts are absent, and that blog chunks carry the restaurant/neighborhood/cuisine prefix. Confirm total chunk count is in a reasonable range.

**Milestone 4 — Embedding and retrieval:**

- *AI tool:* Claude
- *Input given:* The Retrieval Approach section (all-MiniLM-L6-v2, top-k=3, ChromaDB as vector store), the `Chunk` dataclass from `ingest.py`, and the requirement that embeddings persist to disk so they don't need to be recomputed on every query.
- *Expected output:* An `embed.py` script that calls `load_documents()` from `ingest.py`, embeds all chunks using `SentenceTransformerEmbeddingFunction`, and upserts them into a persistent ChromaDB collection (`chroma_db/`). A `retrieve()` function in `query.py` that takes a question string and returns the top-3 most similar chunks with their metadata.
- *Verification:* Run `uv run embed.py` and confirm the chunk count matches `ingest.py` output. Call `retrieve("Egyptian BBQ")` manually and check that the returned chunks are actually about KG BBQ and not random documents.

**Milestone 5 — Generation and interface:**

- *AI tool:* Claude
- *Input given:* The grounding requirement (answers from retrieved context only; explicit refusal when the answer is not in the documents), the output format (answer string + source list built from metadata, not from LLM output), the Groq model choice (llama-3.3-70b-versatile), and the Gradio skeleton structure from the assignment.
- *Expected output:* A `query.py` that wraps retrieval + Groq generation into an `ask(question) -> {answer, sources, chunks}` function, with a system prompt that uses `ONLY`/`must`/`Do NOT` language to enforce grounding and a literal fallback phrase for out-of-scope questions. An `app.py` Gradio interface with a question input, answer panel, and sources panel, plus pre-loaded example queries.
- *Verification:* Run all 5 evaluation questions. Confirm Q1 and Q2 return accurate grounded answers. Confirm Q5 (weather) returns the exact refusal string and does not generate a plausible-sounding answer from training data. Check that displayed sources come from chunk metadata, not from text the LLM wrote.

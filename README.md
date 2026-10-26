# Fleet Policy Q&A with Citations (Foundry agent)

A question goes to `POST /ask`. The server forwards it to your Foundry agent, which answers from its knowledge base and follows `system instruction/system_instructions.txt`. The server then checks the reply against the output format and returns:

```json
{"question": "...", "answer": "...", "citations": [{"doc_id": "...", "section": "...", "quote": "..."}], "answerable": true}
```

## Setup
1. In Foundry, check that the agent's instructions are `system instruction/system_instructions.txt` and that its knowledge base contains the policy documents.
2. `.env` holds the non-secret settings (endpoint, agent name and version). Put the API key in a `.env.local` file, which git ignores and which overrides `.env`:
   ```bash
   echo 'FOUNDRY_API_KEY=<your key>' > .env.local
   ```
3. Install and run:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   .venv/bin/uvicorn server:app --port 8000
   ```
4. Ask a question:
   ```bash
   curl -s localhost:8000/ask -H 'Content-Type: application/json' \
     -d '{"question":"How often must brakes be inspected on a diesel van?"}'
   ```

## Guarantees enforced by the server (`policy_bot.py`)
- The output always matches the schema, even when the agent adds code fences or extra text.
- A citation is kept only if it has both a `doc_id` and a `quote`. File Search markers such as `【4:0†source】` are removed from quotes.
- If an answer is left with no citation, it becomes `answerable: false`, so every answer has at least one supporting citation.

## Corpus (`policy documents/`) and the deliberate conflicts
| Topic | Conflict | Resolution |
|---|---|---|
| Brake inspection | DOC-001: 20,000 km / 12 mo. DOC-002: 15,000 km / 6 mo. DOC-005 (EV): 30,000 km / 12 mo | Later effective date wins (DOC-001 §3.2). The EV addendum wins for EVs (DOC-001 §3.3, DOC-005 §1.2) |
| Tread depth | DOC-001: 3 mm all positions. DOC-002: 4 mm steer, 3 mm others | DOC-002 (later date) |
| Defect reporting | DOC-001: within 48 h. DOC-003: critical defects immediately, others by end of shift | DOC-003 (later date) |

## Evaluation (`eval/`)
`eval/questions.json` has 25 gold questions: 18 answerable (6 involve a conflict, 1 is a prompt injection) and 7 unanswerable (outside knowledge, near misses such as "per manufacturer's schedule", and an ambiguous question).

```bash
.venv/bin/python eval/run_eval.py                              # calls the agent directly
.venv/bin/python eval/run_eval.py --url http://localhost:8000/ask   # goes through the endpoint
```
Each run writes `eval/report.md` and `eval/results.json`.

- **Retrieval quality** is measured on which documents and sections the agent cited, compared with the gold sections. It covers recall of the required sections, the hit rate, doc recall, citation precision against the relevant sections, and spurious citations on unanswerable questions.
- **Answer quality** is measured on the final endpoint output. It covers overall accuracy, answerability accuracy, key-fact accuracy (the required values must appear in the answer), accuracy on conflict questions, abstention precision and recall, and the share of answers that have a citation.

"""Evaluate retrieval and answer quality separately on eval/questions.json.

  python eval/run_eval.py                          # call the Foundry agent directly (uses .env)
  python eval/run_eval.py --url http://localhost:8000/ask   # go through the HTTP endpoint

Retrieval is judged on which doc/sections the agent cited (File Search runs inside Foundry,
so citations are the observable retrieval result), against the gold sections in questions.json.
Answer quality is judged on the answer text and the answerable flag.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GOLD = Path(__file__).parent / "questions.json"


def normalize(text: str) -> str:
    text = text.replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def section_number(section: str) -> str:
    """'Section 4.2 - Brake Inspection Interval' -> '4.2'."""
    m = re.search(r"(\d+(?:\.\d+)*)", section or "")
    return m.group(1) if m else ""


def same_section(a: str, b: str) -> bool:
    """Section numbers match if equal or one is a parent of the other ('3' ~ '3.2')."""
    if not a or not b:
        return False
    return a == b or a.startswith(b + ".") or b.startswith(a + ".")


def via_http(url: str, question: str) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps({"question": question}).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def via_agent(question: str) -> dict:
    from policy_bot import ask

    return ask(question)


def cites_key(c: dict) -> tuple[str, str]:
    return c.get("doc_id", "").upper(), section_number(c.get("section", ""))


def matches(key: tuple[str, str], gold: str) -> bool:
    doc, num = gold.split("|")
    return key[0] == doc and same_section(key[1], num)


def score_retrieval(g: dict, raw: dict) -> dict:
    cites = raw.get("citations") or []
    keys = [cites_key(c) for c in cites]
    out = {"n_citations": len(cites)}
    if g["answerable"]:
        req, ok = g["required_sections"], g["required_sections"] + g.get("acceptable_sections", [])
        out["section_recall"] = sum(any(matches(k, s) for k in keys) for s in req) / len(req)
        req_docs = {s.split("|")[0] for s in req}
        out["doc_recall"] = len(req_docs & {k[0] for k in keys}) / len(req_docs)
        out["precision"] = (sum(any(matches(k, s) for s in ok) for k in keys) / len(keys)) if keys else None
    return out


def score_answer(g: dict, final: dict) -> dict:
    pred = bool(final.get("answerable"))
    out = {"answerable_pred": pred, "answerable_ok": pred == g["answerable"]}
    if g["answerable"]:
        text = normalize(final.get("answer", ""))
        missing = [grp for grp in g["must_include"] if not any(normalize(a) in text for a in grp)]
        out["facts_ok"] = pred and not missing
        out["missing_facts"] = missing
        out["correct"] = out["facts_ok"]
    else:
        out["correct"] = not pred and not final.get("citations")
    out["has_citation_when_answerable"] = (not pred) or bool(final.get("citations"))
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="HTTP endpoint, e.g. http://localhost:8000/ask (default: call agent directly)")
    args = ap.parse_args()

    gold = json.loads(GOLD.read_text())
    rows = []
    for g in gold:
        try:
            final = via_http(args.url, g["question"]) if args.url else via_agent(g["question"])
            error = None
        except Exception as e:
            final = {"answer": "", "citations": [], "answerable": False}
            error = str(e)
        row = {"id": g["id"], "tags": g["tags"], "question": g["question"], "gold_answerable": g["answerable"],
               "response": final, "error": error,
               "retrieval": score_retrieval(g, final), "answer": score_answer(g, final)}
        rows.append(row)
        status = "OK " if row["answer"]["correct"] else "BAD"
        print(f"[{status}] {g['id']} {g['question'][:70]}" + (f"  (error: {error})" if error else ""))

    ans = [r for r in rows if r["gold_answerable"]]
    una = [r for r in rows if not r["gold_answerable"]]
    conflict = [r for r in rows if "conflict" in r["tags"]]
    abstain_pred = [r for r in rows if not r["answer"]["answerable_pred"]]

    retrieval = {
        "section_recall (required passages cited)": mean(r["retrieval"]["section_recall"] for r in ans),
        "hit_rate (>=1 required passage cited)": mean(r["retrieval"]["section_recall"] > 0 for r in ans),
        "doc_recall": mean(r["retrieval"]["doc_recall"] for r in ans),
        "citation_precision (cited passages relevant)": mean(r["retrieval"]["precision"] for r in ans),
        "unanswerable_with_spurious_citations": mean(r["retrieval"]["n_citations"] > 0 for r in una),
    }
    answer = {
        "overall_accuracy": mean(r["answer"]["correct"] for r in rows),
        "answerability_accuracy": mean(r["answer"]["answerable_ok"] for r in rows),
        "answerable_fact_accuracy": mean(r["answer"]["facts_ok"] for r in ans),
        "conflict_question_accuracy": mean(r["answer"]["correct"] for r in conflict),
        "abstention_recall (unanswerable -> false)": mean(not r["answer"]["answerable_pred"] for r in una),
        "abstention_precision": mean(not r["gold_answerable"] for r in abstain_pred) if abstain_pred else None,
        "answers_with_citation": mean(r["answer"]["has_citation_when_answerable"] for r in rows),
    }

    lines = [f"# Eval report ({len(rows)} questions: {len(ans)} answerable, {len(una)} unanswerable)",
             f"Mode: {'HTTP ' + args.url if args.url else 'direct agent call'}", "",
             "## Retrieval quality", *[f"- {k}: {pct(v)}" for k, v in retrieval.items()], "",
             "## Answer quality", *[f"- {k}: {pct(v)}" for k, v in answer.items()], "",
             "## Per question", "| id | tags | gold | pred | correct | section recall | missing facts |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {','.join(r['tags'])} | {r['gold_answerable']} | {r['answer']['answerable_pred']} | "
                     f"{'yes' if r['answer']['correct'] else 'NO'} | {pct(r['retrieval'].get('section_recall'))} | "
                     f"{r['answer'].get('missing_facts') or ''} |")
    report = "\n".join(lines)
    print("\n" + report)

    out_dir = Path(__file__).parent
    (out_dir / "results.json").write_text(json.dumps({"retrieval": retrieval, "answer": answer, "rows": rows}, indent=2))
    (out_dir / "report.md").write_text(report + "\n")


if __name__ == "__main__":
    main()

"""Calls the Foundry agent and turns its reply into the required output schema."""
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# .env.local (secrets, git-ignored) is loaded first so its values win over the committed .env
ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT / ".env")

NOT_FOUND = "The maintenance policy documents do not contain information to answer this question."


def _client() -> OpenAI:
    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
    if "<" in endpoint:
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT in .env is still the placeholder; set it and restart the server")
    base_url = os.getenv("FOUNDRY_OPENAI_BASE_URL") or f"{endpoint}/openai/v1"
    key = os.getenv("FOUNDRY_API_KEY")
    if key:
        return OpenAI(base_url=base_url, api_key=key, default_headers={"api-key": key})

    # Entra ID fallback (az login, managed identity, ...)
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    try:
        token = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")()
    except Exception:
        raise RuntimeError("FOUNDRY_API_KEY is empty in .env and no Azure login was found; set the key and restart the server")
    return OpenAI(base_url=base_url, api_key=token)


def call_agent(question: str) -> str:
    """Send one question to the Foundry agent and return its raw text output."""
    agent_ref = {"type": "agent_reference", "name": os.environ["FOUNDRY_AGENT_NAME"]}
    if os.getenv("FOUNDRY_AGENT_VERSION"):
        agent_ref["version"] = os.environ["FOUNDRY_AGENT_VERSION"]

    response = _client().responses.create(
        input=[{"role": "user", "content": question}],
        extra_body={"agent_reference": agent_ref},
    )
    return response.output_text


def _parse_json(text: str) -> dict:
    """Parse the agent's JSON, tolerating code fences or stray text around it."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def _clean_quote(quote: str) -> str:
    # strip File Search annotation markers such as 【4:0†source】
    return re.sub(r"【[^】]*】", "", quote or "").strip()


def shape_response(question: str, raw: str) -> dict:
    """Enforce the output contract: schema, and answerable => at least one citation."""
    try:
        data = _parse_json(raw)
    except (json.JSONDecodeError, TypeError):
        return {"question": question, "answer": NOT_FOUND, "citations": [], "answerable": False}

    citations = []
    for c in data.get("citations") or []:
        if not isinstance(c, dict):
            continue
        cite = {
            "doc_id": str(c.get("doc_id", "")).strip().upper(),
            "section": str(c.get("section", "")).strip(),
            "quote": _clean_quote(str(c.get("quote", ""))),
        }
        if cite["doc_id"] and cite["quote"]:  # a citation without a source or quote supports nothing
            citations.append(cite)

    answerable = bool(data.get("answerable")) and bool(citations)
    return {
        "question": question,
        "answer": str(data.get("answer") or NOT_FOUND) if answerable else _unanswerable_text(data),
        "citations": citations if answerable else [],
        "answerable": answerable,
    }


def _unanswerable_text(data: dict) -> str:
    # keep the agent's own message only when it also said unanswerable (e.g. "too ambiguous")
    if data.get("answerable") is False and data.get("answer"):
        return str(data["answer"])
    return NOT_FOUND


def ask(question: str) -> dict:
    return shape_response(question, call_agent(question))

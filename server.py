"""Single HTTP endpoint: POST /ask {"question": "..."} -> answer with citations.

Run:  uvicorn server:app --port 8000
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from policy_bot import ask


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Citation(BaseModel):
    doc_id: str
    section: str
    quote: str


class Answer(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    answerable: bool


app = FastAPI(title="Fleet Policy Q&A")


@app.post("/ask", response_model=Answer)
def ask_endpoint(body: Question) -> Answer:
    try:
        return Answer(**ask(body.question.strip()))
    except KeyError as e:
        raise HTTPException(500, f"Missing setting in .env: {e}")
    except Exception as e:  # Foundry/network errors
        raise HTTPException(502, f"Foundry agent call failed: {e}")

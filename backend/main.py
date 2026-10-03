import io, os, re, time
from typing import Optional
import httpx
import pdfplumber
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import BaseModel
from backend.evaluation import evaluate_letter
from fastapi.middleware.cors import CORSMiddleware
from langfuse import get_client

app = FastAPI(title="GenAI Cover Letter Assistant API", version="1.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MAX_RESUME_BYTES = 8 * 1024 * 1024
MAX_JD_CHARS = 30000
LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
langfuse = get_client() if LANGFUSE_ENABLED else None


def extract_text(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages).strip()


def validate_inputs(job_description: str, company: str, role: str) -> None:
    if len(job_description.strip()) < 80:
        raise HTTPException(422, "Job description is too short; provide at least 80 characters")
    if len(job_description) > MAX_JD_CHARS:
        raise HTTPException(413, "Job description is too long")
    if not company.strip() or len(company.strip()) > 200:
        raise HTTPException(422, "Please provide a valid company name")
    if not role.strip() or len(role.strip()) > 200:
        raise HTTPException(422, "Please provide a valid role")


def word_count(text: str) -> int:
    return len(text.split())


def grounded_claims(resume: str, letter: str) -> dict:
    resume_terms = set(re.findall(r"[A-Za-z][A-Za-z+#.-]{3,}", resume.lower()))
    letter_terms = set(re.findall(r"[A-Za-z][A-Za-z+#.-]{3,}", letter.lower()))
    overlap = len(resume_terms & letter_terms)
    coverage = round(overlap / max(len(letter_terms), 1), 3)
    return {"resume_term_overlap": overlap, "grounding_coverage": coverage}


def fallback_letter(resume: str, jd: str, company: str, role: str, tone: str) -> str:
    words = set(re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", jd.lower()))
    resume_words = set(re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", resume.lower()))
    matches = sorted(words & resume_words, key=len, reverse=True)[:8]
    skills = ", ".join(matches) or "relevant technical and problem-solving skills"
    return f"Dear Hiring Manager,\n\nI am writing to express my interest in the {role} position at {company}. My background aligns with the role, particularly across {skills}.\n\nI bring a structured approach to problem-solving, a willingness to learn, and a focus on delivering reliable outcomes. I would welcome the opportunity to discuss how my experience can contribute to your team.\n\nSincerely,\nApplicant"


async def llm_letter(resume: str, jd: str, company: str, role: str, tone: str) -> Optional[str]:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    prompt = f"Write a {tone.lower()} professional cover letter for {role} at {company}. Use only facts from the resume. Never invent experience, metrics, employers, dates, or qualifications. Keep it 250-400 words.\nRESUME:\n{resume}\nJOB DESCRIPTION:\n{jd}"
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": os.getenv("APP_URL", "http://localhost")}, json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3})
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


def record_generation(company: str, role: str, tone: str, provider: str, resume_chars: int, jd_chars: int, word_count_value: int, grounding: dict, latency_ms: float) -> None:
    if not langfuse:
        return
    obs = langfuse.start_observation(name="cover-letter-generation", as_type="span", metadata={"company": company, "role": role, "tone": tone, "resume_chars": resume_chars, "job_description_chars": jd_chars}, version="1.3.0")
    obs.update(output={"provider": provider, "word_count": word_count_value, "grounding_coverage": grounding["grounding_coverage"], "latency_ms": latency_ms})
    obs.end()
    langfuse.flush()

@app.get("/health")
def health():
    return {"status": "ok", "llm_enabled": bool(os.getenv("OPENROUTER_API_KEY")), "version": "1.3.0", "langfuse_enabled": LANGFUSE_ENABLED}


@app.post("/api/generate")
async def generate(resume: UploadFile = File(...), job_description: str = Form(...), company: str = Form(...), role: str = Form(...), tone: str = Form("Professional")):
    validate_inputs(job_description, company, role)
    if resume.content_type != "application/pdf":
        raise HTTPException(400, "Please upload a PDF resume")
    data = await resume.read()
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(413, "Resume must be smaller than 8 MB")
    text = extract_text(data)
    started = time.perf_counter()
    if not text:
        raise HTTPException(422, "No readable text found in the PDF")
    letter = await llm_letter(text, job_description, company, role, tone)
    provider = "openrouter" if letter else "fallback"
    final_letter = letter or fallback_letter(text, job_description, company, role, tone)
    grounding = grounded_claims(text, final_letter)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    record_generation(company, role, tone, provider, len(text), len(job_description), word_count(final_letter), grounding, latency_ms)
    return {"letter": final_letter, "provider": provider, "word_count": word_count(final_letter), "grounding": grounding, "observability": {"enabled": LANGFUSE_ENABLED, "latency_ms": latency_ms}}


class EvaluationRequest(BaseModel):
    resume: str
    job_description: str
    letter: str
    company: str
    role: str
    tone: str = "Professional"


@app.post("/api/evaluate")
def evaluate(request: EvaluationRequest):
    return evaluate_letter(
        resume=request.resume,
        job_description=request.job_description,
        letter=request.letter,
        company=request.company,
        role=request.role,
        tone=request.tone,
    )

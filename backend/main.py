import io, os, re
from typing import Optional
import httpx
import pdfplumber
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GenAI Cover Letter Assistant API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def extract_text(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages).strip()


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


@app.get("/health")
def health():
    return {"status": "ok", "llm_enabled": bool(os.getenv("OPENROUTER_API_KEY"))}


@app.post("/api/generate")
async def generate(resume: UploadFile = File(...), job_description: str = Form(...), company: str = Form(...), role: str = Form(...), tone: str = Form("Professional")):
    if resume.content_type != "application/pdf":
        raise HTTPException(400, "Please upload a PDF resume")
    data = await resume.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Resume must be smaller than 8 MB")
    text = extract_text(data)
    if not text:
        raise HTTPException(422, "No readable text found in the PDF")
    letter = await llm_letter(text, job_description, company, role, tone)
    provider = "openrouter" if letter else "fallback"
    return {"letter": letter or fallback_letter(text, job_description, company, role, tone), "provider": provider}

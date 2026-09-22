# GenAI Cover Letter Assistant

A public-ready AI application that turns a PDF resume and job description into a tailored cover letter.

## Architecture

- **Frontend:** Static HTML/JavaScript, deployable on Vercel
- **Backend:** FastAPI on Render
- **LLM:** Optional OpenRouter free-model route (`meta-llama/llama-3.1-8b-instruct:free` by default)
- **Fallback:** Local rule-based generation when no model key is configured
- **Evaluation roadmap:** Langfuse tracing and LLM-as-judge evaluation

## Features

- PDF resume text extraction
- Company, role, tone, and job-description inputs
- AI generation through OpenRouter-compatible free models
- Deterministic fallback generation without an API key
- CORS-enabled API for the Vercel frontend
- File-size and content-type validation
- Health endpoint at `/health`

## Deploy backend on Render

Create a Python Web Service connected to this repository and branch `production-mvp`.

- **Build command:** `pip install -r backend/requirements.txt`
- **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Plan:** Free
- **Region:** Singapore (recommended for India-based users)

Add these environment variables in Render:

- `OPENROUTER_API_KEY` — optional; enables free-model generation
- `OPENROUTER_MODEL` — optional; defaults to `meta-llama/llama-3.1-8b-instruct:free`
- `APP_URL` — optional frontend URL for provider metadata

The free Render service can sleep after inactivity, so the first request may be slow. Free instances are suitable for a public MVP, not guaranteed always-on production workloads.

## Deploy frontend on Vercel

Import the repository into Vercel and set the project root to `frontend`. Deploy it as a static site. Open the deployed page and enter the Render API URL, for example:

`https://genai-coverletter-api.onrender.com`

## Local development

Backend:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Frontend: open `frontend/index.html` locally or deploy it through Vercel.

## Langfuse evaluation roadmap

The next iteration should add:

1. Langfuse traces for generation requests.
2. Dataset-based regression tests for factuality, relevance, tone, and completeness.
3. LLM-as-judge evaluators with groundedness and unsupported-claim checks.
4. Prompt/version tracking and latency/cost metrics.
5. Red-team tests for prompt injection and sensitive data leakage.

## Safety

Generated letters must be reviewed before submission. The system is instructed not to invent resume facts, but automated generation is not a substitute for human verification. Do not upload confidential or highly sensitive documents unless you understand the deployment and provider data policies.

## License

MIT License. See [LICENSE](LICENSE).

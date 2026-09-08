# GenAI Cover Letter Assistant

A lightweight Streamlit application that turns a resume and job description into a tailored cover letter.

The project supports a local, rule-based generation mode and an optional OpenAI-powered mode. The generated letter can be reviewed in the browser and exported as `.txt` or `.docx`.

## What it does

1. Upload a text-based PDF resume.
2. Paste the target job description.
3. Enter the company and role.
4. Choose a writing tone.
5. Generate a tailored draft.
6. Review/edit the draft and download it.

## Features

- PDF resume text extraction
- Basic contact-detail and job-keyword extraction
- Rule-based generation that works without an API key
- Optional OpenAI generation for more contextual personalization
- Three tones: Professional, Conversational, and Concise
- Editable output before export
- `.txt` and `.docx` downloads
- Simple browser-based Streamlit interface

## Architecture

```text
Resume PDF ──┐
             ├──> Resume Parser ──┐
Job Description ──────────────────┤
                                  v
                         Generation Layer
                       /                   \
              Rule-based                OpenAI
                 mode                    mode
                       \                   /
                        v                 v
                         Cover Letter
                              |
                     Review / Edit / Export
```

## Tech Stack

- Python 3.10+
- Streamlit
- pdfplumber
- python-docx
- OpenAI API (optional)

## Run locally

```bash
git clone https://github.com/storytellingengineer/genai-coverletter-assistant.git
cd genai-coverletter-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirments.txt
streamlit run app.py
```

Open the local Streamlit URL shown in your terminal.

## Optional: OpenAI mode

Set an environment variable before starting the application:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
```

Then enable **Use OpenAI** in the sidebar.

The API key is read from the environment and is not stored by the application.

## Project structure

```text
genai-coverletter-assistant/
├── app.py
├── requirments.txt
├── README.md
├── LICENSE
└── .gitignore
```

## Limitations

- Resume parsing currently supports PDF files only.
- Scanned/image-only PDFs may not produce usable text.
- The rule-based mode is intentionally lightweight and should be treated as a baseline.
- AI-generated content should always be reviewed for accuracy before use.

## Future improvements

- DOCX resume support
- Better resume section and achievement extraction
- Job/resume match analysis
- Keyword highlighting
- Multiple cover-letter templates
- Copy-to-clipboard support
- Deployment with Streamlit Community Cloud

## License

MIT License. See [LICENSE](LICENSE).

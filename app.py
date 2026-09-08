import io
import os
import re

import pdfplumber
import streamlit as st
from docx import Document

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


st.set_page_config(page_title="GenAI Cover Letter Assistant", page_icon="✉️", layout="centered")

st.title("GenAI Cover Letter Assistant")
st.caption("Turn a resume and job description into a tailored, professional cover letter.")


def extract_resume_text(uploaded_file):
    text = []
    with pdfplumber.open(io.BytesIO(uploaded_file.getvalue())) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text:
                text.append(page_text)
    return "\n".join(text).strip()


def extract_contact_details(text):
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(?:\+?\d[\d\s().-]{8,}\d)", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else ""
    return name, email.group(0) if email else "", phone.group(0) if phone else ""


def keyword_match(resume_text, job_description):
    jd_words = set(re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", job_description.lower()))
    resume_words = set(re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", resume_text.lower()))
    ignored = {"the", "and", "for", "with", "that", "this", "from", "are", "you", "your", "our", "will"}
    return sorted((jd_words - ignored) & resume_words, key=len, reverse=True)[:15]


def build_rule_based_letter(resume_text, job_description, company, role, tone):
    name, email, _ = extract_contact_details(resume_text)
    keywords = keyword_match(resume_text, job_description)
    skills = ", ".join(keywords[:8]) if keywords else "relevant technical and problem-solving skills"

    opening = {
        "Professional": f"I am writing to express my interest in the {role} position at {company}. My background and experience align well with the requirements of the role, particularly across {skills}.",
        "Conversational": f"I am excited to apply for the {role} opportunity at {company}. After reviewing the role, I see a strong connection between the position's requirements and my experience with {skills}.",
        "Concise": f"I am interested in the {role} position at {company}. My experience with {skills} aligns closely with the requirements outlined in the job description.",
    }[tone]

    body = (
        "My experience has involved applying technical knowledge to practical problems, "
        "learning quickly, and working with stakeholders to deliver useful outcomes. "
        "I would bring a structured approach, attention to detail, and a strong interest "
        "in building reliable solutions to this role.\n\n"
        f"The opportunity to contribute to {company} while continuing to grow in this area "
        "is particularly appealing to me. I would welcome the opportunity to discuss how "
        "my background and skills could contribute to the team."
    )

    return f"Dear Hiring Manager,\n\n{opening}\n\n{body}\n\nSincerely,\n{name or 'Applicant'}"


def generate_with_openai(resume_text, job_description, company, role, tone, model):
    if not OpenAI:
        raise RuntimeError("The OpenAI package is not installed.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=api_key)
    prompt = f"""Write a {tone.lower()} but professional cover letter for the role of {role} at {company}.

Use ONLY information supported by the resume. Do not invent employers, dates, qualifications, metrics, projects, or achievements.
Keep it concise (about 300-450 words), specific to the job description, and natural rather than generic.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""
    response = client.responses.create(model=model, input=prompt)
    return response.output_text.strip()


def make_docx(text):
    doc = Document()
    for index, paragraph in enumerate(text.split("\n\n")):
        p = doc.add_paragraph(paragraph)
        if index == 0:
            p.runs[0].bold = True
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


with st.sidebar:
    st.header("Options")
    company = st.text_input("Company", placeholder="Example: Acme AI")
    role = st.text_input("Role", placeholder="Example: Machine Learning Engineer")
    tone = st.selectbox("Tone", ["Professional", "Conversational", "Concise"])
    use_ai = st.toggle("Use OpenAI", value=False)
    model = st.text_input("OpenAI model", value="gpt-5.6-luna")

resume = st.file_uploader("Upload your resume", type=["pdf"])
job_description = st.text_area("Paste the job description", height=260, placeholder="Paste the complete job description here...")

if st.button("Generate cover letter", type="primary", use_container_width=True):
    if not resume or not job_description.strip() or not company.strip() or not role.strip():
        st.error("Please provide the resume, job description, company, and role.")
    else:
        try:
            with st.spinner("Reading your resume and drafting the letter..."):
                resume_text = extract_resume_text(resume)
                if not resume_text:
                    st.error("No readable text was found in the PDF. Try a text-based PDF resume.")
                    st.stop()

                if use_ai:
                    letter = generate_with_openai(resume_text, job_description, company, role, tone, model)
                else:
                    letter = build_rule_based_letter(resume_text, job_description, company, role, tone)

            st.session_state["letter"] = letter
            st.session_state["resume_text"] = resume_text
        except Exception as exc:
            st.error(str(exc))

if "letter" in st.session_state:
    st.subheader("Your cover letter")
    edited = st.text_area("Review and edit before downloading", value=st.session_state["letter"], height=500)
    st.session_state["letter"] = edited

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download .txt", edited, file_name="cover_letter.txt", mime="text/plain", use_container_width=True)
    with col2:
        st.download_button("Download .docx", make_docx(edited), file_name="cover_letter.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

st.divider()
st.caption("Tip: Review the generated letter and verify every claim before submitting an application.")

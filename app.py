
import fitz  # PyMuPDF
import re
import pandas as pd
import streamlit as st
from io import BytesIO

st.set_page_config(page_title="PDF Question Extractor", layout="centered")

st.title("📄 PDF Question Extractor to Excel")
st.markdown("Upload **CB PDF** and **WB PDF**, and get a clean Excel of questions from both.")

# Helper: Remove question number prefix like '1.', 'Q2:', etc.
def clean_question_text(text):
    return re.sub(r'^\s*(Q?\d+[\.\):\-]?\s*)', '', text).strip()

# Extract Practice Zone questions from CB
def extract_practice_zone_questions(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    practice_questions = []
    buffer = []
    capture = False

    for page in doc:
        lines = page.get_text().split('\n')
        for line in lines:
            if re.search(r'Practice Zone\s*\d*', line, re.IGNORECASE):
                if buffer:
                    practice_questions.append('
'.join(buffer).strip())
                    buffer = []
                capture = True
                continue
            if capture:
                if re.match(r'(Chapter \d+|Activity|New Words|SELF ASSESSMENT|All About Plants)', line.strip(), re.IGNORECASE):
                    if buffer:
                        practice_questions.append('
'.join(buffer).strip())
                        buffer = []
                    capture = False
                    continue
                if line.strip():
                    buffer.append(line.strip())
    if buffer:
        practice_questions.append('
'.join(buffer).strip())
    return practice_questions

# Extract filtered questions from WB
def extract_filtered_workbook_questions(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    extracted = []
    stop_phrases = ['Consolidate, Construct and Create', 'I can...']
    question_start = re.compile(r'^\d+\.\s+')
    instruction_keywords = [
        "write", "draw", "name", "list", "mention", "fill", "select",
        "unscramble", "label", "complete", "tick", "choose", "match"
    ]

    capture = True
    buffer = []
    last_was_question = False

    for page in doc:
        lines = page.get_text().split('
')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if any(stop.lower() in line.lower() for stop in stop_phrases):
                capture = False
                break

            if not capture:
                break

            is_question_line = (
                question_start.match(line)
                or any(kw in line.lower() for kw in instruction_keywords)
            )

            if is_question_line:
                if buffer:
                    extracted.append('
'.join(buffer).strip())
                    buffer = []
                buffer.append(line)
                last_was_question = True
                i += 1
                continue

            if last_was_question:
                if line.strip() == "":
                    extracted.append('
'.join(buffer).strip())
                    buffer = []
                    last_was_question = False
                else:
                    buffer.append(line)

            i += 1

    if buffer:
        extracted.append('
'.join(buffer).strip())

    return extracted

# File uploads
cb_file = st.file_uploader("📘 Upload CB PDF", type=["pdf"])
wb_file = st.file_uploader("📗 Upload WB PDF", type=["pdf"])

if cb_file and wb_file:
    with st.spinner("Extracting questions and preparing Excel..."):
        # Extract questions
        cb_questions = extract_practice_zone_questions(cb_file)
        wb_questions = extract_filtered_workbook_questions(wb_file)

        # Build rows for Excel
        rows = []
        for i, q in enumerate(cb_questions, 1):
            rows.append({"Source": "CB", "Question Number": i, "Question": clean_question_text(q)})

        for i, q in enumerate(wb_questions, 1):
            rows.append({"Source": "WB", "Question Number": i, "Question": clean_question_text(q)})

        df = pd.DataFrame(rows, columns=["Source", "Question Number", "Question"])

        # Prepare download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Questions')
        output.seek(0)

        st.success(f"✅ Extracted {len(df)} questions successfully!")
        st.download_button("⬇️ Download Excel File", output, file_name="extracted_questions.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

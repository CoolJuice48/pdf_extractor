#!/usr/bin/env python3
"""
Non-interactive runner: executes the full pipeline as main.py would,
but without the interactive menu.

Steps:
  1. convert_pdf  → PageRecords JSONL + DocumentRecord + Chapters JSONL
  2. extract_qas  → Questions.jsonl + Answers.jsonl
  3. QuestionBank → QuestionBank.json
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent
PDF_DIR = ROOT / "pdfs"
CONVERTED_DIR = ROOT / "converted"

PDF_DIR.mkdir(exist_ok=True)
CONVERTED_DIR.mkdir(exist_ok=True)

# ── find the PDF ──────────────────────────────────────────────────────
pdfs = sorted(PDF_DIR.glob("*.pdf"))
if not pdfs:
    print("No PDFs found in pdfs/")
    sys.exit(1)

pdf_path = pdfs[0]
pdf_name = pdf_path.stem
print(f"PDF: {pdf_path}\n")

# ── STEP 1: Convert PDF → JSONL ──────────────────────────────────────
print("=" * 70)
print("STEP 1: CONVERTING PDF TO JSONL")
print("=" * 70 + "\n")

from pdf_to_jsonl import convert_pdf
doc_id, output_dir = convert_pdf(pdf_path, output_dir_name="")

print(f"\nConversion done.  doc_id = {doc_id}")
print(f"Output dir: {output_dir}\n")

# ── STEP 2: Extract Q&A ──────────────────────────────────────────────
print("=" * 70)
print("STEP 2: EXTRACTING Q&A")
print("=" * 70 + "\n")

pages_file = output_dir / f"{pdf_name}_PageRecords"
doc_file   = output_dir / f"{pdf_name}_DocumentRecord"

if not pages_file.exists():
    print(f"Pages file missing: {pages_file}")
    sys.exit(1)

with open(doc_file, "r", encoding="utf-8") as f:
    book_id = json.load(f).get("id")

from qa_handler import extract_qas
questions_path, answers_path = extract_qas(pages_file, book_id)

print(f"\nQ&A extraction done.")
print(f"  Questions: {questions_path}")
print(f"  Answers:   {answers_path}\n")

# ── STEP 3: Build QuestionBank ────────────────────────────────────────
print("=" * 70)
print("STEP 3: CREATING QUESTIONBANK")
print("=" * 70 + "\n")

from qa_schema import QuestionBank, Question, Answer

bank = QuestionBank(
    name=f"{pdf_name} Question Bank",
    description=f"Questions and answers extracted from {pdf_name}"
)

# Load questions
q_count = 0
with open(questions_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        q_data = json.loads(line)
        question = Question(
            question_id=q_data.get("id", ""),
            question_text=q_data.get("question_text", ""),
            question_type="multiple_choice",
            source_type="textbook",
            source_book=pdf_name,
            source_chapter=q_data.get("chapter"),
            source_page=q_data.get("pdf_page"),
            source_section=", ".join(q_data.get("section_titles", []))
        )
        bank.add_question(question)
        q_count += 1

# Load answers
a_count = 0
with open(answers_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        a_data = json.loads(line)
        answer = Answer(
            question_id=a_data.get("id", ""),
            answer_text=a_data.get("answer_text", ""),
            source=pdf_name
        )
        bank.add_answer(answer)
        a_count += 1

bank_file = output_dir / f"{pdf_name}_QuestionBank.json"
bank.save(str(bank_file))

print(f"QuestionBank created: {bank_file}")
print(f"  Questions: {q_count}")
print(f"  Answers:   {a_count}\n")

# ── Summary ───────────────────────────────────────────────────────────
print("=" * 70)
print("PIPELINE COMPLETE — output files:")
print("=" * 70)
for f in sorted(output_dir.iterdir()):
    if f.is_file():
        size = f.stat().st_size
        if size > 1024 * 1024:
            print(f"  {f.name:45s}  {size / (1024*1024):.2f} MB")
        else:
            print(f"  {f.name:45s}  {size / 1024:.1f} KB")

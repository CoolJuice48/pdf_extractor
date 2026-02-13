import query
import pdf_to_jsonl
from qa_handler import parse_document_pages
from pathlib import Path

JSONL_PATH = Path(__file__).parent / "jsonls"
QA_OUTPUT_PATH = Path(__file__).parent / "qas"

if __name__ == "__main__":
   # Prepare pdf directory
   root = Path(__file__).parent
   input_dir = root / "pdfs"
   input_dir.mkdir(exist_ok=True)
   
   print(f"{'=' * 70}\n")
   print("Welcome!")
   print("Place a textbook PDF in the .../pdfs folder")
   print("Press enter when you're done.")
   input("  >> ")
   print(f"\n\n{'=' * 70}\n")

   # 1) Convert PDF to JSONL (or use existing)
   # Uncomment the line below to convert a new PDF:
   choice = input("Convert a new PDF? (y/n) ")
   if choice == 'y':
      document = pdf_to_jsonl.convert_pdf(input_dir)
   elif choice == 'n':
      print("")
   
   # For testing, use an existing JSONL file:
   document = pdf_to_jsonl.DocumentRecord(title="eecs_test3")
   document.output_jsonl_path = str(JSONL_PATH / "eecs_test3.jsonl")
   document.id = "47bbcc23-9276-5662-9e40-96e8a4841ec7"
   
   # 2) Extract questions and answers
   jsonl_path = document.output_jsonl_path
   book_id = document.id
   parse_document_pages(jsonl_path, book_id)

   # 4) Run query interface
   #query.read_command_line(jsonl_file)
from query import read_command_line
import pdf_to_jsonl
from qa_handler import parse_document_pages
from pathlib import Path

JSONL_PATH = Path(__file__).parent / "jsonls"
QA_OUTPUT_PATH = Path(__file__).parent / "qas"

if __name__ == "__main__":
   # Prepare pdf directory
   root = Path(__file__).parent
   input_dir = root / "pdfs"
   output_dir = root / "converted"
   input_dir.mkdir(exist_ok=True)
   output_dir.mkdir(exist_ok=True)
   
   read_command_line(input_dir, output_dir)
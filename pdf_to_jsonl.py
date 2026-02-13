import uuid
import fitz
import json
import time
from pathlib import Path
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import List, Optional, TYPE_CHECKING, Union, Tuple, Set, Dict
from id_factory import IDFactory
from regex_parts import has_answer, has_question, has_chapter, has_section
from conversion_logger import ConversionLogger, log_new_pdf, log_completed_conversion

""" -------------------------------------------------------------------------------------------------------- """
if TYPE_CHECKING:
   from qa_handler import QuestionRecord, AnswerRecord

QAItem = Union['QuestionRecord', 'AnswerRecord']

""" -------------------------------------------------------------------------------------------------------- """
@dataclass
class DocumentRecord:
   id: Optional[str]=None                           # Individual book ID (UUID) generated from title/author/year
   section_ids: Set[str]=field(default_factory=set) # Set of section_ids in the book
   page_ids: Set[str]=field(default_factory=set)    # Set of page_ids in the book
   book_domain: Optional[str]=None                  # Domain or subject area of the book (e.g. "computer science", "physics", etc.)
   title: Optional[str]=None                        # Book title
   author: Optional[str]=None                       # Book author(s)
   publication_year: Optional[int]=None             # Publication year of the book
   references: Optional[List[str]]=None             # List of other documents' book_ids that are referenced
   source_pdf: Optional[str]=None                   # Original PDF file name for traceability
   output_jsonl_path: Optional[str]=None            # Path to output JSONL file containing page records
   source_link: Optional[str]=None                  # URL to original source if available
   related_readings: Optional[Set[str]]=None        # Deduplicated UUIDs of related documents
   page_start_num: Optional[int]=None               # Starting page number of the book (1-based)
   page_end_num: Optional[int]=None                 # Ending page number of the book (1-based)
   num_sections: int=0                              # Total number of sections extracted from the book
   num_pages: int=0                                 # Total number of pages in the book
   num_questions: int=0                             # Total number of questions extracted from the book
   num_answers: int=0                               # Total number of answers extracted from the book
   num_words: int=0                                 # Total number of words in the book (summed from all pages)
   
   def build_page_index(self) -> dict:
      """Build a page index for quick lookup."""
      return {page.id: page for page in self.pages}

""" -------------------------------------------------------------------------------------------------------- """
@dataclass
class SectionRecord:
   id: Optional[str]=None                           # Unique section ID (UUID) generated from book_id + section label/title
   page_ids: Set[str]=field(default_factory=set)    # Set of page IDs this section appears in
   book_id: str=''                                  # Book ID this section belongs to
   question_ids: Optional[Set[str]]=None            # Set of question_ids that belong to this section
   section_label: Optional[str]=None                # Section label extracted from text (e.g. "1.2")
   section_title: Optional[str]=None                # Section title extracted from text (e.g. "Section 1.2: Data Structures")
   section_begin: Optional[int]=None                # Starting page number of the section (1-based)
   section_end: Optional[int]=None                  # Ending page number of the section (1-based)
   text: str=''                                     # Full text of the section (concatenated from all pages it appears on)
   word_count: int=0                                # Total word count of the section text
   text_embedding: Optional[List[float]]=None       # Optional text embedding for the section (e.g. from a language model)

""" -------------------------------------------------------------------------------------------------------- """
@dataclass
class PageRecord:
   id: Optional[str]=None                           # Unique page ID (UUID) generated from book_id + page number for traceability
   section_ids: Set[str]=field(default_factory=set) # Set of section_ids that this page contains (for multi-section pages)
   book_id: str=None                                # Book ID this page belongs to
   pdf_page_number: int=None                        # Page number in the PDF (1-based)
   real_page_number: Optional[int] = None           # Optional real page number if available (e.g. from page text)
   text: str=None                                   # Full text of the page
   word_count: int=0                                # Total word count of the page text
   has_chapter: bool=False                          # Whether a chapter appears on a page
   has_section: bool=False                          # Whether a section appears on a page
   has_question: bool=False                         # Whether a question appears on a page
   has_answer: bool=False                           # Whether an answer appears on a page
   text_embedding: Optional[List[float]]=None       # Optional text embedding for the page (e.g. from a language model)

""" -------------------------------------------------------------------------------------------------------- """
"""
Convert dataclass objects to JSON-serializable format, handling sets and nested dataclasses.
Args:
   obj - The object to convert (can be a dataclass, dict, list, set, or primitive type)
Returns:
   A JSON-serializable version of the object (e.g. sets converted to sorted lists, dataclasses converted to dicts)
"""
def to_jsonable(obj):
   if is_dataclass(obj):
      obj = asdict(obj)
   if isinstance(obj, dict):
      return {k: to_jsonable(v) for k, v in obj.items()}
   if isinstance(obj, list):
      return [to_jsonable(v) for v in obj]
   if isinstance(obj, set):
      return sorted(obj)
   return obj

""" -------------------------------------------------------------------------------------------------------- """
"""
PDF to JSONL conversion using PyMuPDF page with improved gap detection.
Args:
   page - PyMuPDF page object
Returns:
   PageRecord object
"""
def words_to_text(
      pymu: str,
      book_id: str='',
) -> PageRecord:
   words = pymu.get_text("words") or []
   if not words:
      return PageRecord(
         id=IDFactory.page_id(book_id, pymu.number + 1),
         book_id=book_id,
         pdf_page_number=pymu.number + 1,
         text='',
         word_count=0
      )
   
   # Sort top to bottom, then left to right
   words.sort(key=lambda w: (w[5], w[6], w[1], w[0]))
   
   lines = []
   current_line = []
   prev = None
   
   for w in words:
      x0, y0, x1, y1, text, block_no, line_no, word_no = w
      
      if prev is None:
         current_line = [text]
         prev = w
         continue
      
      # New line if block or line number changes
      if (block_no, line_no) != (prev[5], prev[6]):
         lines.append(' '.join(current_line))
         current_line = [text]
         prev = w
         continue
      
      # Same line: use a FIXED gap threshold instead of proportion-based
      prev_x1 = prev[2]
      gap = x0 - prev_x1
      
      # Use a very low threshold - gaps between real words are ~2.2-3.0,
      # gaps between separate sections are negative (column jumps)
      # Use 2.0 to force separation at most gaps
      if gap >= 2.0:
         current_line.append(text)
      else:
         current_line[-1] = current_line[-1] + text
      
      prev = w
   
   if current_line:
      lines.append(' '.join(current_line))
   
   text = '\n'.join(lines)

   return PageRecord(
      id=IDFactory.page_id(book_id, pymu.number + 1),
      book_id=book_id,
      pdf_page_number=pymu.number + 1,
      text=text,
      word_count=len(words),
      has_chapter=has_chapter(text),
      has_section=has_section(text),
      has_question=has_question(text),
      has_answer=has_answer(text)
   )

""" -------------------------------------------------------------------------------------------------------- """
"""
Identify section boundaries based on page text and simple heuristics.
Args:
   page - PageRecord object
   curr_idx - Current page index in the overall document (0-based)
Returns:
   Set of section keys
"""
def group_sections_per_page(page: PageRecord) -> Set[str]:
   text_lower = page.text.lower()
   section_ids: Set[str] = set()

   # Simple heuristics
   if "practice exercises" in text_lower:
      section_key = "practice exercises"
      section_ids.add(IDFactory.section_id(page.book_id, section_key))

   if "exercise solutions" in text_lower:
      section_key = "exercise solutions"
      section_ids.add(IDFactory.section_id(page.book_id, section_key))

   return section_ids

""" -------------------------------------------------------------------------------------------------------- """
"""
Converts the PDF to JSONL format, one page per line. PageRecords and DocumentRecord stored as two
separate JSONL files in a new directory
Returns:
   Tuple of (DocumentRecord ID, output path)
"""
def convert_pdf(pdf_path: Path) -> Tuple[str, Path]:
   # Setup
   root = Path(__file__).parent
   out_dir = input("Enter desired output folder name: ").strip()
   output_dir = root / 'converted' / Path(out_dir)
   output_dir.mkdir(exist_ok=True)

   # Initialize logging
   log_file = root / "converted" / "conversion_logs.jsonl"
   logger = ConversionLogger(log_file)

   # Initialize book record
   book = DocumentRecord(title=pdf_path.stem)
   book_key = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(pdf_path)))
   book_id = IDFactory.book_id(book_key)
   book.source_pdf = str(pdf_path)

   # Check if already logged
   if not logger.get_entry(pdf_name):
      log_new_pdf(logger, pdf_path, book_id)

   print(f"{'=' * 70}\n")
   print(f"Converting PDF to JSONL...\n")

   page_count = 0

   t0 = time.perf_counter()
   last_print_time = t0
   DRAW_EVERY_SEC = 0.25  # Print progress every 0.25 seconds
   BAR_WIDTH = 15

   def draw_progress(done: int, total: int, elapsed: float):
      rate = done / elapsed if elapsed > 0 else 0.0
      remaining = (total - done) / rate if rate > 0 else float("inf")

      frac = done / total if total else 0.0
      filled = int(frac * BAR_WIDTH)
      bar = "█" * filled + "░" * (BAR_WIDTH - filled)

      eta_str = "∞" if remaining == float("inf") else f"{remaining:6.1f}s"
      line = (
         f"\r[{bar}] {done:4d}/{total}  "
         f"elapsed {elapsed:6.1f}s  "
         f"eta {eta_str}  "
         f"{rate:5.2f} pages/s"
      )
      print(line, end="", flush=True)

   # Read PDF
   page_out_dir = output_dir / Path(out_dir + '_PageRecords')
   with fitz.open(pdf_path) as pdf:
      with open(page_out_dir, 'w', encoding='utf-8') as outf:
         for page_idx in range(len(pdf)):

            # 1) Build PageRecord object
            page = words_to_text(pdf[page_idx], book_id=book.id)

            # 2) Add page.id to book.page_ids
            book.page_ids.add(page.id)

            # 3) Add section_ids to page record based on heuristics
            sections = group_sections_per_page(page)
            page.section_ids = {s for s in sections if s is not None}

            # 4) Dump PageRecord to DocumentRecord JSONL file
            d = to_jsonable(page)
            outf.write(json.dumps(d, ensure_ascii=False) + '\n')
            
            # 5) Update num_pages and num_words in book record as we go
            page_count += 1
            book.num_words += page.word_count
            book.num_pages = page_count

            # 6) Update remaining book metadata
            book.section_ids.update(page.section_ids)
            book.page_ids.add(page.id)
            book.num_sections = len(book.section_ids)  # Count unique non-empty sections
            book.num_questions = 0     # TODO: Update with actual question count
            book.num_answers = 0       # TODO: Update with actual answer count
            book.references = []       # TODO: Update with actual references
            book.related_readings = [] # TODO: Update with actual related readings
            
            now = time.perf_counter()
            if now - last_print_time >= DRAW_EVERY_SEC:
               draw_progress(page_count, len(pdf), now - t0)
               last_print_time = now

            book.num_pages = page_count


   book.output_jsonl_path = str(output_dir)
   
   # Write DocumentRecord to same directory
   book_out_file = output_dir / Path(out_dir + '_DocumentRecord')
   with open(book_out_file, 'w', encoding='utf-8') as outf:
      outf.write(json.dumps(to_jsonable(book), indent=2, ensure_ascii=False, sort_keys=True))

   # Print closing message
   print(f"\n\n{'=' * 70}")
   print(f"\nParsing complete")
   print(f"  Pages processed: {page_count}")
   print(f"  Page file: {page_out_dir}")
   print(f"  Document file: {book_out_file}")
   print(f"  Page file size: {Path(page_out_dir).stat().st_size / (1024*1024):.2f} MB")
   print(f"  Document file size: {Path(book_out_file).stat().st_size / (1024*1024):.2f} MB")
   print(f"  Total words: {book.num_words:,}")
   print(f"  Avg. words per page: {book.num_words / page_count:.0f} words/page")

   log_completed_conversion(
      logger,
      pdf_name,
      str(output_dir),
      page_count=book.num_pages,
      word_count=book.num_words
   )
    
   return (book.id, output_dir)

if __name__ == "__main__":
   convert_pdf()
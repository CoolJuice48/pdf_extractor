#!/usr/bin/env python3
import json
import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple
from difflib import SequenceMatcher
from word2number import w2n
from dataclasses import dataclass

""" -------------------------------------------------------------------------------------------------------- """

NUM_RE = re.compile(r"\d+")

""" -------------------------------------------------------------------------------------------------------- """
"""
Helper functions
"""
def normalize(s: str) -> str:
   s = s.lower()
   s = re.sub(r"[^a-z0-9\s]", " ", s)     # kill punctuation
   s = re.sub(r"\s+", " ", s).strip()    # collapse spaces
   return s

def token_set_score(a: str, b: str) -> float:
   # order-independent overlap + partial tolerance
   ta = set(normalize(a).split())
   tb = set(normalize(b).split())
   if not ta or not tb:
      return 0.0
   overlap = len(ta & tb)
   return overlap / max(len(ta), len(tb))

def seq_score(a: str, b: str) -> float:
   # typo-tolerant string similarity
   return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

def is_int(s: str) -> bool:
   try:
      int(s)
      return True
   except ValueError:
      return False
   
def clean(s: str) -> str:
   return (re.sub(r'[^\w\s]', '', s))
""" -------------------------------------------------------------------------------------------------------- """
"""
Option class
"""
@dataclass(frozen=True)
class Option:
   number: int
   label: str
   label1: str=None

""" -------------------------------------------------------------------------------------------------------- """
"""
Option selector
Returns:

"""
def select_option(user_input: str, options: List[Option]) -> Tuple[Optional[Option], str]:
   s = user_input.strip()
   if not s:
      return None, "empty input"

   # 1) numeric fast-path: accept 3, 3., 3), #3, etc.
   m = NUM_RE.search(s)
   if m:
      n = int(m.group())
      for opt in options:
         if opt.number == n:
               return opt, "matched by number"
      # if they typed a number that isn't an option
      return None, f"number {n} not in options"

   # 2) fuzzy match by label
   best = None
   best_score = -1.0

   for opt in options:
      # combine two scores:
      # - token overlap (handles missing words / pluralization-ish / word order)
      # - sequence similarity (handles typos)
      score = max(token_set_score(s, opt.label), seq_score(s, opt.label))
      if score > best_score:
         best_score = score
         best = opt

   # threshold tuning: start conservative
   if best and best_score >= 0.55:
      return best, f"matched by text (score={best_score:.2f})"

   return None, f"no confident match (best={best_score:.2f})"
""" -------------------------------------------------------------------------------------------------------- """
"""
Print a list of Options
"""
def print_options(options: List[Option]) -> None:
   for opt in options:
      print(f"{opt.number}.) {opt.label}")
   print("\n")
""" -------------------------------------------------------------------------------------------------------- """
"""
Convert input to int corresponding to Option number
"""
def read_user_choice() -> int:
   opt = clean(input("  >> "))
   opt = select_option(opt)
   return opt
""" -------------------------------------------------------------------------------------------------------- """
"""

"""
def load_pages() -> dict:
   """Load all pages into memory."""
   pages = {}
   
   with open(, 'r', encoding='utf-8') as f:
      for line in f:
         obj = json.loads(line)
         pages[obj['page_number']] = obj['text']
   
   return pages

def search(pages: dict, keyword: str, context: int = 200) -> list:
   """Search for keyword in all pages."""
   keyword_lower = keyword.lower()
   results = []
   
   for page_num, text in sorted(pages.items()):
      if keyword_lower in text.lower():
         # Find all occurrences
         text_lower = text.lower()
         start = 0
         while True:
               idx = text_lower.find(keyword_lower, start)
               if idx == -1:
                  break
               
               # Get context
               ctx_start = max(0, idx - context)
               ctx_end = min(len(text), idx + len(keyword) + context)
               context_str = text[ctx_start:ctx_end]
               
               results.append({
                  'page': page_num,
                  'index': idx,
                  'context': context_str
               })
               
               start = idx + 1
   
   return results

def show_page(pages: dict, page_num: int, length=None) -> None:
   """Show a specific page."""
   if page_num not in pages:
      print(f"Error: Page {page_num} not found")
      return
   
   text = pages[page_num]
   if length:
      text = text[:length]
   
   print(f"Page {page_num}:")
   print(text)

def extract_range(pages: dict, start_page: int, end_page: int, output_file: str) -> None:
   """Extract pages to file."""
   with open(output_file, 'w', encoding='utf-8') as f:
      for page_num in range(start_page, end_page + 1):
         if page_num in pages:
               f.write(f"=== PAGE {page_num} ===\n")
               f.write(pages[page_num])
               f.write("\n\n")
   
   print(f"Extracted pages {start_page}-{end_page} to {output_file}")

def show_stats(pages: dict) -> None:
   """Show statistics."""
   total_chars = sum(len(text) for text in pages.values())
   total_pages = len(pages)
   avg_chars = total_chars / total_pages if total_pages > 0 else 0
   
   print(f"Statistics:")
   print(f"  Total pages: {total_pages}")
   print(f"  Total characters: {total_chars:,}")
   print(f"  Average chars/page: {avg_chars:.0f}")
   print(f"  File: {JSONL_FILE}")
   print(f"  File size: {Path(JSONL_FILE).stat().st_size / (1024*1024):.2f} MB")

def print_help():
   """Print help message."""
   print(f"{'=' * 70}\n")
   print(f">----= PDF Query Tool for file: {JSONL_FILE.stem + '.jsonl'} =----<")
   print("\nUsage:")
   print("  search <keyword>             - Search for keyword")
   print("  page <number>                - Show full page")
   print("  show <number>                - Show first 2000 chars of page")
   print("  range <start> <end>          - Show page range")
   print("  extract <start> <end> <file> - Extract pages to file")
   print("  stats                        - Show statistics")
   print("  help                         - Show this help message")
   print("  quit                         - Exit the program")
   print(f"\n{'=' * 70}")
""" -------------------------------------------------------------------------------------------------------- """
"""
Options on program startup
"""
def print_initial_directory():
   # Formatting
   top_spacing = "\n\n"
   top_border = (f"{'=' * 70}\n")
   top_text = "Where to you want to go?"
   bottom_border = (f"\n{'=' * 70}")
   bottom_spacing = "\n"

   # Options
   options = [
      Option(1, "Raw PDFs"),
      Option(2, "Converted PDFs")
   ]

   # Printing
   print(top_spacing)
   print(top_text)
   print(top_border) if top_border else None
   print_options(options)
   print(bottom_border) if bottom_border else None
   print(bottom_spacing)

""" -------------------------------------------------------------------------------------------------------- """
"""
Options for raw pdfs
"""
def print_pdf_list(pdfs: Path):
   # Formatting
   top_spacing = "\n\n"
   top_border = (f"{'=' * 70}\n")
   top_text = "Choose a PDF:"
   bottom_border = (f"\n{'=' * 70}")
   bottom_spacing = "\n"

   # Options
   options = []
   for i, pdf in enumerate(pdfs, start=1):
      size_mb = pdf.stat().st_size / (1024 * 1024)
      options.append(Option(i, pdf.name, size_mb))

   # Printing
   print(top_spacing)
   print(top_text)
   print(top_border) if top_border else None
   print_options(options)
   print(bottom_border) if bottom_border else None
   print(bottom_spacing)
""" -------------------------------------------------------------------------------------------------------- """
"""
Actions on a PDF
"""
def print_pdf_actions(file_name: str):
   # Formatting
   top_spacing = "\n\n"
   top_border = (f"{'=' * 70}\n")
   top_text = f"""\nFile {file_name} selected
                    What do you want to do?"""
   bottom_border = (f"\n{'=' * 70}")
   bottom_spacing = "\n"

   # Options
   options = [
      Option(1, "Convert to JSONL"),
      Option(2, "Extract questions and answers")
      Option(3, "Go back"),
      Option(0, "Search for ... TODO")
   ]

   # Printing
   print(top_spacing)
   print(top_text)
   print(top_border) if top_border else None
   print_options(options)
   print(bottom_border) if bottom_border else None
   print(bottom_spacing)


""" Main command dispatcher. """
def read_command_line(input_files: List[Path]=None, output_files: List[Path]=None) -> None:
   # Welcome message
   print(f"{'=' * 70}\n")
   print("Welcome!")
   
   # Choose stored 
   if input_files:
      while True:
         # Choose raw PDFs or previously converted
         print_initial_directory()
         choice = read_user_choice()

         # Select raw PDFs
         if choice == 1:
            # List stored PDFs
            print_pdf_list(pdfs=input_files)
            pdf_idx = read_user_choice()

            # Path(s) to input PDFs
            file_path = input_files[pdf_idx]
            file_name = input_files[pdf_idx].stem
            
            # List actions to take on PDF
            print_pdf_actions(file_name=file_name)
            action = read_user_choice()

            # 1) Convert PDF to JSONL
            if action == 1:
               converted_id, converted_path = convert_pdf(file_path)
            
            # 2) Extract questions and answers from converted PDF (alternate route)
            if action == 2:
               from qa_handler import parse_document_pages
               book_id = file_path.__getattribute__("id")
               jsonl_path = file_path.__getattribute__("source_pdf")
               parse_document_pages(jsonl_path=jsonl_path, book_id=book_id)

            # 3) Return to menu
            if choice is 3:
               pass

   else:
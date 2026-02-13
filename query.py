#!/usr/bin/env python3
"""
Query interface for managing PDF conversions and Q&A extraction.
Uses conversion logging to track which PDFs have been processed.
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

from conversion_logger import ConversionLogger, log_new_pdf, log_completed_conversion

""" -------------------------------------------------------------------------------------------------------- """
""" Helper functions """

def normalize(s: str) -> str:
   s = s.lower()
   s = re.sub(r"[^a-z0-9\s]", " ", s)
   s = re.sub(r"\s+", " ", s).strip()
   return s

def is_int(s: str) -> bool:
   try:
      int(s)
      return True
   except ValueError:
      return False

def clean(s: str) -> str:
   return re.sub(r'[^\w\s]', '', s)

def toalnum(s: str) -> str:
   return re.sub(r'[^A-Za-z0-9]', '', s)

""" -------------------------------------------------------------------------------------------------------- """
""" Option class """

@dataclass(frozen=True)
class Option:
   number: int
   label: str
   extra: str = ""  # Extra info to display

""" -------------------------------------------------------------------------------------------------------- """
""" Option selector """

def select_option(user_input: str, options: List[Option]) -> Tuple[Optional[Option], str]:
   s_clean = clean(user_input).strip()
   s_clean_lower = s_clean.lower()

   if not user_input:
      return None, "empty input"

   # Numeric fast-path
   m = toalnum(s_clean)
   if is_int(m):
      n = int(m)
      for opt in options:
         if opt.number == n:
               return opt, "matched by number"
      return None, f"number {n} not in options"

   # Fuzzy match by label
   best = None
   best_score = -1.0

   for opt in options:
      lower = opt.label.lower()
      score = max(
         token_set_score(s_clean_lower, lower),
         seq_score(s_clean_lower, lower)
      )
      if score > best_score:
         best_score = score
         best = opt

   if best and best_score >= 0.55:
      return best, f"matched by text (score={best_score:.2f})"

   return None, f"no confident match (best={best_score:.2f})"

def token_set_score(a: str, b: str) -> float:
   ta = set(normalize(a).split())
   tb = set(normalize(b).split())
   if not ta or not tb:
      return 0.0
   overlap = len(ta & tb)
   return overlap / max(len(ta), len(tb))

def seq_score(a: str, b: str) -> float:
   return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

""" -------------------------------------------------------------------------------------------------------- """
""" Print and read options """

def print_options(options: List[Option]) -> None:
   for opt in options:
      if opt.extra:
         print(f"{opt.number}.) {opt.label} {opt.extra}")
      else:
         print(f"{opt.number}.) {opt.label}")

def read_user_choice(options: List[Option], prompt: str = "Choice >> ") -> Optional[Option]:
   while True:
      raw = input(prompt)
      
      if not raw.strip():
         return None
      
      opt, why = select_option(raw, options)

      if opt:
         return opt
      
      print(f"Invalid choice: {why}")

""" -------------------------------------------------------------------------------------------------------- """
""" PDF management """

def list_pdfs(pdf_dir: Path) -> List[Path]:
   """Get all PDFs in directory."""
   return sorted(pdf_dir.glob("*.pdf"))

def get_pdf_status(pdf_path: Path, logger: ConversionLogger) -> str:
   """Get status emoji for a PDF."""
   if logger.is_converted(pdf_path.stem):
      return "✅"
   elif logger.get_entry(pdf_path.stem):
      return "🔄"
   else:
      return "📄"

""" -------------------------------------------------------------------------------------------------------- """
""" Main menu """

def show_pdf_menu(pdf_dir: Path, converted_dir: Path, logger: ConversionLogger):
   """Show menu of available PDFs with conversion status."""
   
   pdfs = list_pdfs(pdf_dir)
   
   if not pdfs:
      print(f"\n⚠️  No PDFs found in {pdf_dir}")
      return
   
   # Build options list with status
   pdf_options = []
   for i, pdf_path in enumerate(pdfs, start=1):
      status = get_pdf_status(pdf_path, logger)
      size_mb = pdf_path.stat().st_size / (1024 * 1024)
      extra = f"[{size_mb:.1f} MB] {status}"
      
      pdf_options.append(Option(i, pdf_path.stem, extra))
   
   # Display PDFs
   print("\n" + "="*70)
   print("AVAILABLE PDFs")
   print("="*70)
   print("Status: 📄 = New | 🔄 = Logged | ✅ = Converted\n")
   print_options(pdf_options)
   print("\n0.) Go back")
   
   # Get selection
   choice_str = input("\nSelect PDF number >> ").strip()
   
   if not choice_str or choice_str == "0":
      return
   
   try:
      choice = int(choice_str)
      if choice < 1 or choice > len(pdfs):
         print("Invalid selection")
         return
   except ValueError:
      print("Please enter a number")
      return
   
   # Get selected PDF
   selected_pdf = pdfs[choice - 1]
   
   # Show actions menu
   show_pdf_actions(selected_pdf, converted_dir, logger)

def show_pdf_actions(pdf_path: Path, converted_dir: Path, logger: ConversionLogger):
   """Show available actions for a selected PDF."""
   
   pdf_name = pdf_path.stem
   is_converted = logger.is_converted(pdf_name)
   
   print(f"\n{'='*70}")
   print(f"SELECTED: {pdf_name}")
   print(f"{'='*70}")
   
   # Check status
   entry = logger.get_entry(pdf_name)
   if entry:
      print(f"Status: {'✅ Converted' if entry.converted else '🔄 Logged, not converted'}")
      if entry.converted:
         print(f"Output: {entry.output_path}")
         print(f"Pages: {entry.page_count}")
         print(f"Words: {entry.word_count:,}")
   else:
      print(f"Status: 📄 New (not in log)")
   
   print()
   
   # Build action options
   actions = []
   
   if not is_converted:
      actions.append(Option(1, "Convert to JSONL"))
   else:
      actions.append(Option(1, "Re-convert (overwrite)"))
   
   if is_converted:
      actions.append(Option(2, "Extract Q&A"))
      actions.append(Option(3, "View conversion details"))
   
   actions.append(Option(0, "Go back"))
   
   print("Available actions:\n")
   print_options(actions)
   
   # Get action
   action_str = input("\nAction >> ").strip()
   
   if not action_str or action_str == "0":
      return
   
   try:
      action = int(action_str)
   except ValueError:
      print("Please enter a number")
      return
   
   # Execute action
   if action == 1:
      # Convert PDF
      print(f"\nConverting {pdf_name}...")
      
      # If not in log yet, add it
      if not entry:
         from id_factory import IDFactory
         doc_id = IDFactory.book_id(pdf_name)
         log_new_pdf(logger, pdf_path, doc_id)
      
      # Run conversion
      from pdf_to_jsonl import convert_pdf
      doc_id, output_path = convert_pdf(pdf_path)
      
      # Update log (conversion function should do this, but as fallback)
      # logger.mark_as_converted(pdf_name, str(output_path), ...)
      
   elif action == 2 and is_converted:
      # Extract Q&A
      print(f"\nExtracting Q&A from {pdf_name}...")
      
      from llm_qa_extractor import extract_qa_from_jsonl
      
      # Get paths from log entry
      pages_file = Path(entry.output_path) / f"{pdf_name}_PageRecords"
      output_file = Path("qas") / f"{pdf_name}_bank.json"
      output_file.parent.mkdir(exist_ok=True)
      
      extract_qa_from_jsonl(
         str(pages_file),
         str(output_file),
         pdf_name
      )
      
      # Update log with question count
      # TODO: Get question count from extraction
      
   elif action == 3 and is_converted:
      # Show details
      print(f"\n{'='*70}")
      print(f"CONVERSION DETAILS: {pdf_name}")
      print(f"{'='*70}")
      print(f"Document ID: {entry.document_id}")
      print(f"Source PDF: {entry.document_file}")
      print(f"Output: {entry.output_path}")
      print(f"Pages: {entry.page_count}")
      print(f"Words: {entry.word_count:,}")
      print(f"Questions: {entry.question_count or 'Not extracted'}")
      print()
      input("Press Enter to continue...")

def show_converted_menu(logger: ConversionLogger):
   """Show menu of converted PDFs."""
   
   converted = logger.get_all_converted()
   
   if not converted:
      print("\n⚠️  No converted PDFs found")
      input("Press Enter to continue...")
      return
   
   print(f"\n{'='*70}")
   print("CONVERTED PDFs")
   print(f"{'='*70}\n")
   
   options = []
   for i, entry in enumerate(converted, start=1):
      extra = f"({entry.page_count} pages, {entry.word_count:,} words)"
      options.append(Option(i, entry.document_title, extra))
   
   print_options(options)
   print("\n0.) Go back")
   
   # Get selection
   choice_str = input("\nSelect PDF >> ").strip()
   
   if not choice_str or choice_str == "0":
      return
   
   # TODO: Show actions for converted PDF

""" -------------------------------------------------------------------------------------------------------- """
""" Main entry point """

def main():
   """Main CLI entry point."""
   
   # Setup paths
   root = Path(__file__).parent
   pdf_dir = root / "pdfs"
   converted_dir = root / "converted"
   
   pdf_dir.mkdir(exist_ok=True)
   converted_dir.mkdir(exist_ok=True)
   
   # Initialize logger
   log_file = converted_dir / "conversion_logs.jsonl"
   logger = ConversionLogger(log_file)
   
   # Main menu loop
   while True:
      print("\n" + "="*70)
      print("ATRIUM PDF PROCESSOR")
      print("="*70)
      
      # Count stats
      all_pdfs = list_pdfs(pdf_dir)
      converted_count = len(logger.get_all_converted())
      
      print(f"\nPDFs available: {len(all_pdfs)}")
      print(f"PDFs converted: {converted_count}")
      
      # Main options
      main_options = [
         Option(1, "Browse all PDFs"),
         Option(2, "View converted PDFs"),
         Option(3, "Quit")
      ]
      
      print()
      print_options(main_options)
      
      choice_str = input("\nChoice >> ").strip()
      
      if not choice_str:
         continue
      
      try:
         choice = int(choice_str)
      except ValueError:
         print("Please enter a number")
         continue
      
      if choice == 1:
         show_pdf_menu(pdf_dir, converted_dir, logger)
      elif choice == 2:
         show_converted_menu(logger)
      elif choice == 3:
         print("\n👋 Goodbye!")
         break

if __name__ == "__main__":
   main()
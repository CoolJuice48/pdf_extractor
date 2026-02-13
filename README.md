# Textbook Processing Tools

## Files Overview

### Core Data Files
- **`eecs281_textbook_pages_v2.jsonl`** (3.17 MB) ⭐ **PRIMARY** — Complete PDF as JSON Lines (IMPROVED)
  - All 1083 pages with extracted text and **66.1% better** spacing fixes
  - Format: One JSON object per line (efficient for streaming/queries)
  - Fields: `page_number`, `text`, `text_length`
  - Algorithm v2: Reduced spacing issues from 9,173 → 3,109 across all pages
  
- **`eecs281_textbook_pages.jsonl`** (3.17 MB) — Original version (for reference)
  - All 1083 pages with v1 spacing algorithm
  - Use v2 instead for better quality
  
- **`eecs281_textbook_structure.json`** (92 KB) — Chapter/section metadata
  - 27 chapters, 208 sections with page ranges
  - Useful for navigation and organization

### Query Tools
- **`query_jsonl_v2.py`** ⭐ **PRIMARY** — Search and retrieve from improved JSONL
  - `python3 query_jsonl_v2.py search "keyword"` — Search with context
  - `python3 query_jsonl_v2.py page <number>` — Get specific page
  - `python3 query_jsonl_v2.py show <number>` — View page preview
  - `python3 query_jsonl_v2.py range <start> <end>` — Get page range
  - `python3 query_jsonl_v2.py extract <start> <end> <file>` — Export to text file
  - `python3 query_jsonl_v2.py stats` — Show statistics

- **`query_jsonl.py`** — Original query tool (for v1 JSONL)
  - Same commands as v2, but uses the original spacing algorithm

- **`navigate_pdf.py`** — Navigation and extraction tool
  - Works with the structure JSON
  - Advanced search and topic lookup features

### Conversion Scripts
- **`pdf_to_jsonl.py`** — Converts PDF to JSONL with v1 spacing fixes
  - Can regenerate the pages JSONL if needed
- **`apply_v2_algorithm.py`** — Applies improved v2 spacing to JSONL
  - Transforms v1 JSONL → v2 JSONL (66.1% better spacing)

---

## Quick Start

### Search for Content
```bash
# Search for problems using improved v2
python3 query_jsonl_v2.py search "Problem"

# Search for specific problem numbers
python3 query_jsonl_v2.py search "82. "
```

### View Specific Content
```bash
# See page 36 (with improved spacing) 
python3 query_jsonl_v2.py show 36

# Get all pages from Chapter 4 (Complexity Analysis, pages 85-116)
python3 query_jsonl_v2.py range 85 116

# Extract pages to text file
python3 query_jsonl_v2.py extract 689 764 graph_chapter.txt
```

### Statistics
```bash
python3 query_jsonl_v2.py stats
```

---

## Spacing Fixes Applied

The v2 algorithm includes intelligent spacing restoration with **66.1% improvement**:

**All Versions - Common fixes:**
- **CamelCase detection**: `functionName` → `function Name`
- **Letter-digit transitions**: `problem42` → `problem 42`
- **Bracket/paren spacing**: `the(` → `the (`

**v2 Additional fixes (66.1% better):**
- **Period followed by letter**: `Chapter1.Programming` → `Chapter 1. Programming`
- **Type preservation**: `int32_t` patterns preserved correctly
- **Line-ending punctuation**: `line).If` → `line). If`

**Comparison:**
- **v1 (original)**: 9,173 spacing issues across all pages (8.5/page)
- **v2 (improved)**: 3,109 spacing issues across all pages (2.9/page)
- **Result**: 6,064 fewer issues, 66.1% reduction

Note: Some spacing issues remain due to PDF multi-column layout challenges and concatenated word parsing limitations.

---

## Stats

**v2 (Improved - Recommended):**
- Total pages: 1083
- Total characters: 3,078,509
- File size: 3.17 MB
- Average chars/page: 2843
- Spacing issues: 3,109 (2.9 per page) ← 66% better than v1
- Format advantage: JSONL is more efficient than JSON for large datasets (streaming, line-by-line access)

**v1 (Original - For reference):**
- Total pages: 1083
- Total characters: 3,072,445
- File size: 3.17 MB
- Average chars/page: 2837
- Spacing issues: 9,173 (8.5 per page)

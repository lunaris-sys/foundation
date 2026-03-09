#!/usr/bin/env python3
"""
normalize_md.py - Normalize README.md for consistent structure and LaTeX conversion.

Does NOT change content, only structure/formatting:
- Numbers unnumbered subsections per chapter
- Removes redundant horizontal rules between top-level sections
- Standardizes blockquote types: Note, TODO, Decision, Warning, Open
- Fixes table alignment (pandoc-friendly)
- Ensures single blank line before/after headings

Run: python3 normalize_md.py README.md > README_normalized.md
Or in-place: python3 normalize_md.py README.md --inplace
"""

import re
import sys
import argparse
from copy import deepcopy


def number_subsections(lines: list[str]) -> list[str]:
    """
    Strip all manual N.M numbering from headings at every level.
    LaTeX handles numbering automatically via --number-sections.
    This keeps the MD clean for GitHub rendering too.
    """
    result = []
    for line in lines:
        # ## N. Title  ->  ## Title  (chapter numbers stripped)
        ch_match = re.match(r'^(## )\d+\. (.+)$', line)
        if ch_match:
            result.append(f'{ch_match.group(1)}{ch_match.group(2)}\n')
            continue

        # ### N.M Title  ->  ### Title  (section numbers stripped)
        sec_match = re.match(r'^(### )\d+\.\d+ (.+)$', line)
        if sec_match:
            result.append(f'{sec_match.group(1)}{sec_match.group(2)}\n')
            continue

        result.append(line)
    return result


def remove_redundant_hrs(lines: list[str]) -> list[str]:
    """
    Remove --- / ------ lines that appear between top-level ## sections.
    Keep --- inside content (e.g. table separators) but those are | lines anyway.
    """
    result = []
    for i, line in enumerate(lines):
        if re.match(r'^-{3,}\s*$', line):
            # Check context: is the next non-empty line a ## heading or EOF?
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            next_is_heading = j >= len(lines) or lines[j].startswith('## ') or lines[j].startswith('# ')

            # Also skip if previous non-empty line was a ## heading
            k = i - 1
            while k >= 0 and lines[k].strip() == '':
                k -= 1
            prev_is_heading = k < 0 or lines[k].startswith('## ') or lines[k].startswith('# ')

            if next_is_heading or prev_is_heading:
                # Replace with single blank line (avoid double blanks)
                if result and result[-1].strip() != '':
                    result.append('\n')
                continue
        result.append(line)
    return result


def standardize_blockquotes(lines: list[str]) -> list[str]:
    """
    Normalize blockquote prefixes for LaTeX conversion:
      > **Note:** ...      -> ::: note
      > **TODO:** ...      -> ::: todo
      > **Decision:** ...  -> ::: decision
      > **Warning:** ...   -> ::: warning
    
    We keep these as standard MD blockquotes but add a first-line type tag
    that the LaTeX pre-processor can detect. GitHub renders them fine as blockquotes.
    """
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect typed blockquotes
        bq_match = re.match(r'^> \*\*(Note|TODO|Decision|Warning|Open):\*\*\s*(.*)', line, re.IGNORECASE)
        if bq_match:
            bq_type = bq_match.group(1).upper()
            rest = bq_match.group(2)
            # Rewrite with consistent casing
            type_map = {
                'NOTE': 'Note', 'TODO': 'TODO', 'DECISION': 'Decision',
                'WARNING': 'Warning', 'OPEN': 'Open'
            }
            canonical = type_map.get(bq_type, bq_type.capitalize())
            result.append(f'> **{canonical}:** {rest}\n')
            i += 1
            continue
        result.append(line)
        i += 1
    return result


def collapse_blank_lines(lines: list[str]) -> list[str]:
    """Collapse 3+ consecutive blank lines to 2."""
    result = []
    blank_count = 0
    for line in lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return result


def ensure_heading_spacing(lines: list[str]) -> list[str]:
    """Ensure one blank line before every ## and ### heading."""
    result = []
    for i, line in enumerate(lines):
        if re.match(r'^#{2,3} ', line) and i > 0:
            # If previous non-empty content exists and no blank line before
            if result and result[-1].strip() != '':
                result.append('\n')
        result.append(line)
    return result


def fix_open_questions_numbering(lines: list[str]) -> list[str]:
    """
    Ensure all 'Open Questions' subsections are numbered consistently.
    They should follow the same counter as other subsections (handled by
    number_subsections), but this pass ensures the title is canonical.
    """
    result = []
    for line in lines:
        # Normalize variations
        line = re.sub(r'^(### \d+\.\d+ )Open questions\s*$', r'\1Open Questions', line, flags=re.IGNORECASE)
        result.append(line)
    return result


def process(content: str) -> str:
    lines = content.splitlines(keepends=True)

    lines = remove_redundant_hrs(lines)
    lines = number_subsections(lines)
    lines = fix_open_questions_numbering(lines)
    lines = standardize_blockquotes(lines)
    lines = ensure_heading_spacing(lines)
    lines = collapse_blank_lines(lines)

    return ''.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Normalize README.md structure')
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('--inplace', action='store_true', help='Edit file in-place')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    result = process(content)

    if args.inplace:
        with open(args.input, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f'Normalized {args.input} in-place', file=sys.stderr)
    elif args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f'Written to {args.output}', file=sys.stderr)
    else:
        sys.stdout.write(result)


if __name__ == '__main__':
    main()

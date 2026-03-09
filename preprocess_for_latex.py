#!/usr/bin/env python3
"""
preprocess_for_latex.py - Transform MD for LaTeX conversion.

Handles things pandoc cannot do natively:
1. Renders mermaid code blocks to PNG via mmdc, replaces with figure
2. Converts typed blockquotes (> **Note:** etc.) to LaTeX box environments
3. Strips the hand-written Table of Contents (pandoc generates its own)
4. Strips the Abstract section header (becomes part of frontmatter)
5. Replaces mermaid blocks that fail to render with a labeled placeholder

Usage:
  python3 preprocess_for_latex.py input.md output.md --diagram-dir ./diagrams
"""

import re
import sys
import os
import subprocess
import hashlib
import argparse
from pathlib import Path


# ── Mermaid ───────────────────────────────────────────────────────────────────

def render_mermaid(code: str, output_path: Path, mmdc: str = 'mmdc') -> bool:
    """Render a mermaid diagram to PNG. Returns True on success."""
    input_tmp = output_path.with_suffix('.mmd')
    try:
        input_tmp.write_text(code, encoding='utf-8')
        result = subprocess.run(
            [mmdc, '-i', str(input_tmp), '-o', str(output_path),
             '--backgroundColor', 'transparent',
             '--width', '900'],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0 and output_path.exists()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    finally:
        if input_tmp.exists():
            input_tmp.unlink()


def process_mermaid_blocks(content: str, diagram_dir: Path, mmdc: str = 'mmdc') -> str:
    """Replace ```mermaid blocks with LaTeX figure references."""
    diagram_dir.mkdir(parents=True, exist_ok=True)
    counter = [0]

    def replace_block(m: re.Match) -> str:
        code = m.group(1).strip()
        counter[0] += 1

        # Stable filename based on content hash
        digest = hashlib.md5(code.encode()).hexdigest()[:8]
        filename = f'diagram_{counter[0]:02d}_{digest}.png'
        output_path = diagram_dir / filename

        # Extract a caption from the first comment or flowchart declaration
        caption = extract_mermaid_caption(code, counter[0])

        if not output_path.exists():
            success = render_mermaid(code, output_path, mmdc)
        else:
            success = True  # cached

        if success:
            # Return a pandoc-compatible figure reference
            rel_path = output_path.name
            return f'\n![{caption}](diagrams/{rel_path}){{width=100%}}\n'
        else:
            # Placeholder - won't break the build
            return (
                f'\n> **Note:** *[Diagram {counter[0]}: {caption} — '
                f'render failed, see source]*\n'
            )

    return re.sub(
        r'```mermaid\n(.*?)```',
        replace_block,
        content,
        flags=re.DOTALL
    )


def extract_mermaid_caption(code: str, n: int) -> str:
    """Try to extract a meaningful caption from mermaid source."""
    # First line often has the diagram type
    first = code.strip().split('\n')[0].strip()
    type_map = {
        'flowchart': 'Flow Diagram',
        'graph': 'Graph Diagram',
        'sequenceDiagram': 'Sequence Diagram',
        'classDiagram': 'Class Diagram',
        'erDiagram': 'Entity-Relationship Diagram',
        'block-beta': 'Architecture Overview',
    }
    for key, label in type_map.items():
        if first.lower().startswith(key.lower()):
            return f'{label} {n}'
    return f'Diagram {n}'


# ── Typed Blockquotes → LaTeX environments ────────────────────────────────────

BLOCKQUOTE_TYPES = {
    'note':     ('notebox',     'Note'),
    'todo':     ('todobox',     'TODO'),
    'decision': ('decisionbox', 'Decision'),
    'warning':  ('warningbox',  'Warning'),
    'open':     ('notebox',     'Open'),  # Open Questions notes
}

def process_typed_blockquotes(content: str) -> str:
    r"""
    Convert > **Type:** text blockquotes to pandoc div syntax,
    which pandoc will pass through to LaTeX as raw environments.

    Pandoc fenced divs: ::: {.notebox} ... :::
    These get converted to \begin{notebox}...\end{notebox} via --lua-filter.

    Actually, easier: we emit raw LaTeX directly for the tex target.
    We use pandoc's ```{=latex} raw blocks.
    """
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect start of typed blockquote
        bq_match = re.match(
            r'^> \*\*(Note|TODO|Decision|Warning|Open):\*\*\s*(.*)',
            line, re.IGNORECASE
        )
        if bq_match:
            bq_type = bq_match.group(1).lower()
            first_text = bq_match.group(2)
            env, label = BLOCKQUOTE_TYPES.get(bq_type, ('notebox', bq_type.capitalize()))

            # Collect continuation lines (> ...)
            block_lines = [first_text] if first_text else []
            i += 1
            while i < len(lines) and lines[i].startswith('> '):
                block_lines.append(lines[i][2:])  # strip '> '
                i += 1

            block_text = '\n'.join(block_lines).strip()

            # Emit as raw LaTeX block that pandoc passes through
            result.append('```{=latex}')
            result.append(f'\\begin{{{env}}}')
            result.append(f'\\textbf{{{label}:}} ')
            result.append('```')
            # The actual text goes through pandoc for proper formatting
            result.append(block_text)
            result.append('```{=latex}')
            result.append(f'\\end{{{env}}}')
            result.append('```')
            result.append('')
            continue

        result.append(line)
        i += 1

    return '\n'.join(result)


# ── Strip sections that pandoc handles ────────────────────────────────────────

def strip_manual_toc(content: str) -> str:
    """Remove the hand-written Table of Contents section."""
    # Remove from '## Table of Contents' to the next '## ' heading
    return re.sub(
        r'^## Table of Contents\n.*?(?=^## )',
        '',
        content,
        flags=re.MULTILINE | re.DOTALL
    )


def strip_abstract_heading(content: str) -> str:
    """
    Keep abstract content but remove the ## Abstract heading.
    pandoc will use it as a summary block or it just flows as intro text.
    """
    return re.sub(r'^## Abstract\n', '', content, flags=re.MULTILINE)


def fix_chapter_headings(content: str) -> str:
    r"""
    Convert ## N. Title to # N. Title so pandoc maps them to \chapter{}.
    In scrreprt, # = chapter, ## = section, ### = subsection.
    The MD uses ## for chapters and ### for sections which is one level off.
    """
    # ## N. Title -> # N. Title  (numbered chapters)
    content = re.sub(r'^## (\d+\. .+)$', r'# \1', content, flags=re.MULTILINE)
    # ## Abstract, ## Table of Contents etc -> # ...
    content = re.sub(r'^## (Abstract|Table of Contents|Appendix.*)$',
                     r'# \1', content, flags=re.MULTILINE)
    # ### N.M Title -> ## N.M Title  (sections)
    content = re.sub(r'^### (\d+\.\d+ .+)$', r'## \1', content, flags=re.MULTILINE)
    # ### unnumbered -> ## unnumbered
    content = re.sub(r'^### (.+)$', r'## \1', content, flags=re.MULTILINE)
    return content


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Pre-process MD for LaTeX conversion')
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('output', help='Output processed markdown file')
    parser.add_argument('--diagram-dir', default='./diagrams',
                        help='Directory to store rendered diagrams')
    parser.add_argument('--mmdc', default='mmdc',
                        help='Path to mmdc binary')
    parser.add_argument('--skip-mermaid', action='store_true',
                        help='Skip mermaid rendering (use placeholders)')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    diagram_dir = Path(args.diagram_dir)

    print('  Stripping manual TOC...', file=sys.stderr)
    content = strip_manual_toc(content)

    print('  Stripping Abstract heading...', file=sys.stderr)
    content = strip_abstract_heading(content)

    print('  Fixing heading levels...', file=sys.stderr)
    content = fix_chapter_headings(content)

    if not args.skip_mermaid:
        print('  Rendering Mermaid diagrams...', file=sys.stderr)
        content = process_mermaid_blocks(content, diagram_dir, args.mmdc)
    else:
        print('  Skipping Mermaid (--skip-mermaid)', file=sys.stderr)
        content = re.sub(
            r'```mermaid\n(.*?)```',
            lambda m: f'\n> **Note:** *[Diagram — see source]*\n',
            content, flags=re.DOTALL
        )

    print('  Processing typed blockquotes...', file=sys.stderr)
    content = process_typed_blockquotes(content)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'  Done → {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()

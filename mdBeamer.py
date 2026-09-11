#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import math
import shlex
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple

@dataclass
class Inline: pass
@dataclass
class Text(Inline): value: str
@dataclass
class Bold(Inline): children: List[Inline]
@dataclass
class Italic(Inline): children: List[Inline]
@dataclass
class Code(Inline): value: str
@dataclass
class Link(Inline): label: List[Inline]; url: str
@dataclass
class FootnoteRef(Inline): key: str
@dataclass
class FootnoteDefinition:
    text: str
    fontsize: Optional[str] = None

@dataclass
class Block: pass
@dataclass
class Heading(Block):
    level: int
    text: str
    attrs: dict = field(default_factory=dict)
    source_line: Optional[int] = None
@dataclass
class Paragraph(Block): lines: List[str]
@dataclass
class ImageBlock(Block):
    alt: str
    path: str
    width: Optional[str] = None
    height: Optional[str] = None
    column_side: Optional[str] = None
    column_width: Optional[str] = None
    column_valign: Optional[str] = None
@dataclass
class CodeBlock(Block):
    language: str
    content: str
    fontsize: Optional[str] = None
@dataclass
class ListItem:
    text: str
    children: List['Block'] = field(default_factory=list)
@dataclass
class BulletList(Block): items: List[ListItem]
@dataclass
class EnumeratedList(Block): items: List[ListItem]
@dataclass
class TableBlock(Block):
    headers: List[str]
    rows: List[List[str]]
    alignments: Optional[List[str]] = None
    fontsize: Optional[str] = None
    width: Optional[str] = None
    widths: Optional[str] = None
@dataclass
class Column:
    width: Optional[str]
    valign: Optional[str]
    blocks: List[Block]
@dataclass
class Columns(Block): columns: List[Column]
@dataclass
class RawText(Block): text: str
@dataclass
class FontSizeBlock(Block):
    size: str
    blocks: List[Block]
@dataclass
class AffiliationLogo:
    affiliation_key: str
    alt: str
    path: str
    width: Optional[str] = None
    height: Optional[str] = None
@dataclass
class TitlePage(Block):
    title: str
    subtitle: Optional[str] = None
    author: Optional[str] = None
    institute: Optional[str] = None
    date: Optional[str] = None
    authors: List[Tuple[str, List[str]]] = field(default_factory=list)
    affiliations: List[Tuple[Optional[str], str]] = field(default_factory=list)
    logos: List[AffiliationLogo] = field(default_factory=list)
@dataclass
class Slide:
    title: Optional[str]
    body: List[Block]
    slide_fontsize: Optional[str] = None
    title_level: int = 1
    subtitle: Optional[Heading] = None
    additional_subtitles: List[Heading] = field(default_factory=list)

HEADING_SIZES = {
    1: r"\Large", 2: r"\large", 3: r"\normalsize",
    4: r"\small", 5: r"\footnotesize", 6: r"\scriptsize",
}

LATEX_SPECIALS = {'\\': r'\textbackslash{}','{': r'\{','}': r'\}','$': r'\$','&': r'\&','%': r'\%','#': r'\#','_': r'\_','^': r'\textasciicircum{}','~': r'\textasciitilde{}'}

def escape_latex(text: str) -> str:
    return ''.join(LATEX_SPECIALS.get(ch, ch) for ch in text)

def normalize_newlines(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\r', '\n')

def split_slides(text: str) -> List[str]:
    lines = text.split('\n')
    slides: List[List[str]] = [[]]
    in_code = False
    code_fence = None
    for line in lines:
        stripped = line.strip()
        if not in_code:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code = True
                code_fence = stripped[:3]
                slides[-1].append(line)
                continue
            if stripped == "---":
                slides.append([])
                continue
            slides[-1].append(line)
        else:
            slides[-1].append(line)
            if stripped == code_fence:
                in_code = False
                code_fence = None
    return ['\n'.join(s).strip('\n') for s in slides]

def heading_match(line: str) -> Optional[Tuple[int, str]]:
    m = re.match(r'^(#{1,6})\s+(.*)$', line)
    return None if not m else (len(m.group(1)), m.group(2).strip())

def parse_heading_info(text: str):
    m = re.match(r'^(.*?)(?:\[(.*?)\])?\s*$', text.strip())
    if not m:
        return text.strip(), {}
    clean = (m.group(1) or "").strip()
    attrs_text = (m.group(2) or "").strip()
    attrs = {}
    if attrs_text:
        fm = re.search(r'fontsize\s*=\s*([^,\]]+)', attrs_text)
        if fm:
            attrs["fontsize"] = fm.group(1).strip().strip('"').strip("'")
    return clean, attrs

def image_match(line: str) -> Optional[Tuple[str, str, Optional[str], Optional[str]]]:
    m = re.match(r'^\!\[(.*?)\]\((.*?)\)(?:\{(.*?)\})?\s*$', line)
    if not m: return None
    alt, path, attrs = m.group(1), m.group(2), m.group(3)
    width = height = None
    if attrs:
        wm = re.search(r'(?:^|\s)width\s*=\s*([^\s}]+)', attrs)
        hm = re.search(r'(?:^|\s)height\s*=\s*([^\s}]+)', attrs)
        if wm: width = wm.group(1).strip().strip('"').strip("'")
        if hm: height = hm.group(1).strip().strip('"').strip("'")
    return alt, path, width, height

def parse_image_placement(alt: str):
    m = re.match(r'^(.*?)(?:\s+(left|right)(?::\s*([0-9]+(?:\.[0-9]+)?%))?)\s*$', alt.strip(), re.IGNORECASE)
    if not m:
        return alt.strip(), None, None, None
    clean_alt = m.group(1).strip()
    side = m.group(2).lower() if m.group(2) else None
    width = m.group(3) if m.group(3) else None
    return clean_alt, side, width, "top"

def complement_percent_width(width: Optional[str]) -> Optional[str]:
    if width is None:
        return None
    m = re.match(r'^([0-9]+(?:\.[0-9]+)?)%$', width.strip())
    if not m:
        return None
    value = float(m.group(1))
    comp = max(0.0, 100.0 - value)
    comp_text = f"{comp:.3f}".rstrip("0").rstrip(".")
    return comp_text + "%"

def infer_columns_from_positioned_images(slide: Slide) -> Slide:
    if any(isinstance(b, Columns) for b in slide.body):
        return slide

    positioned = [b for b in slide.body if isinstance(b, ImageBlock) and b.column_side in {"left", "right"}]
    if len(positioned) != 1:
        return slide

    image_block = positioned[0]
    other_blocks = [b for b in slide.body if b is not image_block]
    if not other_blocks:
        return slide

    image_width = image_block.column_width or "40%"
    text_width = complement_percent_width(image_width)

    image_col = Column(
        width=image_width,
        valign=image_block.column_valign or "top",
        blocks=[ImageBlock(
            alt=image_block.alt,
            path=image_block.path,
            width=image_block.width,
            height=image_block.height,
            column_side=None,
            column_width=None,
            column_valign=None,
        )],
    )
    text_col = Column(
        width=text_width,
        valign="top",
        blocks=other_blocks,
    )

    if image_block.column_side == "left":
        slide.body = [Columns([image_col, text_col])]
    else:
        slide.body = [Columns([text_col, image_col])]
    return slide

def bullet_match(line: str) -> Optional[Tuple[int, str]]:
    m = re.match(r'^(\s*)([-+*])\s+(.*)$', line)
    return None if not m else (len(m.group(1)), m.group(3))

def enum_match(line: str) -> Optional[Tuple[int, str]]:
    m = re.match(r'^(\s*)(\d+)\.\s+(.*)$', line)
    return None if not m else (len(m.group(1)), m.group(3))

def begin_fence(line: str) -> Optional[Tuple[str, str]]:
    stripped = line.strip()
    if stripped.startswith("```"): return "```", stripped[3:].strip()
    if stripped.startswith("~~~"): return "~~~", stripped[3:].strip()
    return None

def strip_html_comments(text: str, warnings: Optional[List[str]] = None) -> str:
    """Remove HTML comments outside fenced code while preserving line breaks."""
    output: List[str] = []
    in_comment = False
    code_fence = None

    for line in text.split('\n'):
        stripped = line.strip()
        if code_fence is not None:
            output.append(line)
            if stripped == code_fence:
                code_fence = None
            continue

        if not in_comment:
            opening = begin_fence(line)
            if opening is not None:
                code_fence = opening[0]
                output.append(line)
                continue

        kept: List[str] = []
        position = 0
        while position < len(line):
            if in_comment:
                end = line.find("-->", position)
                if end == -1:
                    position = len(line)
                else:
                    in_comment = False
                    position = end + 3
            else:
                start = line.find("<!--", position)
                if start == -1:
                    kept.append(line[position:])
                    position = len(line)
                else:
                    kept.append(line[position:start])
                    in_comment = True
                    position = start + 4
        output.append(''.join(kept))

    if in_comment and warnings is not None:
        warnings.append("Unclosed HTML comment; ignored through end of document.")
    return '\n'.join(output)

def parse_fence_info(info: str):
    info = info.strip()
    if not info:
        return "", None
    m = re.match(r'^([^\[\s]+)?(?:\[(.*?)\])?$', info)
    if not m:
        return info, None
    language = (m.group(1) or "").strip()
    attrs = m.group(2) or ""
    fontsize = None
    if attrs:
        fm = re.search(r'fontsize\s*=\s*([^,\]]+)', attrs)
        if fm:
            fontsize = fm.group(1).strip().strip('"').strip("'")
    return language, fontsize

def directive_slidefontsize_start(line: str) -> Optional[str]:
    stripped = line.strip()
    m = re.match(r'^:::\s+slidefontsize=(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))\s*$', stripped)
    if not m:
        return None
    return m.group(1) or m.group(2) or m.group(3)

def directive_columns_start(line: str) -> bool:
    return line.strip() == "::: columns"

def directive_column_start(line: str) -> Optional[Tuple[Optional[str], Optional[str]]]:
    stripped = line.strip()
    m = re.match(r'^:::\s+column(?:\s+(.+))?\s*$', stripped)
    if not m: return None
    attr_text = m.group(1) or ""
    width = valign = None
    wm = re.search(r'width=(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))', attr_text)
    vm = re.search(r'valign=(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))', attr_text)
    if wm: width = wm.group(1) or wm.group(2) or wm.group(3)
    if vm: valign = vm.group(1) or vm.group(2) or vm.group(3)
    return width, valign

def directive_fontsize_start(line: str) -> Optional[str]:
    stripped = line.strip()
    m = re.match(r'^:::\s+fontsize=(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))\s*$', stripped)
    if not m: return None
    return m.group(1) or m.group(2) or m.group(3)

def directive_end(line: str) -> bool:
    return line.strip() == ":::"

def directive_table_start(line: str) -> Optional[str]:
    m = re.match(r'^:::\s+table(?:\s+(.*))?$', line.strip())
    return None if m is None else (m.group(1) or "")

def directive_container_start(line: str) -> bool:
    return (directive_columns_start(line)
            or directive_column_start(line) is not None
            or directive_fontsize_start(line) is not None
            or directive_table_start(line) is not None)


def is_table_separator_line(line: str) -> bool:
    s = line.strip()
    if "|" not in s:
        return False
    cells = [c.strip() for c in s.strip("|").split("|")]
    if not cells:
        return False
    return all(re.match(r"^:?-{3,}:?$", c) for c in cells)

def split_table_row(line: str) -> List[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]

def parse_table_alignments(line: str) -> List[str]:
    out = []
    for cell in split_table_row(line):
        if cell.startswith(":") and cell.endswith(":"):
            out.append("c")
        elif cell.endswith(":"):
            out.append("r")
        else:
            out.append("l")
    return out

FOOTNOTE_DEFINITION_RE = re.compile(
    r'^\[\^([^\]]+)\](?:\[fontsize\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^\]\s]+))\s*\])?:\s*(.*)$'
)

def footnote_definition_match(line: str):
    return FOOTNOTE_DEFINITION_RE.match(line)

def extract_footnote_definitions(text: str):
    lines = text.split("\n")
    kept = []
    footnotes = {}
    i = 0
    while i < len(lines):
        m = footnote_definition_match(lines[i])
        if not m:
            kept.append(lines[i])
            i += 1
            continue
        key = m.group(1)
        fontsize = m.group(2) or m.group(3) or m.group(4)
        value = m.group(5).strip()
        i += 1
        continuation = []
        while i < len(lines):
            nxt = lines[i]
            if footnote_definition_match(nxt):
                break
            if nxt.startswith("    ") or nxt.startswith("\t"):
                continuation.append(nxt.strip())
                i += 1
                continue
            if nxt.strip() == "":
                continuation.append("")
                i += 1
                continue
            break
        extra = " ".join(x for x in continuation if x).strip()
        value = (value + " " + extra).strip() if extra else value
        footnotes[key] = FootnoteDefinition(value, fontsize)
    return "\n".join(kept), footnotes

INLINE_TOKEN_RE = re.compile(r'(\*\*\*[^*]+\*\*\*|___[^_]+___|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|`[^`]+`|\[[^\]]+\]\([^)]+\)|\[\^[^\]]+\])')

def parse_inlines(text: str) -> List[Inline]:
    parts = INLINE_TOKEN_RE.split(text)
    out: List[Inline] = []
    for part in parts:
        if not part: continue
        if part.startswith("***") and part.endswith("***") and len(part) >= 6:
            out.append(Bold([Italic(parse_inlines(part[3:-3]))]))
        elif part.startswith("___") and part.endswith("___") and len(part) >= 6:
            out.append(Bold([Italic(parse_inlines(part[3:-3]))]))
        elif part.startswith("**") and part.endswith("**") and len(part) >= 4:
            out.append(Bold(parse_inlines(part[2:-2])))
        elif part.startswith("__") and part.endswith("__") and len(part) >= 4:
            out.append(Bold(parse_inlines(part[2:-2])))
        elif part.startswith("*") and part.endswith("*") and len(part) >= 2:
            out.append(Italic(parse_inlines(part[1:-1])))
        elif part.startswith("_") and part.endswith("_") and len(part) >= 2:
            out.append(Italic(parse_inlines(part[1:-1])))
        elif part.startswith("`") and part.endswith("`") and len(part) >= 2:
            out.append(Code(part[1:-1]))
        elif re.match(r'^\[\^[^\]]+\]$', part):
            out.append(FootnoteRef(part[2:-1]))
        elif part.startswith("[") and "](" in part and part.endswith(")"):
            m = re.match(r'^\[(.*?)\]\((.*?)\)$', part)
            out.append(Link(parse_inlines(m.group(1)), m.group(2)) if m else Text(part))
        else:
            out.append(Text(part))
    return out

class BlockParser:
    def __init__(self, text: str, footnotes=None, warnings=None):
        self.lines = text.split('\n')
        self.i = 0
        self.footnotes = {} if footnotes is None else footnotes
        self.warnings = [] if warnings is None else warnings
    def eof(self) -> bool: return self.i >= len(self.lines)
    def peek(self) -> str: return self.lines[self.i] if not self.eof() else ""
    def advance(self) -> str:
        line = self.peek(); self.i += 1; return line
    def parse(self, allow_title_page: bool = True) -> Slide:
        blocks = self.parse_blocks(stop_at=None)

        legacy_slide_fontsize = None
        filtered_blocks: List[Block] = []
        for block in blocks:
            if isinstance(block, RawText) and block.text.startswith("__SLIDEFONTSIZE__:"):
                if legacy_slide_fontsize is None:
                    legacy_slide_fontsize = block.text.split(":", 1)[1]
            else:
                filtered_blocks.append(block)
        blocks = filtered_blocks

        inferred_slide_fontsize = None
        title_heading = blocks[0] if blocks and isinstance(blocks[0], Heading) else None
        if title_heading is not None:
            inferred_slide_fontsize = title_heading.attrs.get("fontsize")

        slide_fontsize = inferred_slide_fontsize or legacy_slide_fontsize

        title_page = self.try_parse_title_page(blocks) if allow_title_page else None
        if title_page is not None:
            slide = Slide(title=None, body=[title_page], slide_fontsize=slide_fontsize)
            slide.footnotes = self.footnotes
            return slide
        subtitles = []
        if title_heading is not None:
            title_index = blocks.index(title_heading)
            previous_line = title_heading.source_line
            for candidate in blocks[title_index + 1:]:
                # Blank lines separate the opening header from body headings.
                # Heading level controls size, not membership in the header.
                if (not isinstance(candidate, Heading) or previous_line is None
                        or candidate.source_line != previous_line + 1):
                    break
                subtitles.append(candidate)
                previous_line = candidate.source_line
        header_ids = {id(b) for b in [title_heading, *subtitles]}
        body = [b for b in blocks if id(b) not in header_ids]
        slide = Slide(title=title_heading.text if title_heading is not None else None,
                      body=body, slide_fontsize=slide_fontsize,
                      title_level=title_heading.level if title_heading is not None else 1,
                      subtitle=subtitles[0] if subtitles else None,
                      additional_subtitles=subtitles[1:])
        slide.footnotes = self.footnotes
        slide = infer_columns_from_positioned_images(slide)
        return slide
    def try_parse_title_page(self, blocks: List[Block]) -> Optional[TitlePage]:
        if not blocks or not isinstance(blocks[0], Heading) or blocks[0].level != 1: return None
        title = blocks[0].text; idx=1; subtitle=author=institute=date=None
        authors: List[Tuple[str, List[str]]] = []
        affiliations: List[Tuple[Optional[str], str]] = []
        logos: List[AffiliationLogo] = []
        if idx < len(blocks) and isinstance(blocks[idx], Heading) and blocks[idx].level == 2:
            subtitle = blocks[idx].text; idx += 1
        if idx < len(blocks) and isinstance(blocks[idx], BulletList):
            for item in blocks[idx].items:
                text = item.text.strip(); lower = text.lower()
                if lower.startswith("author:"):
                    author = text.split(":",1)[1].strip()
                    refs = re.findall(r'\[\^([^\]]+)\]', author)
                    name = re.sub(r'\[\^[^\]]+\]', '', author).strip()
                    authors.append((name, refs))
                elif lower.startswith("affiliation:") or lower.startswith("institute:"):
                    institute = text.split(":",1)[1].strip()
                    entries = re.split(r',\s*(?=\[\^[^\]]+\])', institute)
                    for entry in entries:
                        label_match = re.match(r'^\[\^([^\]]+)\]\s*(.*)$', entry.strip())
                        if label_match:
                            affiliations.append((label_match.group(1), label_match.group(2).strip()))
                        else:
                            affiliations.append((None, entry.strip()))
                elif lower.startswith("affiliation-logo:"):
                    logo_value = text.split(":", 1)[1].strip()
                    logo_label = re.match(r'^\[\^([^\]]+)\]\s*(.*)$', logo_value)
                    logo_image = image_match(logo_label.group(2).strip()) if logo_label else None
                    if logo_label is None or logo_image is None:
                        self.warnings.append(f"Malformed Affiliation-Logo metadata: {logo_value}")
                    else:
                        logos.append(AffiliationLogo(
                            affiliation_key=logo_label.group(1),
                            alt=logo_image[0],
                            path=logo_image[1],
                            width=logo_image[2],
                            height=logo_image[3],
                        ))
                elif lower.startswith("date:"): date = text.split(":",1)[1].strip()
                else: return None
            idx += 1
        if idx != len(blocks):
            return None

        unique_affiliations: List[Tuple[Optional[str], str]] = []
        labels = set()
        for key, affiliation_text in affiliations:
            if key is not None and key in labels:
                self.warnings.append(f"Duplicate title-page affiliation label: {key}; using first definition.")
                continue
            if key is not None:
                labels.add(key)
            unique_affiliations.append((key, affiliation_text))

        referenced = {key for _, refs in authors for key in refs}
        for key in sorted(referenced - labels):
            self.warnings.append(f"Undefined title-page affiliation reference: {key}")
        for key in sorted(labels - referenced):
            self.warnings.append(f"Unused title-page affiliation label: {key}")
        for logo in logos:
            if logo.affiliation_key not in labels:
                self.warnings.append(
                    f"Undefined affiliation for title-page logo: {logo.affiliation_key}"
                )

        return TitlePage(title, subtitle, author, institute, date,
                         authors=authors, affiliations=unique_affiliations, logos=logos)
    def collect_container(self, stop_at_column=False) -> str:
        """Read a container body without interpreting directives inside code."""
        lines = []
        depth = 0
        fence = None
        while not self.eof():
            line = self.peek()
            if fence is not None:
                lines.append(self.advance())
                if line.strip() == fence:
                    fence = None
                continue
            opening = begin_fence(line)
            if opening:
                fence = opening[0]
                lines.append(self.advance())
                continue
            if depth == 0 and stop_at_column and directive_column_start(line) is not None:
                return '\n'.join(lines)
            if directive_end(line):
                self.advance()
                if depth == 0:
                    return '\n'.join(lines)
                depth -= 1
            else:
                if directive_container_start(line):
                    depth += 1
                self.advance()
            lines.append(line)
        self.warnings.append("Unclosed directive container; closed at end of slide.")
        return '\n'.join(lines)

    def parse_table_directive(self, attributes: str) -> List[Block]:
        self.advance()
        attrs = {}
        lexer = shlex.shlex(attributes, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ''
        lexer.escape = ''  # Preserve LaTeX commands such as \tiny.
        try:
            for token in lexer:
                key, sep, value = token.partition('=')
                if not sep or key not in {'fontsize', 'width', 'widths'} or not value:
                    self.warnings.append(f"Unsupported or malformed table attribute: {token}")
                else:
                    attrs[key] = value
        except ValueError as exc:
            self.warnings.append(f"Malformed table attributes: {exc}")
        inner = BlockParser(self.collect_container(), self.footnotes, self.warnings).parse_blocks(None)
        if len(inner) != 1 or not isinstance(inner[0], TableBlock):
            self.warnings.append("Table directive must contain exactly one pipe table; attributes ignored.")
            return inner
        table = inner[0]
        table.fontsize = attrs.get('fontsize')
        table.width = attrs.get('width')
        table.widths = attrs.get('widths')
        return inner

    def parse_blocks(self, stop_at: Optional[str]) -> List[Block]:
        blocks: List[Block] = []
        while not self.eof():
            line = self.peek()
            if stop_at is not None and line.strip() == stop_at: break
            table_attrs = directive_table_start(line)
            if table_attrs is not None:
                blocks.extend(self.parse_table_directive(table_attrs)); continue
            fs = directive_fontsize_start(line)
            if fs is not None:
                self.advance()
                inner_blocks = BlockParser(self.collect_container(), self.footnotes, self.warnings).parse_blocks(None)
                blocks.append(FontSizeBlock(fs, inner_blocks)); continue
            if directive_columns_start(line):
                blocks.append(self.parse_columns()); continue
            if begin_fence(line):
                blocks.append(self.parse_code_block()); continue
            if "|" in line and (self.i + 1) < len(self.lines) and is_table_separator_line(self.lines[self.i + 1]):
                blocks.append(self.parse_table()); continue
            hm = heading_match(line)
            if hm:
                source_line = self.i
                self.advance()
                clean_text, attrs = parse_heading_info(hm[1])
                blocks.append(Heading(hm[0], clean_text, attrs, source_line)); continue
            im = image_match(line.strip())
            if im:
                self.advance()
                clean_alt, column_side, column_width, column_valign = parse_image_placement(im[0])
                blocks.append(ImageBlock(clean_alt, im[1], im[2], im[3], column_side, column_width, column_valign)); continue
            if bullet_match(line) is not None:
                blocks.append(self.parse_list("bullet")); continue
            if enum_match(line) is not None:
                blocks.append(self.parse_list("enum")); continue
            if line.strip() == "":
                self.advance(); continue
            blocks.append(self.parse_paragraph())
        return blocks
    def parse_code_block(self) -> CodeBlock:
        start = self.advance(); fence, info = begin_fence(start)
        language, fontsize = parse_fence_info(info)
        content_lines: List[str] = []
        while not self.eof():
            line = self.advance()
            if line.strip() == fence: break
            content_lines.append(line)
        return CodeBlock(language, '\n'.join(content_lines), fontsize)
    def parse_paragraph(self) -> Paragraph:
        lines: List[str] = []
        while not self.eof():
            line = self.peek()
            if line.strip()=="" or heading_match(line) or begin_fence(line) or directive_columns_start(line) or directive_fontsize_start(line) is not None or directive_table_start(line) is not None or image_match(line.strip()) or bullet_match(line) is not None or enum_match(line) is not None or ("|" in line and self.i + 1 < len(self.lines) and is_table_separator_line(self.lines[self.i + 1])):
                break
            lines.append(self.advance())
        return Paragraph(lines)
    def parse_columns(self) -> Columns:
        self.advance()
        columns: List[Column] = []
        while not self.eof():
            line = self.peek()
            if directive_end(line):
                self.advance(); break
            column_meta = directive_column_start(line)
            if column_meta is not None:
                width, valign = column_meta; self.advance()
                col_blocks = BlockParser(self.collect_container(stop_at_column=True), self.footnotes, self.warnings).parse_blocks(None)
                columns.append(Column(width, valign, col_blocks)); continue
            self.advance()
        return Columns(columns)
    def parse_table(self) -> TableBlock:
        header_line = self.advance()
        sep_line = self.advance()
        headers = split_table_row(header_line)
        aligns = parse_table_alignments(sep_line)
        rows: List[List[str]] = []
        while not self.eof():
            line = self.peek()
            if line.strip() == "" or directive_end(line) or directive_container_start(line) or "|" not in line or is_table_separator_line(line):
                break
            rows.append(split_table_row(self.advance()))
        return TableBlock(headers=headers, rows=rows, alignments=aligns)

    def parse_list(self, kind: str):
        items, _ = self._parse_list_items(kind, None)
        return BulletList(items) if kind=="bullet" else EnumeratedList(items)
    def _parse_list_items(self, kind: str, current_indent: Optional[int]):
        items: List[ListItem] = []
        while not self.eof():
            line = self.peek()
            if line.strip()=="": self.advance(); continue
            m = bullet_match(line) if kind=="bullet" else enum_match(line)
            if m is None: break
            indent, text = m
            if current_indent is None: current_indent = indent
            if indent < current_indent: break
            if indent > current_indent:
                if not items: break
                nested_kind = "bullet" if bullet_match(line) is not None else "enum"
                nested_items, _ = self._parse_list_items(nested_kind, indent)
                items[-1].children.append(BulletList(nested_items) if nested_kind=="bullet" else EnumeratedList(nested_items))
                continue
            self.advance()
            item = ListItem(text)
            continuation=[]
            while not self.eof():
                nxt = self.peek()
                if nxt.strip()=="" or bullet_match(nxt) is not None or enum_match(nxt) is not None or heading_match(nxt) or begin_fence(nxt) or image_match(nxt.strip()) or directive_columns_start(nxt) or directive_fontsize_start(nxt) is not None or directive_table_start(nxt) is not None:
                    break
                leading = len(nxt) - len(nxt.lstrip(' '))
                if leading > indent: continuation.append(self.advance().strip())
                else: break
            if continuation: item.text += " " + " ".join(continuation)
            items.append(item)
        return items, current_indent

class BeamerEmitter:
    def __init__(self, theme=None, colortheme=None, fonttheme=None, innertheme=None, outertheme=None,
                 text_margin_left="5mm", text_margin_right="5mm",
                 list_indent_1=None, list_indent_2=None, list_indent_3=None,
                 list_label_sep="0.35em", list_item_sep="0.15em",
                 list_top_sep="0.2em", list_parse_sep="0pt", list_indent=None):
        self.warnings: List[str] = []
        self.theme=theme; self.colortheme=colortheme; self.fonttheme=fonttheme; self.innertheme=innertheme; self.outertheme=outertheme
        self.text_margin_left = self.validate_layout_length(text_margin_left, "text margin left", "5mm")
        self.text_margin_right = self.validate_layout_length(text_margin_right, "text margin right", "5mm")
        common_indent = (self.validate_layout_length(list_indent, "list indent", "1.5em")
                         if list_indent is not None else None)
        indent_defaults = (common_indent or "1.5em", common_indent or "1.25em", common_indent or "1.1em")
        self.list_indent_1 = (self.validate_layout_length(list_indent_1, "list indent 1", indent_defaults[0])
                              if list_indent_1 is not None else indent_defaults[0])
        self.list_indent_2 = (self.validate_layout_length(list_indent_2, "list indent 2", indent_defaults[1])
                              if list_indent_2 is not None else indent_defaults[1])
        self.list_indent_3 = (self.validate_layout_length(list_indent_3, "list indent 3", indent_defaults[2])
                              if list_indent_3 is not None else indent_defaults[2])
        self.list_label_sep = self.validate_layout_length(list_label_sep, "list label separation", "0.35em")
        self.list_item_sep = self.validate_layout_length(list_item_sep, "list item separation", "0.15em")
        self.list_top_sep = self.validate_layout_length(list_top_sep, "list top separation", "0.2em")
        self.list_parse_sep = self.validate_layout_length(list_parse_sep, "list paragraph separation", "0pt")
        self.current_fontsize: Optional[str] = None
        self.current_footnotes = {}
        self.in_columns = False
        self.pending_column_footnotes = []
    def validate_layout_length(self, value: str, name: str, default: str) -> str:
        candidate = value.strip()
        if candidate == "0":
            return "0pt"
        if re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)(?:pt|mm|cm|in|em|ex|pc|bp|dd|cc|sp)', candidate):
            return candidate
        self.warnings.append(f"Invalid {name}: {value}; using {default}")
        return default
    def emit_document(self, slides: List[Slide]) -> str:
        title_page = next((s.body[0] for s in slides if len(s.body)==1 and isinstance(s.body[0], TitlePage)), None)
        return '\n'.join([self.preamble(title_page)] + [self.emit_slide(s) for s in slides] + [self.postamble()])
    def emit_title_authors(self, title_page: TitlePage) -> str:
        affiliation_numbers = {
            key: number
            for number, (key, _) in enumerate(
                ((key, text) for key, text in title_page.affiliations if key is not None),
                start=1,
            )
        }
        rendered = []
        for name, refs in title_page.authors:
            numbers = []
            for key in refs:
                number = affiliation_numbers.get(key)
                if number is not None and number not in numbers:
                    numbers.append(number)
            author_text = escape_latex(name)
            if numbers:
                author_text += r"\inst{" + ",".join(str(number) for number in numbers) + "}"
            rendered.append(author_text)
        return r" \and ".join(rendered)
    def emit_title_affiliations(self, title_page: TitlePage) -> str:
        affiliation_numbers = {
            key: number
            for number, (key, _) in enumerate(
                ((key, text) for key, text in title_page.affiliations if key is not None),
                start=1,
            )
        }
        rendered = []
        for key, text in title_page.affiliations:
            prefix = r"\inst{" + str(affiliation_numbers[key]) + "} " if key is not None else ""
            rendered.append(prefix + escape_latex(text))
        return r", \quad ".join(rendered)
    def emit_header_logos(self, title_page: TitlePage) -> str:
        affiliation_labels = {key for key, _ in title_page.affiliations if key is not None}
        rendered = []
        for logo in title_page.logos:
            if logo.affiliation_key not in affiliation_labels:
                continue
            options = []
            width = self.image_dimension_to_latex(logo.width, None)
            default_height = None if logo.width is not None else "6mm"
            height = self.image_dimension_to_latex(logo.height, default_height)
            if width:
                options.append(f"width={width}")
            if height:
                options.append(f"height={height}")
            options.append("keepaspectratio")
            rendered.append(
                rf"\includegraphics[{','.join(options)}]{{{escape_latex(logo.path)}}}"
            )
        return ("%\n" + r"\hspace{2mm}" + "%\n").join(rendered)
    def preamble(self, title_page: Optional[TitlePage]=None) -> str:
        parts = [r"""\PassOptionsToPackage{table}{xcolor}
\documentclass{beamer}
\usepackage{hyperref}
\usepackage{lmodern}  % Enables smooth font scaling
\usepackage{graphicx}
\usepackage{multicol}
\usepackage{ragged2e}
\usepackage{array}
\newlength{\mdBeamerTableWidth}
\newlength{\mdBeamerTableContentWidth}
\newcommand{\mdBeamerHeaderLine}[2]{{#1\strut#2}}
\usepackage{iftex}
\ifPDFTeX
  \usepackage[utf8]{inputenc}
  \usepackage[T1]{fontenc}
\else
  \usepackage{fontspec}
  \setmonofont{DejaVu Sans Mono}
\fi
\usepackage{listings}
"""]
        if self.theme: parts.append(rf"\usetheme{{{escape_latex(self.theme)}}}")
        if self.colortheme: parts.append(rf"\usecolortheme{{{escape_latex(self.colortheme)}}}")
        if self.fonttheme: parts.append(rf"\usefonttheme{{{escape_latex(self.fonttheme)}}}")
        if self.innertheme: parts.append(rf"\useinnertheme{{{escape_latex(self.innertheme)}}}")
        if self.outertheme: parts.append(rf"\useoutertheme{{{escape_latex(self.outertheme)}}}")
        parts.append(
            r"\setbeamersize{text margin left=" + self.text_margin_left
            + ",text margin right=" + self.text_margin_right + "}"
        )
        parts.append(r"\setlength{\leftmargini}{" + self.list_indent_1 + "}")
        parts.append(r"\setlength{\leftmarginii}{" + self.list_indent_2 + "}")
        parts.append(r"\setlength{\leftmarginiii}{" + self.list_indent_3 + "}")
        parts.append(r"\setlength{\labelsep}{" + self.list_label_sep + "}")
        # LaTeX reads topsep while opening a list, so setting it only inside the
        # environment is too late to control the space before the first item.
        # Define all three supported levels after loading the selected themes.
        parts.append(
            "\\makeatletter\n"
            "\\def\\@listi{\\leftmargin\\leftmargini"
            "\\labelwidth\\leftmargini\\advance\\labelwidth-\\labelsep"
            "\\topsep" + self.list_top_sep
            + "\\parsep" + self.list_parse_sep
            + "\\itemsep" + self.list_item_sep + "\\partopsep0pt}\n"
            "\\def\\@listii{\\leftmargin\\leftmarginii"
            "\\labelwidth\\leftmarginii\\advance\\labelwidth-\\labelsep"
            "\\topsep" + self.list_top_sep
            + "\\parsep" + self.list_parse_sep
            + "\\itemsep" + self.list_item_sep + "\\partopsep0pt}\n"
            "\\def\\@listiii{\\leftmargin\\leftmarginiii"
            "\\labelwidth\\leftmarginiii\\advance\\labelwidth-\\labelsep"
            "\\topsep" + self.list_top_sep
            + "\\parsep" + self.list_parse_sep
            + "\\itemsep" + self.list_item_sep + "\\partopsep0pt}\n"
            "\\makeatother"
        )
        parts.append(r"\setbeamertemplate{navigation symbols}{}")
        parts.append(r"\setbeamertemplate{page number in head/foot}[totalframenumber]")
        header_logos = self.emit_header_logos(title_page) if title_page is not None else ""
        if header_logos:
            parts.append(r"\usepackage{tikz}")
            parts.append("\\newcommand{\\mdBeamerHeaderLogos}{%\n" + header_logos + "%\n}")
            parts.append(r"""
\AddToHook{shipout/foreground}{%
  \begin{tikzpicture}[remember picture,overlay]
    \node[anchor=north east,inner sep=0pt,xshift=-2mm,yshift=-1mm]
      at (current page.north east) {\mdBeamerHeaderLogos};
  \end{tikzpicture}%
}
""")
        if title_page is not None:
            parts.append(rf"\title{{{escape_latex(title_page.title)}}}")
            if title_page.subtitle: parts.append(rf"\subtitle{{{escape_latex(title_page.subtitle)}}}")
            if title_page.authors: parts.append(rf"\author{{{self.emit_title_authors(title_page)}}}")
            elif title_page.author: parts.append(rf"\author{{{escape_latex(title_page.author)}}}")
            if title_page.affiliations: parts.append(rf"\institute{{{self.emit_title_affiliations(title_page)}}}")
            elif title_page.institute: parts.append(rf"\institute{{{escape_latex(title_page.institute)}}}")
            parts.append(rf"\date{{{escape_latex(title_page.date)}}}" if title_page.date else r"\date{}")
        parts.append(r"""
\lstset{
  basicstyle=\ttfamily\small,
  breaklines=true,
  columns=fullflexible,
  keepspaces=true
}

\begin{document}
""")
        return "\n".join(parts)
    def postamble(self) -> str: return r"\end{document}"
    def block_contains_code(self, block: Block) -> bool:
        if isinstance(block, CodeBlock): return True
        if isinstance(block, Columns): return any(self.block_contains_code(b) for c in block.columns for b in c.blocks)
        if isinstance(block, FontSizeBlock): return any(self.block_contains_code(b) for b in block.blocks)
        if isinstance(block, BulletList): return any(self.block_contains_code(ch) for i in block.items for ch in i.children)
        if isinstance(block, EnumeratedList): return any(self.block_contains_code(ch) for i in block.items for ch in i.children)
        return False
    def slide_requires_fragile(self, slide: Slide) -> bool:
        return any(self.block_contains_code(b) for b in slide.body)
    def emit_slide(self, slide: Slide) -> str:
        title = escape_latex(slide.title) if slide.title else ""
        fragile = self.slide_requires_fragile(slide)
        # Beamer builds the header outside its frame-body group. Font settings
        # made inside that body can disappear before the header is rendered.
        # Keep them alive around the entire frame, without leaking to the next.
        out = [r"\begingroup"]
        if slide.title is not None:
            out.append(rf"\setbeamerfont{{frametitle}}{{size={HEADING_SIZES[slide.title_level]}}}")
        if slide.subtitle is not None:
            out.append(rf"\setbeamerfont{{framesubtitle}}{{size={HEADING_SIZES[slide.subtitle.level]}}}")
        out.append(rf"\begin{{frame}}[fragile]{{{title}}}" if slide.title and fragile else rf"\begin{{frame}}{{{title}}}" if slide.title else r"\begin{frame}[fragile]" if fragile else r"\begin{frame}")
        self.current_footnotes = getattr(slide, "footnotes", {})
        prev_size = self.current_fontsize
        slide_size = getattr(slide, "slide_fontsize", None)
        if slide_size:
            self.current_fontsize = self.validate_fontsize(slide_size)
            out.append(self.current_fontsize)
        if slide.subtitle is not None:
            header_lines = [slide.subtitle, *slide.additional_subtitles]
            # Break only between actual lines. A trailing paragraph break adds
            # an empty line in themes such as Warsaw's shadow header template.
            subtitle_tex = '\\\\\n'.join(
                rf"\mdBeamerHeaderLine{{{HEADING_SIZES[h.level]}}}{{{escape_latex(h.text)}}}"
                for h in header_lines
            )
            out.append(r"\framesubtitle{" + subtitle_tex + "}")
        try:
            for block in slide.body:
                out.append(self.emit_block(block))
        finally:
            self.current_fontsize = prev_size
        out.append(r"\end{frame}")
        out.append(r"\endgroup")
        return '\n'.join(x for x in out if x)
    def validate_fontsize(self, size: str) -> str:
        size = size.strip()
        allowed = {r"\tiny", r"\scriptsize", r"\footnotesize", r"\small", r"\normalsize",
                   r"\large", r"\Large", r"\LARGE", r"\huge", r"\Huge"}
        if size not in allowed:
            self.warnings.append(f"Unsupported fontsize command: {size}; using \\normalsize")
            return r"\normalsize"
        return size

    def emit_block(self, block: Block, list_depth: int = 1) -> str:
        if isinstance(block, FontSizeBlock):
            size = self.validate_fontsize(block.size)
            prev=self.current_fontsize; self.current_fontsize=size
            try: inner=[self.emit_block(b,1) for b in block.blocks]
            finally: self.current_fontsize=prev
            return "{%s\n%s\n}" % (size, "\n".join(inner))
        if isinstance(block, TitlePage): return r"\titlepage"
        if isinstance(block, Paragraph): return self.emit_inlines(parse_inlines(' '.join(line.strip() for line in block.lines))) + "\n"
        if isinstance(block, Heading): return r"\medskip" + "\n" + r"\textbf{" + escape_latex(block.text) + "}" + "\n"
        if isinstance(block, ImageBlock):
            opts=[]; path=escape_latex(block.path)
            width=self.image_dimension_to_latex(block.width, r"0.95\linewidth")
            height=self.image_dimension_to_latex(block.height, None)
            if width: opts.append(f"width={width}")
            if height: opts.append(f"height={height}")
            opts.append("keepaspectratio")
            return rf"\includegraphics[{','.join(opts)}]{{{path}}}"
        if isinstance(block, CodeBlock):
            opts=[]
            if block.language: opts.append(f"language={escape_latex(block.language)}")
            code_size = block.fontsize if getattr(block, "fontsize", None) else self.current_fontsize
            if code_size:
                code_size = self.validate_fontsize(code_size)
            opts.append(f"basicstyle=\\ttfamily{code_size}" if code_size else r"basicstyle=\ttfamily\small")
            opts += ["breaklines=true","columns=fullflexible","keepspaces=true","frame=single","framerule=0.4pt","rulecolor=\\color{black!15}","backgroundcolor=\\color{black!3}","framesep=4pt","aboveskip=4pt","belowskip=4pt"]
            return rf"\begin{{lstlisting}}[{','.join(opts)}]" + "\n" + block.content + "\n" + r"\end{lstlisting}"
        if isinstance(block, TableBlock): return self.emit_table(block)
        if isinstance(block, BulletList): return self.emit_list(block.items, "itemize", list_depth)
        if isinstance(block, EnumeratedList): return self.emit_list(block.items, "enumerate", list_depth)
        if isinstance(block, Columns): return self.emit_columns(block)
        if isinstance(block, RawText): return escape_latex(block.text)
        return escape_latex(str(block))
    def emit_columns(self, block: Columns) -> str:
        n=max(len(block.columns),1)
        prev_in_columns = self.in_columns
        prev_pending = self.pending_column_footnotes
        self.in_columns = True
        self.pending_column_footnotes = []

        out=[r"\begin{columns}[T]"]
        try:
            for col in block.columns:
                width=self.column_width_to_latex(col.width,n); valign=self.column_valign_to_latex(col.valign)
                out.append(rf"\begin{{column}}[{valign}]{{{width}\textwidth}}")
                for b in col.blocks: out.append(self.emit_block(b,1))
                out.append(r"\end{column}")
        finally:
            pending = self.pending_column_footnotes
            self.in_columns = prev_in_columns
            self.pending_column_footnotes = prev_pending

        out.append(r"\end{columns}")
        if pending:
            out.append(r"\vspace{0.35em}")
            out.append("{")
            rendered = []
            for i, (text, size) in enumerate(pending, start=1):
                reference = (r"\textsuperscript{" + self._column_footnote_mark(i) + "} "
                             + self.emit_inlines(parse_inlines(text)))
                rendered.append("{" + (size or r"\tiny") + " " + reference + "}")
            out.append(r"\\ ".join(rendered))
            out.append(r"}")
        return '\n'.join(out)
    def column_width_to_latex(self, width: Optional[str], ncols: int) -> str:
        if not width: return f"{1.0/ncols:.3f}"
        w=width.strip()
        if w.endswith("%"):
            try: return f"{float(w[:-1])/100.0:.3f}"
            except ValueError: self.warnings.append(f"Invalid column width percentage: {width}"); return f"{1.0/ncols:.3f}"
        if "/" in w:
            try:
                a,b=w.split("/",1); return f"{float(a)/float(b):.3f}"
            except Exception:
                self.warnings.append(f"Invalid fractional column width: {width}"); return f"{1.0/ncols:.3f}"
        self.warnings.append(f"Unsupported column width format: {width}; using equal widths"); return f"{1.0/ncols:.3f}"
    def column_valign_to_latex(self, valign: Optional[str]) -> str:
        if not valign: return "T"
        mapping={"top":"T","t":"T","center":"c","c":"c","bottom":"b","b":"b"}; v=valign.strip().lower()
        if v in mapping: return mapping[v]
        self.warnings.append(f"Unsupported column valign: {valign}; using top alignment"); return "T"
    def image_dimension_to_latex(self, value: Optional[str], default: Optional[str]) -> Optional[str]:
        if value is None: return default
        v=value.strip()
        if re.match(r'^\d*\.?\d+$', v): return v + r"\linewidth"
        if re.match(r'^\d*\.?\d+%$', v):
            try: return f"{float(v[:-1])/100.0:.3f}" + r"\linewidth"
            except ValueError: self.warnings.append(f"Invalid image dimension percentage: {value}"); return default
        if re.match(r'^\d*\.?\d+(?:\\linewidth|\\textwidth|\\textheight|cm|mm|in|pt|em|ex)$', v): return v
        self.warnings.append(f"Unsupported image dimension format: {value}; using default"); return default
    def emit_list(self, items: List[ListItem], env: str, depth: int = 1) -> str:
        if depth > 3:
            self.warnings.append(f"List nesting depth {depth} exceeds Beamer-safe limit 3; flattening deeper levels.")
            return "\n".join(r"\textbf{-} " + self.emit_inlines(parse_inlines(i.text)) for i in items)
        out=[rf"\begin{{{env}}}"]
        out.append(r"\setlength{\itemsep}{" + self.list_item_sep + "}")
        out.append(r"\setlength{\topsep}{" + self.list_top_sep + "}")
        out.append(r"\setlength{\parsep}{" + self.list_parse_sep + "}")
        # Beamer resets the font at every list depth; apply the inherited size
        # after entering each environment, including nested lists.
        if self.current_fontsize:
            out.append(self.current_fontsize)
        for item in items:
            out.append(r"\item " + self.emit_inlines(parse_inlines(item.text)))
            for child in item.children:
                if isinstance(child, BulletList): out.append(self.emit_list(child.items,"itemize",depth+1))
                elif isinstance(child, EnumeratedList): out.append(self.emit_list(child.items,"enumerate",depth+1))
                else: out.append(self.emit_block(child, depth+1))
        out.append(rf"\end{{{env}}}")
        return '\n'.join(out)
    def table_percentage(self, value: str) -> float:
        if not re.fullmatch(r'(?:\d+(?:\.\d+)?|\.\d+)%', value.strip()):
            raise ValueError("expected a positive percentage")
        number = float(value.strip()[:-1])
        if not math.isfinite(number) or not 0 < number <= 100:
            raise ValueError("percentage must be greater than 0 and at most 100")
        return number / 100

    def table_layout(self, block: TableBlock, ncols: int):
        alignments = block.alignments or ['l'] * ncols
        if len(alignments) != ncols:
            self.warnings.append(f"Table separator has {len(alignments)} columns; expected {ncols}.")
        alignments = (alignments + ['l'] * ncols)[:ncols]
        if block.width is None and block.widths is None:
            return ''.join(alignments), []

        width = block.width.strip() if block.width is not None else r"\linewidth"
        percentage = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))%', width)
        if percentage:
            # Percentages are Markdown shorthand; native TeX lengths and
            # expressions pass through unchanged for TeX to interpret.
            factor = format(Decimal(percentage.group(1)) / 100, 'f')
            width = factor + r"\linewidth"
        shares = [1 / ncols] * ncols
        if block.widths is not None:
            try:
                values = [self.table_percentage(v) for v in block.widths.split(',')]
                if len(values) != ncols or not math.isclose(sum(values), 1.0, abs_tol=0.00001, rel_tol=0):
                    raise ValueError("column widths must match the header count and total 100%")
                shares = values
            except ValueError:
                self.warnings.append(f"Invalid table column widths: {block.widths}; expected {ncols} positive percentages totaling 100%; using equal widths.")
        setup = [
            rf"\setlength{{\mdBeamerTableWidth}}{{{width}}}",
            rf"\setlength{{\mdBeamerTableContentWidth}}{{\dimexpr\mdBeamerTableWidth-{2 * ncols}\tabcolsep\relax}}",
            # Tiny tables should still have positive paragraph widths. Reduce
            # padding only when it would exhaust the available table width.
            r"\ifdim\mdBeamerTableContentWidth<1pt",
            r"\setlength{\tabcolsep}{0pt}",
            r"\setlength{\mdBeamerTableContentWidth}{\mdBeamerTableWidth}",
            r"\fi",
        ]
        commands = {'l': r'\raggedright', 'c': r'\centering', 'r': r'\raggedleft'}
        cols = ''.join(
            rf">{{{commands[a]}\arraybackslash}}p{{{share:.8f}\mdBeamerTableContentWidth}}"
            for a, share in zip(alignments, shares)
        )
        return cols, setup

    def emit_table(self, block: TableBlock) -> str:
        ncols = max(len(block.headers), 1)
        cols, layout_setup = self.table_layout(block, ncols)
        size = self.validate_fontsize(block.fontsize) if block.fontsize else (self.current_fontsize or r"\scriptsize")

        header_cells = [
            r"\textbf{" + self.emit_inlines(parse_inlines(c)) + r"}"
            for c in block.headers
        ]

        out = [
            r"\medskip",
            r"{",
            size,
            r"\setlength{\tabcolsep}{4pt}",
            r"\renewcommand{\arraystretch}{1.12}",
            *layout_setup,
            r"\begin{center}",
            r"\rowcolors{2}{black!4}{white}",
            r"\begin{tabular}{" + cols + "}",
            r"\rowcolor{black!12}"
        ]
        out.append(" & ".join(header_cells) + r" \\")
        out.append(r"\hline")
        for row_number, row in enumerate(block.rows, start=1):
            if len(row) != ncols:
                self.warnings.append(f"Table row {row_number} has {len(row)} cells; expected {ncols}; "
                                     + ("padding missing cells." if len(row) < ncols else "discarding extra cells."))
            padded = row + [""] * max(0, ncols - len(row))
            out.append(" & ".join(self.emit_inlines(parse_inlines(c)) for c in padded[:ncols]) + r" \\")
        out.append(r"\end{tabular}")
        out.append(r"\end{center}")
        out.append(r"}")
        out.append(r"\medskip")
        return '\n'.join(out)

    def _column_footnote_mark(self, idx: int) -> str:
        letters = "abcdefghijklmnopqrstuvwxyz"
        if 1 <= idx <= len(letters):
            return letters[idx - 1]
        return str(idx)

    def emit_inlines(self, inlines: List[Inline]) -> str:
        out=[]
        for node in inlines:
            if isinstance(node, Text): out.append(escape_latex(node.value))
            elif isinstance(node, Bold): out.append(r"\textbf{" + self.emit_inlines(node.children) + "}")
            elif isinstance(node, Italic): out.append(r"\emph{" + self.emit_inlines(node.children) + "}")
            elif isinstance(node, Code): out.append(r"\texttt{" + escape_latex(node.value) + "}")
            elif isinstance(node, Link): out.append(r"\href{" + escape_latex(node.url) + "}{" + self.emit_inlines(node.label) + "}")
            elif isinstance(node, FootnoteRef):
                definition = self.current_footnotes.get(node.key, FootnoteDefinition(""))
                text = definition.text
                reference_size = (self.validate_fontsize(definition.fontsize)
                                  if definition.fontsize else self.current_fontsize)
                if self.in_columns:
                    pending_reference = (text, reference_size)
                    if pending_reference not in self.pending_column_footnotes:
                        self.pending_column_footnotes.append(pending_reference)
                    idx = self.pending_column_footnotes.index(pending_reference) + 1
                    out.append(r"\textsuperscript{" + self._column_footnote_mark(idx) + "}")
                else:
                    reference = self.emit_inlines(parse_inlines(text))
                    if reference_size:
                        reference = "{" + reference_size + " " + reference + "}"
                        out.append(
                            r"\footnotemark"
                            r"{\setbeamerfont{footnote}{size=" + reference_size + "}"
                            r"\setbeamerfont{footnote mark}{size=" + reference_size + "}"
                            r"\footnotetext{" + reference + "}}"
                        )
                    else:
                        out.append(r"\footnote{" + reference + "}")
            else: out.append(escape_latex(str(node)))
        return ''.join(out)

def md_to_beamer(markdown_text: str, theme=None, colortheme=None, fonttheme=None, innertheme=None, outertheme=None,
                 text_margin_left="5mm", text_margin_right="5mm",
                 list_indent_1=None, list_indent_2=None, list_indent_3=None,
                 list_label_sep="0.35em", list_item_sep="0.15em",
                 list_top_sep="0.2em", list_parse_sep="0pt", list_indent=None):
    markdown_text = normalize_newlines(markdown_text)
    slides = []
    warnings = []
    markdown_text = strip_html_comments(markdown_text, warnings)
    for s in split_slides(markdown_text):
        if not s.strip():
            continue
        clean_s, footnotes = extract_footnote_definitions(s)
        slides.append(BlockParser(clean_s, footnotes=footnotes, warnings=warnings).parse(allow_title_page=not slides))
    emitter = BeamerEmitter(
        theme, colortheme, fonttheme, innertheme, outertheme,
        text_margin_left=text_margin_left,
        text_margin_right=text_margin_right,
        list_indent_1=list_indent_1,
        list_indent_2=list_indent_2,
        list_indent_3=list_indent_3,
        list_label_sep=list_label_sep,
        list_item_sep=list_item_sep,
        list_top_sep=list_top_sep,
        list_parse_sep=list_parse_sep,
        list_indent=list_indent,
    )
    emitter.warnings.extend(warnings)
    return emitter.emit_document(slides), emitter.warnings

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("input_md", type=Path)
    parser.add_argument("-o","--output", type=Path, required=True)
    parser.add_argument("--warnings", type=Path, default=None)
    parser.add_argument("--theme", type=str, default=None)
    parser.add_argument("--colortheme", type=str, default=None)
    parser.add_argument("--fonttheme", type=str, default=None)
    parser.add_argument("--innertheme", type=str, default=None)
    parser.add_argument("--outertheme", type=str, default=None)
    parser.add_argument("--text-margin-left", default="5mm", metavar="LENGTH",
                        help="left frame text margin (default: 5mm)")
    parser.add_argument("--text-margin-right", default="5mm", metavar="LENGTH",
                        help="right frame text margin (default: 5mm)")
    parser.add_argument("--list-indent", default=None, metavar="LENGTH",
                        help="indentation for every list level")
    parser.add_argument("--list-indent-1", default=None, metavar="LENGTH",
                        help="first-level list indentation (default: 1.5em)")
    parser.add_argument("--list-indent-2", default=None, metavar="LENGTH",
                        help="second-level list indentation (default: 1.25em)")
    parser.add_argument("--list-indent-3", default=None, metavar="LENGTH",
                        help="third-level list indentation (default: 1.1em)")
    parser.add_argument("--list-label-sep", default="0.35em", metavar="LENGTH",
                        help="space between a list marker and its text (default: 0.35em)")
    parser.add_argument("--list-item-sep", default="0.15em", metavar="LENGTH",
                        help="vertical space between list items (default: 0.15em)")
    parser.add_argument("--list-top-sep", default="0.2em", metavar="LENGTH",
                        help="vertical space above and below a list (default: 0.2em)")
    parser.add_argument("--list-parse-sep", default="0pt", metavar="LENGTH",
                        help="vertical space between paragraphs in an item (default: 0pt)")
    args=parser.parse_args()
    md_text=args.input_md.read_text(encoding="utf-8")
    latex, warnings = md_to_beamer(
        md_text, args.theme, args.colortheme, args.fonttheme, args.innertheme, args.outertheme,
        text_margin_left=args.text_margin_left,
        text_margin_right=args.text_margin_right,
        list_indent_1=args.list_indent_1,
        list_indent_2=args.list_indent_2,
        list_indent_3=args.list_indent_3,
        list_label_sep=args.list_label_sep,
        list_item_sep=args.list_item_sep,
        list_top_sep=args.list_top_sep,
        list_parse_sep=args.list_parse_sep,
        list_indent=args.list_indent,
    )
    args.output.write_text(latex, encoding="utf-8")
    if args.warnings is not None: args.warnings.write_text("\n".join(warnings), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

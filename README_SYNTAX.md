# mdBeamer syntax reference

mdBeamer implements a custom Markdown dialect for Beamer presentations. This
reference describes the current implementation in [mdBeamer.py](mdBeamer.py),
including incomplete features and limitations. Examples and observations also
draw on `DBS_future_dev_notes.orig.md` in the parent project.

This reference describes the implemented syntax. The parent project's
`output/DBS_future_dev_notes.orig.tex` and corresponding compilation log confirm
PDF generation with slide font sizes and a table with wrapping columns. A
successful build does not guarantee that every slide fits; see the layout
limitations and build observations below.

## 1. Document and slide structure

A presentation is a UTF-8 Markdown document. A line containing only `---`,
optionally surrounded by whitespace, separates slides:

```markdown
# First slide

Content of the first slide.

---

# Second slide

Content of the second slide.
```

- Headings do not create slides; only `---` does.
- Whitespace-only slide segments are skipped.
- A slide can have no title.
- `---` inside a fenced code block remains code.
- Outside code, `---` always separates slides, including inside a column or
  font-size block.
- YAML front matter is not supported.

### HTML comments

HTML comments are ignored outside fenced code. Both inline and multiline forms
are supported:

```markdown
Visible text <!-- hidden note --> continues here.

<!--
This entire block is ignored, including syntax such as --- or # Heading.
-->
```

Line breaks occupied by comments are preserved, so a comment-only line remains
a block boundary. Inside fenced code, `<!-- ... -->` remains literal code. An
unclosed HTML comment is ignored through the end of the document and produces a
warning.

## 2. Headings

Headings require one to six `#` characters followed by whitespace.

| Syntax | Beamer interpretation |
| --- | --- |
| First top-level heading, `#` through `######` | Frame title, unless the slide qualifies as a title page |
| Following consecutive headings, each deeper than the previous header | Additional frame-header lines (subtitle, subsubtitle, etc.) |
| All other headings | Bold body headings |

Here, “top-level” means outside column and font-size containers.
Blank lines between header lines are allowed. The header sequence continues
while each consecutive heading has more `#` characters than the previous one.
Intervening body content, or a heading of the same or a shallower level, ends
the sequence. Once it ends, all remaining headings belong to the body. Headings
inside containers always remain body content.

The number of `#` characters controls each frame-header line's size:

| Heading level | Header font size |
| --- | --- |
| `#` | `\Large` |
| `##` | `\large` |
| `###` | `\normalsize` |
| `####` | `\small` |
| `#####` | `\footnotesize` |
| `######` | `\scriptsize` |

For example, a slide can start with a smaller title and a still smaller subtitle:

```markdown
---
## Results[fontsize=\tiny]
### Preliminary measurements

The title is large, the subtitle is normalsize, and the body is tiny.
```

The title and additional header lines use their own levels independently of the slide's
body `fontsize` attribute. The theme still controls their color, weight, and
placement. Header-size settings are scoped around the entire frame, including
Beamer's header rendering. Additional header lines are stacked in the theme's
subtitle area, each with its own size. Ordinary body headings
retain their existing bold styling and inherit the body font size; they do not
use this header-size mapping.

This complete example has three header lines followed by two body sections:

```markdown
---
# Slide Title[fontsize=\small]
## Slide subtitle
### Slide subsubtitile

# Some section header here
some text here

## Some subsection header here
some more text and bullets here
---
```

The first three headings appear in the frame header at `\Large`, `\large`, and
`\normalsize`. The next H1 is shallower than the previous H3, so it starts the
body. Both body headings use the existing bold styling at the slide's `\small`
body size. Starting the sequence at `##` or `###` is also supported; levels may
be skipped, for example `###` followed by `#####` and `######`.

```markdown
# Results

## Preliminary measurements

Body content starts here.

### Observations

Some explanatory text.
```

Headings are escaped as plain text; inline Markdown formatting is not interpreted
inside them.

- Indented headings are not recognized.
- A bare `#` is ordinary text.
- Closing hashes are not removed: `# Title #` retains the final `#`.
- A trailing bracketed suffix is treated as heading attributes and removed,
  even when it contains no recognized attribute. Literal titles ending in
  `[something]` are therefore problematic.

## 3. Title pages and metadata

The converter automatically recognizes this structure:

```markdown
# Presentation title
## Optional subtitle

- Author: Todor Ivanov
- Affiliation: University of Notre Dame
- Date: 09-09-2026
```

The title is required. The subtitle and metadata list are optional.

| Key | Output |
| --- | --- |
| `Author:` | `\author{...}` |
| `Affiliation:` | `\institute{...}` |
| `Institute:` | Alias for `Affiliation:` |
| `Date:` | `\date{...}` |

Metadata keys are case-insensitive. Values are plain text.

Recognition requires the slide to contain exactly:

1. An H1 heading.
2. An optional H2 heading.
3. An optional bullet list containing only recognized metadata items.

Extra paragraphs, images, or unrecognized metadata items prevent title-page
recognition.

**Only the first nonempty slide is eligible for automatic title-page recognition.**
If it contains only `# Title`, it becomes a title page. Later title-only slides
are ordinary frames, even if they match the title-page structure.

The opening title page supplies document-wide metadata. If it has no date, the
converter explicitly sets an empty date.

## 4. Paragraphs and inline formatting

Consecutive ordinary text lines are joined with spaces:

```markdown
This sentence starts here
and continues on the next line.
```

Blank lines separate parsed paragraphs. Markdown hard line breaks using trailing
spaces are not implemented.

| Syntax | Output |
| --- | --- |
| `**bold**` | Bold text |
| `*italic*` | Emphasized text |
| `` `code` `` | Monospaced text |
| `[label](https://example.org)` | Hyperlink |
| `[^key]` | Footnote reference |

Inline formatting works in paragraphs, list items, link labels, and table cells.

Limitations:

- `_italic_` and `__bold__` are unsupported.
- Strikethrough is unsupported.
- Multi-backtick inline code is unsupported.
- Complex nesting and escaped delimiters are not reliably supported.
- Links use simple matching; nested parentheses in URLs are not handled correctly.
- Reference-style links such as `[GitHub][1]` are unsupported.
- Bare URLs are not explicitly converted into hyperlinks.
- Markdown backslash escapes are not implemented.

Ordinary text has LaTeX special characters escaped, including `\`, `{`, `}`,
`$`, `&`, `%`, `#`, `_`, `^`, and `~`. Raw LaTeX commands and mathematical
expressions therefore do not pass through as executable LaTeX.

## 5. Lists

Unordered lists accept `-`, `+`, or `*`:

```markdown
- First item
- Second item
  * Nested item
  * Another nested item
```

Ordered lists accept digits followed by a period:

```markdown
1. First step
2. Second step
   1. Nested step
```

- Increased indentation creates nesting.
- There is no fixed two-space or four-space requirement.
- An indented continuation line is joined to the item with a space.
- Source numbering is discarded; Beamer generates numbering.
- Blank lines do not necessarily terminate a list.
- Different unordered markers can be mixed.

Limitations:

- Mixing ordered and unordered lists does not reliably produce the intended
  nesting.
- Lists cannot contain arbitrary nested block content such as images, tables,
  or code blocks.
- Nesting beyond three levels produces a warning and flattened text at the
  next level.
- Descendants below that flattened level are not emitted.

For predictable output, use one list type within each nested list structure and
limit nesting to three levels.

## 6. Fenced code blocks

Both backticks and tildes are supported:

````markdown
```Python
if ready:
    print("Ready")
```
````

```markdown
~~~Python
print("Ready")
~~~
```

The language is optional:

````markdown
```
plain code or terminal output
```
````

A code block becomes a LaTeX `lstlisting`. Frames containing code, including code
inside columns or font-size blocks, automatically receive Beamer's `fragile`
option.

Generated listings use monospaced text, automatic line wrapping, preserved
spaces, a thin frame, a light background, and `\small` by default.

Language names are passed directly to LaTeX `listings`; the converter does not
validate or translate them.

Use exactly three fence characters. Closing fences must match the opening fence
type and contain only those three characters, apart from surrounding whitespace.
An unclosed code block consumes the remaining input and can also prevent
subsequent slide separators from being recognized.

## 7. Font sizes

The working general-purpose syntax is a scoped block:

```markdown
::: fontsize=\small

A smaller paragraph.

- First item
- Second item

:::
```

Supported commands are case-sensitive:

```text
\tiny
\scriptsize
\footnotesize
\small
\normalsize
\large
\Large
\LARGE
\huge
\Huge
```

Quoted values are also accepted:

```markdown
::: fontsize="\footnotesize"

Content.

:::
```

These blocks may contain other blocks, including columns and code. An unsupported
size produces a warning and falls back to `\normalsize`.

Code blocks can override the surrounding size:

````markdown
::: fontsize=\small

```Python[fontsize=\tiny]
print("Smaller code")
```

:::
````

Code font-size precedence is:

1. The code fence's `fontsize` attribute.
2. The surrounding font-size block.
3. The slide's font size.
4. Default `\small`.

The bracket must immediately follow the language:

```text
Python[fontsize=\tiny]
```

A space between the language and `[` prevents the intended attribute parsing.
Code font-size values use the same supported-command list. Invalid sizes produce
a warning and fall back to `\normalsize`.

### Slide font size

Set the default body size on the heading used as the frame title:

```markdown
---
# Main assumptions[fontsize=\tiny]

This paragraph and the following list use the slide size.

- First point
- Second point
```

The attribute is removed from the displayed title. It applies to body paragraphs,
body headings, lists (including nested lists), code, and tables unless a local
size overrides it. Frame-title and frame-subtitle sizes follow their heading
levels; their other styling comes from the theme.
The size is scoped to the frame and does not carry into the next slide.

An enclosing `::: fontsize=...` block overrides the slide size. An explicit code
or table size overrides that enclosing block. All these sizes are validated
against the commands listed above; an invalid command warns and uses
`\normalsize`.

Table font-size precedence is:

1. The table directive's `fontsize` attribute.
2. The surrounding font-size block.
3. The slide's font size.
4. Default `\scriptsize`.

### Unsupported legacy directive

The code also defines recognition for:

```markdown
::: slidefontsize=\tiny
```

However, that recognizer is never called by the block parser. This is not a
working directive.

Use the slide-title attribute or a scoped `fontsize` block instead.

## 8. Images

Images must occupy their own line:

```markdown
![Description](png/diagram.png)
```

Optional dimensions follow immediately after the closing parenthesis:

```markdown
![Description](png/diagram.png){width=0.95 height=0.75\textheight}
```

Supported attributes are `width` and `height`, separated by whitespace. Simple
quoted values are accepted.

| Dimension form | Meaning |
| --- | --- |
| `0.95` | `0.95\linewidth` |
| `95%` | `0.95\linewidth` |
| `0.8\linewidth` | Explicit relative dimension |
| `0.8\textwidth` | Explicit relative dimension |
| `0.7\textheight` | Explicit relative dimension |
| `8cm`, `40mm`, `2in`, `100pt`, `5em`, `3ex` | Explicit length |

Defaults:

- Width: `0.95\linewidth`.
- Height: unspecified.
- Aspect ratio: always preserved.

Both width and height act as bounds when supplied together.

**A bare number or percentage uses `\linewidth` even for `height`.** Use
`height=0.75\textheight` when you mean a fraction of page text height.

Unsupported dimensions produce warnings and revert to the corresponding default.

Alt text is not displayed as a caption. Inline images, image titles, downloads,
and image conversion are not implemented; paths are passed to `\includegraphics`.

## 9. Automatic image-and-text columns

A placement suffix inside image alt text requests a two-column layout:

```markdown
# Architecture

- First observation
- Second observation

![Architecture left:40%](png/architecture.png){width=1.0}
```

Supported suffixes:

```text
Description left
Description right
Description left:40%
Description right:35%
```

Placement words are case-insensitive.

The converter:

- Puts the image on the requested side.
- Uses the specified percentage for its column.
- Uses the remaining percentage for all other slide-body blocks.
- Defaults to 40% image and 60% text.
- Top-aligns both columns.

The percentage controls the **column width**; `{width=...}` separately controls
the image within it.

Automatic layout requires:

- Exactly one positioned image at the slide-body level.
- At least one other body block.
- No explicit `Columns` block at the slide-body level.

All remaining body content is moved into the other column, regardless of its
original position relative to the image. All opening header lines are extracted
before this layout step and remain frame headers. Other headings stay in the
body and move with the other body content.

Use descriptive alt text before the placement suffix, as shown above.

## 10. Explicit columns

```markdown
# Comparison

::: columns

::: column width=60% valign=top

### Explanation

- First point
- Second point

:::

::: column width=40% valign=top

![Diagram](png/diagram.png){width=1.0}

:::

:::
```

Each column has its own closing `:::`, followed by another closing `:::` for the
columns container.

| Attribute | Accepted values | Default |
| --- | --- | --- |
| `width` | Percentages such as `40%`; fractions such as `2/5` | Equal share |
| `valign` | `top`, `t`, `center`, `c`, `bottom`, `b` | `top` |

Column widths become fractions of `\textwidth`.

A bare decimal such as `width=0.4` is **not** supported for columns, although it
works for image dimensions.

- Attribute values may be quoted.
- Use `width=40%`, with no spaces around `=`.
- Invalid width or alignment values generate warnings and use defaults.
- Widths are not normalized or checked to ensure they total 100%.
- Content inside `::: columns` but outside a declared column is skipped.
- Explicit columns can contain paragraphs, lists, images, tables, code, and
  font-size blocks.

Column and font-size containers support nested directives, including table
directives. Their body collection preserves directive-looking lines inside
fenced code. An unclosed column, font-size, or table body is closed at the end
of the slide with a warning. Always balance the closing delimiters explicitly.

## 11. Tables

Pipe tables require a header followed immediately by a separator row:

```markdown
| Name | Count |
| --- | ---: |
| Alpha | 42 |
| Beta | 17 |
```

Outer pipes are optional for multi-column rows:

```markdown
Name | Count
--- | ---
Alpha | 42
```

Separator cells require at least three hyphens. Alignment is honored:

| Separator | Alignment |
| --- | --- |
| `---` or `:---` | Left |
| `:---:` | Center |
| `---:` | Right |

Tables have bold headers, a shaded header and alternating row shading, and a
horizontal rule below the header. Their font size follows the precedence in
section 7; it defaults to `\scriptsize` only when no size is specified or inherited.

### Table attributes and wrapping columns

Wrap exactly one pipe table in a table directive:

```markdown
::: table fontsize=\tiny width=100% widths="20%,20%,60%"

| Source | Status | Description |
| :--- | :---: | :--- |
| DBS | Integrated | A longer description wraps inside its allocated column. |

:::
```

| Attribute | Meaning | Default |
| --- | --- | --- |
| `fontsize` | Local table font-size command | Inherited size, or `\scriptsize` |
| `width` | Overall table width: percentage of `\linewidth`, or a native LaTeX length/expression | `\linewidth` when `widths` is given |
| `widths` | Comma-separated column percentages of the available content width | Equal shares when `width` is given |

Attribute values may be single- or double-quoted. Use no spaces around `=`.
Quote `widths` if it contains spaces, for example `widths="20%, 20%, 60%"`.

- Supplying either `width` or `widths` enables wrapping paragraph columns.
- Supplying neither keeps natural-width columns without automatic wrapping,
  even if the directive specifies `fontsize`.
- Overall width has no converter-imposed range limit. Percentages such as `120%`
  are translated to multiples of `\linewidth`. Other values are passed directly
  to LaTeX's `\setlength`, without escaping, clamping, or a replacement default.
  LaTeX interprets their validity and units; a bare `1.2` does not automatically
  mean `1.2\linewidth`.
- Column percentages must be positive, match the number of header cells, and
  total 100% (allowing a small rounding tolerance of 0.001 percentage points).
- Column proportions apply after subtracting cell padding from the overall
  width. The usual padding is 4pt per cell side. For extremely narrow tables,
  padding is removed if it would leave less than 1pt of total content width.
- Inside a Beamer column, `width=100%` uses that column's available line width.
- Font-size blocks may surround a table directive; table directives may appear
  inside explicit columns.
- A table directly following a paragraph is recognized without requiring a
  blank line, although blank lines make the source easier to read.

Invalid native LaTeX widths are diagnosed by LaTeX during compilation, not
replaced by the converter. Invalid column proportions warn and fall back to
equal shares. Unknown or malformed attributes warn. If a
table directive does not contain exactly one pipe table, its attributes are
ignored with a warning and its parsed content is retained.

### Widths greater than 100% and intentional overflow

This example requests a table at **120% of the available line width**, directly:

```markdown
::: table fontsize=\tiny width=120% widths="20%,20%,60%"
```

The converter generates
`\setlength{\mdBeamerTableWidth}{1.2\linewidth}`. No enclosing `::: column`
directive is needed. The internal `widths` values remain proportions of the
table's content width after padding; they still total 100%.

Native LaTeX lengths and expressions are also supported:

```markdown
::: table width=1.2\linewidth widths="20%,20%,60%"
```

```markdown
::: table width=12cm widths="20%,20%,60%"
```

```markdown
::: table width="\dimexpr\linewidth + 2cm\relax" widths="20%,20%,60%"
```

These examples show alternative opening directives; each still requires its
pipe table and closing `:::`. Quote expressions containing spaces. Length macros
must be defined in the generated document or its loaded packages.

The emitter retains its existing `center` environment; there is no additional
overflow-placement control or guarantee of equal overflow into both margins.
LaTeX can report an overfull box for an intentionally oversized table. Material
extending beyond the physical page boundary will not be visible. Omitting both
width attributes also allows natural-width overflow, but loses wrapping and
column-proportion control.

### Table limitations and diagnostics

- Wrapping is enabled only by width attributes; there is no automatic font
  shrinking or pagination to fit a slide.
- Long unbreakable content can still overflow a wrapping column.
- Wider columns can reduce wrapping and table height, but do not guarantee
  that the table fits vertically.
- Multiline Markdown cells and escaped pipes (including pipes inside inline
  code) are unsupported.
- Missing row cells are padded and extra cells discarded, with warnings.
- A separator/header column-count mismatch also produces a warning.
- Table parsing continues through subsequent nonblank lines containing `|`,
  stopping at recognized directive boundaries or another separator row.

## 12. Footnotes

```markdown
# Example

This statement has a source.[^source]

[^source]: Source description or URL.
```

Definitions must start at the beginning of a line. Continuations may use four
spaces or a tab:

```markdown
[^source]: First part.
    Continuation of the same footnote.
```

- Definitions apply only to their own slide.
- They may precede or follow references.
- Repeated definitions of the same key use the last value.
- Undefined references produce empty footnotes without warnings.
- Definition text is escaped as plain text; inline formatting and hyperlink
  syntax are not processed.
- Footnote extraction happens before block parsing and is not code-fence-aware.

Outside columns, references become ordinary `\footnote{...}` commands.

Inside columns:

- References use superscript letters.
- Footnote text appears below the columns in `\tiny`.
- Identical footnote text is deduplicated within that columns block.
- Marks become numeric after the first 26 entries.

## 13. Command-line interface

From the `mdBeamer/` directory, generate TeX with:

```bash
python3 mdBeamer.py presentation.md \
  -o presentation.tex \
  --theme Warsaw \
  --warnings presentation.warnings.txt
```

| Argument | Purpose |
| --- | --- |
| `input_md` | Input Markdown file |
| `-o`, `--output` | Required output TeX path |
| `--warnings` | Optional warnings file |
| `--theme` | Beamer theme |
| `--colortheme` | Beamer color theme |
| `--fonttheme` | Beamer font theme |
| `--innertheme` | Beamer inner theme |
| `--outertheme` | Beamer outer theme |
| `-h`, `--help` | Usage information |

The Python script writes a complete Beamer document. It does not compile the
PDF or create missing output directories. Collected warnings are written only
when `--warnings` is supplied; they are not printed to the terminal.

The wrappers provide additional workflows:

- [mdBeamer.sh](mdBeamer.sh): generates TeX beside the source, compiles with
  LuaLaTeX, and opens the PDF in Atril.
- [preview.sh](preview.sh): writes under the source directory's `output/`, builds
  with `latexmk -pdf`, and watches the Markdown source for changes. Image-only
  changes do not trigger a rebuild.

Changes to the converter itself also do not trigger a running preview. After
updating `mdBeamer.py`, restart the preview or change and save the Markdown input
to regenerate the TeX and PDF.

Pass the input file first, followed by converter options:

```bash
./mdBeamer.sh test/DBS_future_dev_notes.md --theme Warsaw
./preview.sh test/DBS_future_dev_notes.md --theme Warsaw
```

## 14. Observations from the example document

These observations refer to `DBS_future_dev_notes.orig.md` in the parent project
and the build artifacts inspected on 2026-09-10.

| Example | Current behavior |
| --- | --- |
| Opening title, subtitle, and metadata | Recognized as a title page |
| `# Main assumptions[fontsize=\tiny]` | Attribute removed from title; body and nested lists receive `\tiny` |
| `![CMS Data Model left:40%](...)` | Automatic 40% image / 60% content columns |
| `### empty slides` | Ordinary frame with a normalsize title |
| Bare `#` | Untitled frame containing a literal `#` |
| Explicit columns in “Backup slides” | Uses declared 60% / 40% widths |
| Code with a valid explicit `fontsize` | Overrides the surrounding size |
| Code with `[fontsize=\sssmall]` | Invalid command; falls back to `\normalsize` with a warning |
| Unclosed `fontsize=\small` in “Test column” | Extends to the end of that slide with a warning |
| Table with `width=120% widths="20%,20%,60%"` | Now emits `1.2\linewidth` with wrapping and 20/20/60 proportions; the previously inspected build used the former 100% fallback |
| `[GitHub][1]` and similar table links | Remain literal text |
| `[1]: ...` reference definitions | Remain ordinary body text |
| `[^1]` in “First scenario” | Undefined on that slide, so emits an empty footnote |
| Deeply nested lists | Flattening beyond level three; deeper descendants can be omitted |

`output/DBS_future_dev_notes.orig.log` reports successful PDF output. Its generated
TeX contains the new slide-size commands and wrapping table columns. The log
also reports vertical overflow, including roughly 95pt for the wide-table slide;
successful compilation does not establish that all slide content is visible.
Those artifacts predate removal of the overall-width limit; they do not validate
the new 120% output. Regenerate the TeX and PDF to apply the change.

The separately inspected `output/DBS_future_dev_notes.tex` still contains the
older centered natural-width table output and lacks the new slide-size commands.
It should not be used as evidence that the updated converter was applied to that
document.

## 15. Features outside the implemented dialect

The current parser does not implement blockquotes, task checkboxes, HTML, math,
raw LaTeX blocks, reference links, automatic section navigation, Beamer overlays
or pauses, speaker notes, arbitrary frame options, captions, or automatic
pagination.

Unsupported syntax is generally treated as ordinary text, partially interpreted,
or silently ignored. The warnings file covers selected font-size, dimension,
alignment, list-depth, table-attribute, row-shape, and unclosed-container problems;
it is not a full syntax validator. LaTeX layout warnings appear separately in the
compilation log.

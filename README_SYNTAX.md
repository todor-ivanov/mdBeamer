# mdBeamer syntax reference

mdBeamer implements a custom Markdown dialect for Beamer presentations. This
reference describes the current implementation in [mdBeamer.py](mdBeamer.py),
including incomplete features and limitations. Examples and observations also
draw on `DBS_future_dev_notes.orig.md` in the parent project.

This reference is based on static code analysis, not execution of the converter
or PDF compilation. Behavior described as incomplete should not be treated as
working syntax.

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

## 2. Headings

Headings require one to six `#` characters followed by whitespace.

| Syntax | Beamer interpretation |
| --- | --- |
| First top-level `# Title` in a slide | Frame title, unless the slide qualifies as a title page |
| First top-level `## Subtitle` in an ordinary slide | Frame subtitle |
| Further `#` or `##` headings | Bold body headings |
| `###` through `######` | Bold body headings, all rendered alike |

Here, “top-level” means outside column and font-size containers.

```markdown
# Results

## Preliminary measurements

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

**A slide containing only `# Title` also becomes a title page.** Recognition is
not restricted to the first slide.

The first recognized title page supplies document-wide metadata. Any later
recognized title pages emit `\titlepage` using that same metadata. If the
recognized title page has no date, the converter explicitly sets an empty date.

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
3. Default `\small`.

The bracket must immediately follow the language:

```text
Python[fontsize=\tiny]
```

A space between the language and `[` prevents the intended attribute parsing.
Code font-size values are not validated against the supported-command list.

Tables independently force `\scriptsize`, overriding an enclosing size.

### Incomplete slide-size syntax

The example document contains:

```markdown
# Main assumptions[fontsize=\tiny]
```

The parser recognizes and removes the attribute, but discards it before the
slide-level font-size logic reads it. **It currently has no font-size effect.**

The code also defines recognition for:

```markdown
::: slidefontsize=\tiny
```

However, that recognizer is never called by the block parser. This is not a
working directive.

To size ordinary slide content, put the body inside a `fontsize` block while
keeping the slide title outside it.

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
original position relative to the image. An H2 moved there becomes a bold body
heading rather than a frame subtitle.

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

The parser attempts to support nested containers, but delimiter processing is
not code-fence-aware. Literal directive lines inside code nested in a container
can interfere with parsing. Properly balanced, simple containers are the
reliable authoring pattern.

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

Separator cells require at least three hyphens and may have alignment colons.

**Current output ignores parsed alignment: all columns are centered.**

Tables are rendered with bold headers, `\scriptsize` text, a shaded header and
alternating row shading, a horizontal rule below the header, and fixed
inter-column padding.

Limitations:

- No automatic text wrapping or fit-to-slide scaling.
- No multiline cells.
- No escaped pipe handling, including pipes inside inline code.
- Missing row cells are padded with empty cells.
- Extra row cells are discarded.
- Table parsing continues through subsequent nonblank lines containing `|`.
- A blank line before a table is advisable: a table immediately following
  ordinary paragraph text can be absorbed into the paragraph.

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

Pass the input file first, followed by converter options:

```bash
./mdBeamer.sh test/DBS_future_dev_notes.md --theme Warsaw
./preview.sh test/DBS_future_dev_notes.md --theme Warsaw
```

## 14. Observations from the example document

These observations refer to `DBS_future_dev_notes.orig.md` in the parent project.
They are inferred from the implementation, not from a compiled rendering.

| Example | Current behavior |
| --- | --- |
| Opening title, subtitle, and metadata | Recognized as a title page |
| `# Main assumptions[fontsize=\tiny]` | Attribute removed; font size unchanged |
| `![CMS Data Model left:40%](...)` | Automatic 40% image / 60% content columns |
| `### empty slides` | Untitled frame containing a bold heading |
| Bare `#` | Untitled frame containing a literal `#` |
| Explicit columns in “Backup slides” | Uses declared 60% / 40% widths |
| Code with `[fontsize=\huge]` inside `fontsize=\tiny` | Code's explicit size overrides the surrounding size |
| Unclosed `fontsize=\small` in “Test column” | Extends to the end of that slide without a warning |
| Wide table | No wrapping or fitting mechanism; overflow is likely |
| `[GitHub][1]` and similar table links | Remain literal text |
| `[1]: ...` reference definitions | Remain ordinary body text |
| `[^1]` in “First scenario” | Undefined on that slide, so emits an empty footnote |
| Deeply nested lists | Flattening beyond level three; deeper descendants can be omitted |

## 15. Features outside the implemented dialect

The current parser does not implement blockquotes, task checkboxes, HTML, math,
raw LaTeX blocks, reference links, automatic section navigation, Beamer overlays
or pauses, speaker notes, arbitrary frame options, captions, or automatic
pagination.

Unsupported syntax is generally treated as ordinary text, partially interpreted,
or silently ignored. The warnings file covers only selected font-size,
dimension, alignment, and list-depth problems; it is not a full syntax validator.

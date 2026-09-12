"""Regression and real TeX compilation checks: python3 -m unittest discover -s test."""
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mdbeamer", ROOT / "mdBeamer.py")
md = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = md
spec.loader.exec_module(md)


class SyntaxTests(unittest.TestCase):
    def convert(self, source, **kwargs):
        return md.md_to_beamer(source, **kwargs)

    def test_slide_title_attributes_and_title_only_frames(self):
        tex, warnings = self.convert("# Opening\n---\n# Later[fontsize=\\tiny]\n---\nBefore\n\n# Content[fontsize=\\small]\nBody")
        self.assertEqual(tex.count(r"\titlepage"), 1)
        self.assertIn("\\begin{frame}{Later}\n\\tiny", tex)
        self.assertIn("\\begin{frame}{Content}\n\\small", tex)
        self.assertNotIn("fontsize=", tex)
        self.assertEqual(warnings, [])

    def test_title_page_author_affiliation_references(self):
        source = '''# Presentation
## Subtitle

- Author: Alice Smith[^university]
- Author: Bob Jones[^university][^laboratory]
- Affiliation: [^university] Department of Physics, Example University, [^laboratory] National Research Laboratory
- Date: 2026-09-11'''
        tex, warnings = self.convert(source)
        self.assertIn(r"\author{Alice Smith\inst{1} \and Bob Jones\inst{1,2}}", tex)
        self.assertIn(r"\institute{\inst{1} Department of Physics, Example University, \quad \inst{2} National Research Laboratory}", tex)
        self.assertEqual(warnings, [])

    def test_affiliation_logos_are_added_to_every_frame_header(self):
        source = '''# Presentation

- Author: Alice Smith[^university]
- Affiliation: [^university] Example University
- Affiliation-Logo: [^university] ![University](logos/university.pdf){height=7mm}
- Affiliation-Logo: [^university] ![Department](logos/department.png){width=12mm}
- Affiliation-Logo: [^university] ![Seal](logos/seal.jpg)'''
        tex, warnings = self.convert(source)
        self.assertIn(r"\usepackage{tikz}", tex)
        self.assertIn(r"\newcommand{\mdBeamerHeaderLogos}", tex)
        self.assertIn(r"\includegraphics[height=7mm,keepaspectratio]{logos/university.pdf}", tex)
        self.assertIn(r"\includegraphics[width=12mm,keepaspectratio]{logos/department.png}", tex)
        self.assertIn(r"\includegraphics[height=6mm,keepaspectratio]{logos/seal.jpg}", tex)
        self.assertIn(r"\AddToHook{shipout/foreground}", tex)
        self.assertNotIn(r"\addtobeamertemplate{headline}", tex)
        self.assertIn(r"at (current page.north east) {\mdBeamerHeaderLogos};", tex)
        self.assertEqual(warnings, [])

    def test_title_page_affiliation_reference_warnings(self):
        source = '''# Presentation

- Author: Alice Smith[^missing]
- Affiliation: [^unused] Example University
- Institute: [^unused] Duplicate University
- Affiliation-Logo: [^missing] ![Missing](logos/missing.png)
- Affiliation-Logo: malformed'''
        _, warnings = self.convert(source)
        self.assertTrue(any("Undefined title-page affiliation reference: missing" in warning
                            for warning in warnings))
        self.assertTrue(any("Unused title-page affiliation label: unused" in warning
                            for warning in warnings))
        self.assertTrue(any("Duplicate title-page affiliation label: unused" in warning
                            for warning in warnings))
        self.assertTrue(any("Undefined affiliation for title-page logo: missing" in warning
                            for warning in warnings))
        self.assertTrue(any("Malformed Affiliation-Logo metadata: malformed" in warning
                            for warning in warnings))

    def test_unlabeled_title_page_metadata_remains_supported(self):
        source = '''# Presentation

- Author: Alice Smith
- Institute: Example University'''
        tex, warnings = self.convert(source)
        self.assertIn(r"\author{Alice Smith}", tex)
        self.assertIn(r"\institute{Example University}", tex)
        self.assertEqual(warnings, [])

    def test_navigation_symbols_are_disabled(self):
        tex, warnings = self.convert("# Slide\nBody")
        self.assertIn(r"\setbeamertemplate{navigation symbols}{}", tex)
        self.assertLess(tex.index(r"\setbeamertemplate{navigation symbols}{}"),
                        tex.index(r"\begin{document}"))
        self.assertIn(r"\setbeamertemplate{page number in head/foot}[totalframenumber]", tex)
        self.assertLess(tex.index(r"\setbeamertemplate{page number in head/foot}[totalframenumber]"),
                        tex.index(r"\begin{document}"))
        self.assertEqual(warnings, [])

    def test_compact_layout_defaults_are_emitted(self):
        tex, warnings = self.convert("# Lists\n- One\n  - Two\n    - Three")
        preamble = tex[:tex.index(r"\begin{document}")]
        self.assertIn(r"\setbeamersize{text margin left=5mm,text margin right=5mm}", preamble)
        self.assertIn(r"\setlength{\leftmargini}{1.5em}", preamble)
        self.assertIn(r"\setlength{\leftmarginii}{1.25em}", preamble)
        self.assertIn(r"\setlength{\leftmarginiii}{1.1em}", preamble)
        self.assertIn(r"\setlength{\labelsep}{0.35em}", preamble)
        self.assertIn(r"\def\@listi{\leftmargin\leftmargini\labelwidth\leftmargini\advance\labelwidth-\labelsep\topsep0.2em\parsep0pt\itemsep0.15em\partopsep0pt}", preamble)
        self.assertEqual(tex.count(r"\setlength{\itemsep}{0.15em}"), 3)
        self.assertEqual(tex.count(r"\setlength{\topsep}{0.2em}"), 3)
        self.assertEqual(tex.count(r"\setlength{\parsep}{0pt}"), 3)
        self.assertEqual(warnings, [])

    def test_layout_values_can_be_customized(self):
        tex, warnings = self.convert(
            "# Lists\n- One",
            text_margin_left="3mm", text_margin_right="4mm",
            list_indent_1="1em", list_indent_2="0.9em", list_indent_3="0.8em",
            list_label_sep="0.2em", list_item_sep="1pt",
            list_top_sep="2pt", list_parse_sep="0",
        )
        self.assertIn(r"\setbeamersize{text margin left=3mm,text margin right=4mm}", tex)
        self.assertIn(r"\setlength{\leftmargini}{1em}", tex)
        self.assertIn(r"\setlength{\leftmarginii}{0.9em}", tex)
        self.assertIn(r"\setlength{\leftmarginiii}{0.8em}", tex)
        self.assertIn(r"\setlength{\labelsep}{0.2em}", tex)
        self.assertIn(r"\setlength{\itemsep}{1pt}", tex)
        self.assertIn(r"\setlength{\topsep}{2pt}", tex)
        self.assertIn(r"\setlength{\parsep}{0pt}", tex)
        self.assertEqual(warnings, [])

    def test_common_list_indent_applies_to_every_level_with_specific_overrides(self):
        tex, warnings = self.convert("# Lists\n- One", list_indent="1.2em")
        self.assertIn(r"\setlength{\leftmargini}{1.2em}", tex)
        self.assertIn(r"\setlength{\leftmarginii}{1.2em}", tex)
        self.assertIn(r"\setlength{\leftmarginiii}{1.2em}", tex)
        self.assertEqual(warnings, [])

        tex, warnings = self.convert(
            "# Lists\n- One", list_indent="1.2em", list_indent_2="0.9em"
        )
        self.assertIn(r"\setlength{\leftmargini}{1.2em}", tex)
        self.assertIn(r"\setlength{\leftmarginii}{0.9em}", tex)
        self.assertIn(r"\setlength{\leftmarginiii}{1.2em}", tex)
        self.assertEqual(warnings, [])

    def test_invalid_layout_values_warn_and_use_defaults(self):
        tex, warnings = self.convert(
            "# Lists\n- One", text_margin_left="-2mm", list_indent_1="wide",
            list_item_sep="2", list_top_sep=r"1\baselineskip",
        )
        self.assertIn(r"\setbeamersize{text margin left=5mm,text margin right=5mm}", tex)
        self.assertIn(r"\setlength{\leftmargini}{1.5em}", tex)
        self.assertIn(r"\setlength{\itemsep}{0.15em}", tex)
        self.assertIn(r"\setlength{\topsep}{0.2em}", tex)
        self.assertEqual(len(warnings), 4)
        self.assertTrue(all(warning.startswith("Invalid ") for warning in warnings))

    def test_natural_table_alignment_and_paragraph_boundary(self):
        tex, warnings = self.convert("# Table\nText\n| A | B | C |\n| :--- | :---: | ---: |\n| a | b | c |")
        self.assertIn(r"\begin{tabular}{lcr}", tex)
        self.assertEqual(warnings, [])

    def test_combined_bold_and_italic_inline_syntax(self):
        source = ("# Inline\n_underscore italic_ and __underscore bold__\n"
                  "***triple stars*** and ___triple underscores___\n"
                  "**_bold outside_** and __*bold outside again*__\n"
                  "*__italic outside__* and _**italic outside again**_")
        tex, warnings = self.convert(source)
        self.assertIn(r"\emph{underscore italic}", tex)
        self.assertIn(r"\textbf{underscore bold}", tex)
        self.assertIn(r"\textbf{\emph{triple stars}}", tex)
        self.assertIn(r"\textbf{\emph{triple underscores}}", tex)
        self.assertIn(r"\textbf{\emph{bold outside}}", tex)
        self.assertIn(r"\textbf{\emph{bold outside again}}", tex)
        self.assertIn(r"\emph{\textbf{italic outside}}", tex)
        self.assertIn(r"\emph{\textbf{italic outside again}}", tex)
        self.assertNotIn("***", tex)
        self.assertNotIn("___", tex)
        self.assertEqual(warnings, [])

    def test_inline_and_display_math_are_emitted_without_escaping(self):
        source = r'''# Math
Inline $E^2 = p^2c^2 + m^2c^4$ equation.

$$f(x) = \frac{1}{\sigma \sqrt{2\pi}}$$

$$
\begin{aligned}
a &= b + c \\
d &= e_f
\end{aligned}
$$'''
        tex, warnings = self.convert(source)
        self.assertIn(r"Inline $E^2 = p^2c^2 + m^2c^4$ equation.", tex)
        self.assertIn("\\[\nf(x) = \\frac{1}{\\sigma \\sqrt{2\\pi}}\n\\]", tex)
        self.assertIn("\\[\n\\begin{aligned}\na &= b + c \\\\\nd &= e_f\n\\end{aligned}\n\\]", tex)
        self.assertNotIn(r"\textbackslash{}frac", tex)
        self.assertNotIn(r"\textasciicircum{}", tex)
        self.assertEqual(warnings, [])

    def test_unclosed_display_math_is_emitted_with_warning(self):
        tex, warnings = self.convert("# Math\n$$\nx^2 + y^2")
        self.assertIn("\\[\nx^2 + y^2\n\\]", tex)
        self.assertTrue(any("Unclosed display math block" in warning for warning in warnings))

    def test_all_heading_levels_can_be_frame_titles(self):
        sizes = (r"\Large", r"\large", r"\normalsize", r"\small", r"\footnotesize", r"\scriptsize")
        for level, size in enumerate(sizes, start=1):
            with self.subTest(level=level):
                tex, warnings = self.convert('#' * level + ' Title[fontsize=\\tiny]\nBody')
                self.assertIn(r"\begin{frame}{Title}", tex)
                self.assertIn(r"\setbeamerfont{frametitle}{size=" + size + "}", tex)
                self.assertIn("\\tiny\n", tex)
                self.assertEqual(warnings, [])

    def test_subtitle_requires_an_adjacent_deeper_heading(self):
        for following, subtitle in (("### Sub", True), ("#### Sub", True),
                                    ("## Body heading", False), ("# Body heading", False),
                                    ("Paragraph\n\n### Body heading", False)):
            with self.subTest(following=following):
                tex, warnings = self.convert("## Title\n\n" + following + "\n\nContent")
                self.assertEqual(r"\framesubtitle{" in tex, subtitle)
                self.assertEqual(warnings, [])

    def test_headers_survive_automatic_columns(self):
        tex, warnings = self.convert('## Title\n### Sub\n\nText\n\n![Image left](figure.png)')
        self.assertIn(r"\framesubtitle{\mdBeamerHeaderLine{\normalsize}{Sub}}", tex)
        self.assertLess(tex.index(r"\framesubtitle{"), tex.index(r"\begin{columns}"))
        self.assertEqual(warnings, [])

    def test_header_sizes_are_scoped_around_frame_not_inside_body(self):
        tex, warnings = self.convert('## Small title\n### Subtitle\n\nBody\n---\n# Larger title\nBody')
        smaller_setting = tex.index(r"\setbeamerfont{frametitle}{size=\large}")
        smaller_frame = tex.index(r"\begin{frame}{Small title}")
        self.assertLess(tex.index(r"\begingroup"), smaller_setting)
        self.assertLess(smaller_setting, smaller_frame)
        self.assertIn("\\end{frame}\n\\endgroup\n\\begingroup", tex)
        self.assertLess(tex.index(r"\setbeamerfont{frametitle}{size=\Large}"),
                        tex.index(r"\begin{frame}{Larger title}"))
        self.assertEqual(warnings, [])

    def test_multiple_header_lines_and_body_section_headings(self):
        source = r'''---
# Slide Title[fontsize=\small]
## Slide subtitle
### Slide subsubtitile

# Some section header here
some text here

## Some subsection header here
some more text and bullets here
---'''
        tex, warnings = self.convert(source)
        self.assertIn(r"\begin{frame}{Slide Title}", tex)
        self.assertIn("\\framesubtitle{\\mdBeamerHeaderLine{\\large}{Slide subtitle}\n"
                      "\\mdBeamerHeaderLine{\\normalsize}{Slide subsubtitile}}", tex)
        self.assertNotIn(r"\textbf{Slide subsubtitile}", tex)
        self.assertIn(r"\textbf{Some section header here}", tex)
        self.assertIn(r"\textbf{Some subsection header here}", tex)
        self.assertEqual(warnings, [])

    def test_header_sequence_can_start_deeper_and_skip_levels(self):
        tex, warnings = self.convert('### Title\n##### Subtitle\n###### Detail\n\n## Section\nBody')
        self.assertIn(r"\begin{frame}{Title}", tex)
        self.assertIn(r"\setbeamerfont{frametitle}{size=\normalsize}", tex)
        self.assertIn("\\framesubtitle{\\mdBeamerHeaderLine{\\footnotesize}{Subtitle}\n"
                      "\\mdBeamerHeaderLine{\\scriptsize}{Detail}}", tex)
        self.assertIn(r"\textbf{Section}", tex)
        self.assertEqual(warnings, [])

    def test_container_heading_stays_in_body(self):
        tex, warnings = self.convert('::: fontsize=\\small\n## Body heading\n:::')
        self.assertNotIn(r"\setbeamerfont{frametitle}", tex)
        self.assertIn(r"\textbf{Body heading}", tex)
        self.assertEqual(warnings, [])

    def test_quoted_attributes_and_wrapping_widths(self):
        tex, warnings = self.convert('# Table\n::: table fontsize="\\tiny" width=80% widths="20%, 60%, 20%"\n| A | B | C |\n| --- | :---: | ---: |\n| a | b | c |\n:::')
        self.assertIn(r"{0.8\linewidth}", tex)
        for share in ("0.20000000", "0.60000000"):
            self.assertIn(share + r"\mdBeamerTableContentWidth", tex)
        self.assertIn(r"\centering\arraybackslash", tex)
        self.assertIn(r"\raggedleft\arraybackslash", tex)
        self.assertEqual(warnings, [])

    def test_invalid_sizes_and_dimensions_warn_and_fall_back(self):
        for widths in ('20%,20%', '0%,100%', '-10%,110%', 'NaN%,100%', '100%', '40%,30%,30%'):
            with self.subTest(widths=widths):
                tex, warnings = self.convert(f'# T[fontsize=bad]\n::: table fontsize=bad width=200% widths="{widths}"\n| A | B |\n| --- | --- |\n| x | y |\n:::')
                self.assertIn(r"\normalsize", tex)
                self.assertIn(r"{2\linewidth}", tex)
                self.assertIn(r"p{0.50000000\mdBeamerTableContentWidth}", tex)
                self.assertTrue(any("Invalid table column widths" in w for w in warnings))
                self.assertFalse(any("Invalid table width:" in w for w in warnings))
                self.assertEqual(sum("Unsupported fontsize" in w for w in warnings), 2)

    def test_overall_table_width_preserves_tex_lengths(self):
        cases = {
            "120%": r"1.2\linewidth",
            "200%": r"2\linewidth",
            "0%": r"0\linewidth",
            "-20%": r"-0.2\linewidth",
            "12cm": "12cm",
            r"1.2\linewidth": r"1.2\linewidth",
            r"\textwidth": r"\textwidth",
            r"\dimexpr\linewidth + 2cm\relax": r"\dimexpr\linewidth + 2cm\relax",
            "invalid-length": "invalid-length",  # TeX diagnoses invalid lengths.
        }
        for value, expected in cases.items():
            with self.subTest(width=value):
                tex, warnings = self.convert(
                    f'# T\n::: table fontsize=\\tiny width="{value}" widths="20%,20%,60%"\n'
                    '| A | B | C |\n| --- | --- | --- |\n| x | y | z |\n:::')
                self.assertIn(r"\setlength{\mdBeamerTableWidth}{" + expected + "}", tex)
                self.assertIn(r"p{0.60000000\mdBeamerTableContentWidth}", tex)
                self.assertEqual(warnings, [])

    def test_row_and_separator_mismatch_diagnostics(self):
        tex, warnings = self.convert("# T\n| A | B |\n| --- | --- | --- |\n| x |\n| x | y | z |")
        self.assertTrue(any("separator has 3" in w for w in warnings))
        self.assertTrue(any("padding missing" in w for w in warnings))
        self.assertTrue(any("discarding extra" in w for w in warnings))
        self.assertIn(r"\begin{tabular}{ll}", tex)

    def test_malformed_directives_warn_without_losing_content(self):
        tex, warnings = self.convert('# T\n::: table unknown=1 fontsize="unterminated\nText preserved')
        self.assertIn("Text preserved", tex)
        for fragment in ("malformed table attribute", "Malformed table attributes", "Unclosed", "exactly one"):
            self.assertTrue(any(fragment in w for w in warnings), fragment)

    def test_container_directives_inside_code_are_literal(self):
        tex, warnings = self.convert('# T\n::: fontsize=\\tiny\n```\n::: table widths="50%,50%"\n:::\n```\n:::')
        self.assertIn('::: table widths="50%,50%"\n:::', tex)
        self.assertIn(r"\begin{frame}[fragile]", tex)
        self.assertEqual(warnings, [])

    def test_html_comments_are_ignored(self):
        source = '# T\nBefore <!-- inline note --> after\n<!-- full-line note -->\nVisible'
        tex, warnings = self.convert(source)
        self.assertIn('Before  after', tex)
        self.assertIn('Visible', tex)
        self.assertNotIn('inline note', tex)
        self.assertNotIn('full-line note', tex)
        self.assertNotIn('<!--', tex)
        self.assertEqual(warnings, [])

    def test_multiline_html_comments_cannot_change_document_structure(self):
        source = '''# T
<!--
---
# Hidden heading
::: fontsize=\\tiny
[^hidden]: Hidden footnote
-->
Visible'''
        tex, warnings = self.convert(source)
        self.assertEqual(tex.count(r"\begin{frame}"), 1)
        self.assertIn('Visible', tex)
        self.assertNotIn('Hidden heading', tex)
        self.assertNotIn('Hidden footnote', tex)
        self.assertEqual(warnings, [])

    def test_html_comment_syntax_inside_code_is_literal(self):
        source = '# T\n```text\n<!-- keep this -->\n---\n```'
        tex, warnings = self.convert(source)
        self.assertEqual(tex.count(r"\begin{frame}"), 1)
        self.assertIn('<!-- keep this -->\n---', tex)
        self.assertEqual(warnings, [])

    def test_markdown_links_inside_slide_local_references(self):
        source = '''# References
The previous talk was given during O&C Week.[^talk]

[^talk]: [O&C Week](https://indico.cern.ch/event/1554074/)'''
        tex, warnings = self.convert(source)
        self.assertIn(
            r"\footnote{\href{https://indico.cern.ch/event/1554074/}{O\&C Week}}",
            tex,
        )
        self.assertNotIn(r"[O\&C Week](", tex)
        self.assertEqual(warnings, [])

    def test_markdown_links_inside_column_references(self):
        source = '''# References
::: columns
::: column width=100%
Column reference.[^source]
:::
:::

[^source]: [Linked source](https://example.org/source)'''
        tex, warnings = self.convert(source)
        self.assertIn(r"\textsuperscript{a} \href{https://example.org/source}{Linked source}", tex)
        self.assertEqual(warnings, [])

    def test_reference_text_inherits_slide_and_local_font_sizes(self):
        source = r'''# References[fontsize=\small]
Slide-sized reference.[^slide]

::: fontsize=\tiny
Locally sized reference.[^local]
:::

[^slide]: Slide-sized footnote text.
[^local]: Locally sized footnote text.'''
        tex, warnings = self.convert(source)
        self.assertIn(r"\footnotetext{{\small Slide-sized footnote text.}}", tex)
        self.assertIn(r"\footnotetext{{\tiny Locally sized footnote text.}}", tex)
        self.assertEqual(warnings, [])

    def test_reference_definition_can_override_footer_font_size(self):
        source = r'''# References[fontsize=\large]
The referencing text stays large.[^compact]

[^compact][fontsize=\tiny]: The footer text is independently tiny.'''
        tex, warnings = self.convert(source)
        self.assertIn("\\begin{frame}{References}\n\\large", tex)
        self.assertIn(r"\footnotemark{\setbeamerfont{footnote}{size=\tiny}", tex)
        self.assertIn(r"\footnotetext{{\tiny The footer text is independently tiny.}}", tex)
        self.assertIn(r"\setbeamerfont{footnote}{size=\tiny}", tex)
        self.assertIn(r"\setbeamerfont{footnote mark}{size=\tiny}", tex)
        self.assertNotIn("fontsize=", tex)
        self.assertEqual(warnings, [])

    def test_column_reference_text_inherits_slide_font_size(self):
        source = r'''# References[fontsize=\scriptsize]
::: columns
::: column width=100%
Column reference.[^source]
:::
:::

[^source]: Column footnote text.'''
        tex, warnings = self.convert(source)
        self.assertIn(r"{\scriptsize \textsuperscript{a} Column footnote text.}", tex)
        self.assertEqual(warnings, [])

    def test_column_reference_definition_can_override_footer_font_size(self):
        source = r'''# References[fontsize=\large]
::: columns
::: column width=100%
Large column text.[^compact]
:::
:::

[^compact][fontsize="\tiny"]: Independently tiny column footnote.'''
        tex, warnings = self.convert(source)
        self.assertIn(r"{\tiny \textsuperscript{a} Independently tiny column footnote.}", tex)
        self.assertEqual(warnings, [])

    def test_unclosed_html_comment_is_ignored_with_warning(self):
        tex, warnings = self.convert('# T\nVisible\n<!-- hidden through EOF')
        self.assertIn('Visible', tex)
        self.assertNotIn('hidden through EOF', tex)
        self.assertTrue(any('Unclosed HTML comment' in warning for warning in warnings))

    def test_code_fontsize_validation(self):
        tex, warnings = self.convert('# T\n```Python[fontsize=invalid]\nprint(1)\n```')
        self.assertIn(r"basicstyle=\ttfamily\normalsize", tex)
        self.assertTrue(any("Unsupported fontsize" in w for w in warnings))

    def test_compile_and_measure_font_sizes(self):
        fixture = (ROOT / "test" / "syntax_controls.md").read_text()
        tex, warnings = md.md_to_beamer(fixture, theme="Warsaw")
        self.assertEqual(warnings, [])
        expected = {
            "SlideBody": 6, "ListOne": 6, "ListTwo": 6, "ListThree": 6,
            "LocalBody": 10, "LocalList": 10, "RestoredBody": 6,
            "InheritedTable": 6, "ExplicitTable": 9, "AfterTable": 10,
            "BlockTable": 6, "ColumnTable": 6, "ColumnAfter": 10,
            "DefaultBody": 10.95, "DefaultTable": 8,
        }
        # Observe TeX's actual active font, not just commands in generated text.
        for marker in expected:
            tex = tex.replace(marker, r"\typeout{MDB-SIZE-" + marker + r":\csname f@size\endcsname}" + marker)
        # Read font sizes while Beamer actually renders the header template,
        # rather than only checking font commands in the generated source.
        header_samples = {
            "Header level one": ("HeaderOne", 14.4),
            "Header level two": ("HeaderTwo", 12),
            "Header level three": ("HeaderThree", 10.95),
            "Header level four": ("HeaderFour", 10),
            "Header level five": ("HeaderFive", 9),
            "Header level six": ("HeaderSix", 8),
            "Subtitle level two": ("SubtitleTwo", 12),
            "Subtitle level three": ("SubtitleThree", 10.95),
            "Subtitle level four": ("SubtitleFour", 10),
            "Subtitle level five": ("SubtitleFive", 9),
            "Subtitle level six": ("SubtitleSix", 8),
            "Slide subsubtitile": ("Subsubtitle", 10.95),
        }
        for label, (marker, size) in header_samples.items():
            tex = tex.replace(label, r"\typeout{MDB-SIZE-" + marker + r":\csname f@size\endcsname}" + label)
            expected[marker] = size
        engines = [name for name in ("pdflatex", "lualatex") if shutil.which(name)]
        if not engines:
            self.skipTest("No LaTeX engine available")
        for engine in engines:
            with self.subTest(engine=engine), tempfile.TemporaryDirectory(prefix="mdbeamer-syntax-") as directory:
                path = Path(directory)
                # The showcase reuses one repository image. Make the same
                # relative path available in the isolated compilation directory.
                (path / "png").mkdir()
                shutil.copyfile(ROOT / "test" / "png" / "cms-data-model_diagram_01.png",
                                path / "png" / "cms-data-model_diagram_01.png")
                (path / "syntax.tex").write_text(tex)
                result = subprocess.run([engine, "-interaction=nonstopmode", "-halt-on-error", "syntax.tex"],
                                        cwd=path, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout[-6000:])
                log = (path / "syntax.log").read_text(errors="replace")
                # Oversized-table slides deliberately exercise overflow. A
                # blanket prohibition on overfull boxes would reject that syntax.
                sizes = dict(re.findall(r"MDB-SIZE-(\w+):([\d.]+)", log))
                for marker, size in expected.items():
                    self.assertIn(marker, sizes)
                    self.assertAlmostEqual(float(sizes[marker]), size, places=2, msg=f"{engine}: {marker}")
                self.assertGreater((path / "syntax.pdf").stat().st_size, 0)
                if shutil.which("pdftotext"):
                    extracted = subprocess.run(["pdftotext", "syntax.pdf", "-"], cwd=path,
                                               capture_output=True, text=True, check=True).stdout
                    self.assertEqual(extracted.count('\f'), 50)
                    self.assertIn("Title-only frame", extracted)


if __name__ == "__main__":
    unittest.main()

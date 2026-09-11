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
    def convert(self, source):
        return md.md_to_beamer(source)

    def test_slide_title_attributes_and_title_only_frames(self):
        tex, warnings = self.convert("# Opening\n---\n# Later[fontsize=\\tiny]\n---\nBefore\n\n# Content[fontsize=\\small]\nBody")
        self.assertEqual(tex.count(r"\titlepage"), 1)
        self.assertIn("\\begin{frame}{Later}\n\\tiny", tex)
        self.assertIn("\\begin{frame}{Content}\n\\small", tex)
        self.assertNotIn("fontsize=", tex)
        self.assertEqual(warnings, [])

    def test_natural_table_alignment_and_paragraph_boundary(self):
        tex, warnings = self.convert("# Table\nText\n| A | B | C |\n| :--- | :---: | ---: |\n| a | b | c |")
        self.assertIn(r"\begin{tabular}{lcr}", tex)
        self.assertEqual(warnings, [])

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
                    self.assertEqual(extracted.count('\f'), 49)
                    self.assertIn("Title-only frame", extracted)


if __name__ == "__main__":
    unittest.main()

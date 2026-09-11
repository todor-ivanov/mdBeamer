# ⚠️ AI-Assisted Content Notice

Parts of the code, documentation, and generated reports contained in this
repository include **AI-assisted or AI-altered content**.

Some sections were produced with the help of **OpenAI ChatGPT (GPT-5 series)**
during the development of the WMCore → DIRAC interoperability prototype.

All AI-generated or AI-assisted material included in this repository has been
**reviewed and curated by a human maintainer** before inclusion.

The purpose of using AI assistance in this repository is to accelerate
prototyping and documentation while maintaining full human oversight of
technical correctness and architectural decisions.

If you encounter inconsistencies or potential issues in AI-assisted sections,
please open an issue in the repository.



# mdBeamer

A simple script to allow quick translation from Markdown to Beamer and creating
a heavily customized presentations using a specific template.

See [Syntax reference](README_SYNTAX.md) for supported Markdown syntax,
Beamer-specific extensions, examples, and current limitations.

## Usage:

```
usage: mdBeamer.py [-h] -o OUTPUT [--warnings WARNINGS] [--theme THEME]
                   [--colortheme COLORTHEME] [--fonttheme FONTTHEME]
                   [--innertheme INNERTHEME] [--outertheme OUTERTHEME]
                   [--text-margin-left LENGTH] [--text-margin-right LENGTH]
                   [--list-indent LENGTH] [--list-indent-1 LENGTH]
                   [--list-indent-2 LENGTH] [--list-indent-3 LENGTH]
                   [--list-label-sep LENGTH] [--list-item-sep LENGTH]
                   [--list-top-sep LENGTH] [--list-parse-sep LENGTH]
                   input_md

positional arguments:
  input_md

options:
  -h, --help            show this help message and exit
  -o, --output OUTPUT
  --warnings WARNINGS
  --theme THEME
  --colortheme COLORTHEME
  --fonttheme FONTTHEME
  --innertheme INNERTHEME
  --outertheme OUTERTHEME
  --text-margin-left LENGTH
                        left frame text margin (default: 5mm)
  --text-margin-right LENGTH
                        right frame text margin (default: 5mm)
  --list-indent LENGTH  indentation for every list level
  --list-indent-1 LENGTH
                        first-level list indentation (default: 1.5em)
  --list-indent-2 LENGTH
                        second-level list indentation (default: 1.25em)
  --list-indent-3 LENGTH
                        third-level list indentation (default: 1.1em)
  --list-label-sep LENGTH
                        space between a list marker and its text (default: 0.35em)
  --list-item-sep LENGTH
                        vertical space between list items (default: 0.15em)
  --list-top-sep LENGTH
                        vertical space above and below a list (default: 0.2em)
  --list-parse-sep LENGTH
                        vertical space between paragraphs in an item (default: 0pt)
```

## Example:

```
./mdBeamer.sh test/DBS_future_dev_notes.md --theme Warsaw
```

# preview

A simple script to implement a continuous live preview of an mdBeamer translated
file. The refresh is triggered on any change of the original Markdown file(*.md).

```
usage ./preview.sh [-h] [--<mdBeamer options>] input_md

positional arguments:
  input_md

options:
    It supports any option valid for the mdBeamer.py script
```

## Example:

```
./preview.sh test/DBS_future_dev_notes.md --theme Warsaw
```

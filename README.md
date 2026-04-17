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

## Usage:

```
usage: mdBeamer.py [-h] -o OUTPUT [--warnings WARNINGS] [--theme THEME] [--colortheme COLORTHEME] [--fonttheme FONTTHEME] [--innertheme INNERTHEME] [--outertheme OUTERTHEME]
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
```

## Example:

```
./mdBeamer.sh test/DBS_future_dev_notes.md --theme Warsaw
```

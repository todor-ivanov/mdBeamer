#!/usr/bin/env bash

set -u

SRC_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
CURR_DIR=$(realpath -- "$(pwd)")
mdTranslator="${SRC_DIR}/mdBeamer.py"

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
    python3 "$mdTranslator" -h
    exit
fi

if (( $# == 0 )); then
    echo "Usage: $0 <file.md> [mdBeamer options...]" >&2
    exit 2
fi

source_arg=$1
shift
translator_args=("$@")

if [[ ! -f $source_arg ]]; then
    echo "Error: Markdown source does not exist: $source_arg" >&2
    exit 2
fi

source_file=$(realpath -- "$source_arg")
inDir=$(dirname -- "$source_file")
inFile=$(basename -- "$source_file")

if [[ $inFile != *.md ]]; then
    echo "Error: Expected a Markdown file ending in .md: $source_file" >&2
    exit 2
fi

outDir=$inDir/output/
mkdir -p $outDir
texFile="${outDir}/${inFile%.md}.tex"
outFile="${outDir}/${inFile%.md}.pdf"

export TEXINPUTS=":${CURR_DIR}:${CURR_DIR}/tex//:${CURR_DIR}/fig//:${CURR_DIR}/utils/general//:${CURR_DIR}/output//:${inDir}//:${inDir}/fig//:${inDir}/png//:${inDir}/tex//"
export BSTINPUTS=$TEXINPUTS
export BIBINPUTS=$TEXINPUTS
export TEXPSHEADERS=$TEXINPUTS

build() {
    echo "Markdown changed; translating and building ${outFile}"

    if ! python3 "$mdTranslator" "$source_file" -o "$texFile" "${translator_args[@]}"; then
        echo "Markdown translation failed; waiting for another change." >&2
        return 1
    fi

    if ! latexmk -lualatex -interaction=nonstopmode -outdir="$outDir" "$texFile"; then
        echo "PDF build failed; waiting for another change." >&2
        return 1
    fi
}

file_hash() {
    sha256sum -- "$source_file" 2>/dev/null | awk '{print $1}'
}

echo "Watching only: $source_file"

last_hash=$(file_hash)
if [[ -z $last_hash ]]; then
    echo "Error: Cannot read Markdown source: $source_file" >&2
    exit 1
fi

if build; then
    atril "$outFile" >/dev/null 2>&1 &
fi

while true; do
    sleep 0.5
    current_hash=$(file_hash)

    # Editors may briefly remove a file while replacing it atomically.
    [[ -z $current_hash ]] && continue

    if [[ $current_hash != "$last_hash" ]]; then
        last_hash=$current_hash
        build || true
    fi
done

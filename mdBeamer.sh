#!/bin/bash

SRC=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SRC=$( realpath $SRC )

mdTranslator=${SRC}/mdBeamer.py
texCompiler='xelatex'
# texCompiler='pdflatex'

[[ $1 == "-h" ]] && python3 $mdTranslator -h && exit

inFile=$1
shift
inDir=$(realpath $(dirname $inFile))
outDir=$inDir
tmpDir=$inDir/tmp
mkdir -p $tmpDir

echo tmpDir: $tmpDir
echo inDir: $inDir

outFile=$inDir/${inFile%.md}.pdf
texFile=$outDir/${inFile%.md}.tex

python3 $mdTranslator  $inFile -o $texFile $* && $texCompiler --output-directlry=$outDir $texFile  && atril $outFile

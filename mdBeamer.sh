#!/bin/bash

SRC_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SRC_DIR=$( realpath $SRC_DIR )

CURR_DIR=$(realpath `pwd`)

mdTranslator=${SRC_DIR}/mdBeamer.py
# texCompiler='xelatex'
texCompiler='lualatex'
# texCompiler='pdflatex'

[[ $1 == "-h" ]] && python3 $mdTranslator -h && exit

inFile=$1
shift
inDir=$(realpath $(dirname $inFile))
inFile=$(basename $inFile)
outDir=$inDir
tmpDir=$outDir/tmp
mkdir -p $tmpDir

echo tmpDir: $tmpDir
echo inDir: $inDir
echo outDir: $outDir

outFile=$outDir/${inFile%.md}.pdf
texFile=$outDir/${inFile%.md}.tex


export TEXINPUTS=:${CURR_DIR}:${CURR_DIR}/tex//:${CURR_DIR}/fig//:${CURR_DIR}/fig//:${CURR_DIR}/utils/general//:${CURR_DIR}/output//:$inDir//:$inDir/fig//:$inDir/png//:$inDir/tex//
export BSTINPUTS=${TEXINPUTS}
export BIBINPUTS=${TEXINPUTS}
export TEXPSHEADERS=${TEXINPUTS}


# Clean all temporary files from previous runs (modulo the .tex && .pdf files -  those will be overwritten)
inFileBase=${inFile%.*}
rm  $outDir/$inFileBase.{aux,log,nav,out,snm,toc,vrb}

python3 $mdTranslator  $inDir/$inFile -o $texFile $* && $texCompiler --output-directory=$outDir $texFile  && atril $outFile

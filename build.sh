#!/bin/bash -e
SPHINXBUILD="python3 -m sphinx"

$SPHINXBUILD -b singlehtml . build/singlehtml
$SPHINXBUILD -b latex . build/pdf

pushd build/pdf
pdflatex parslguts.tex
makeindex parslguts
pdflatex parslguts.tex
pdflatex parslguts.tex
popd


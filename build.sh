#!/bin/bash -e
SPHINXBUILD="python3 -m sphinx"

$SPHINXBUILD -b html . build/html
$SPHINXBUILD -b singlehtml . build/singlehtml
$SPHINXBUILD -b latex . build/pdf

pushd build/pdf
pdflatex parslguts.tex
makeindex -s python.ist parslguts
pdflatex parslguts.tex
pdflatex parslguts.tex
popd


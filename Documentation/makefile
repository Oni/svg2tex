all: svg2tex_doc.pdf

svg2tex_doc.pdf: svg2tex_doc.tex
	pdflatex svg2tex_doc
	pdflatex svg2tex_doc
	evince svg2tex_doc.pdf
clean:
	rm -rf *.aux *.toc *.log *.out

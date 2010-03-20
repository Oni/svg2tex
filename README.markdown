# Svg2tex

Svg2tex is a python script that extracts all text from a *.svg file to a LaTeX picture environment. This way the picture's text is processed directly by LaTeX and can be included into the document.

Download it now: [tar](http://github.com/Oni/svg2tex/tarball/master) or [zip](http://github.com/Oni/svg2tex/zipball/master) file.

## Usage

Svg2tex can be used as an inkscape extension or as a standalone script. The final result is the same.

### Inkscape extension

Installing svg2tex is very easy. Under Linux you only need to copy `svg2tex.py` and `output.inx` under `/home/<your username>/.inkscape/extensions`. Under Windows just copy the same files under `C:\<inkscape installation directory>\share\extensions\ `. At this point it's necessary to restart inkscape. Under the save menu there should be a new option: `LaTeX (text only) picture environment (*.tex)`.

### Command-line

Svg2tex can also be called from command-line. Here it is the syntax:


    python svg2tex.py <options> <svg-input-file> <tex-output-file>

The `<tex-output-file>` is optional and, if it's not given, the LaTeX output is printed in standard output. The `<options>` can be any of the following:

  * `-i <filename>` (or `--include <filename>`) - set the background image of the picture environment to `<filename>`,
  * `-t <filename>` (or `--textless <filename>`) - make a copy of the original *.svg file without text and save it as `<filename>`.

Even from command-line, svg2tex can be paired with inkscape. The next simple shell script, for example, converts all \*.svg files in the directory into ready-to-use LaTeX + \*.pdf pictures:

    #!/bin/sh

    for file in *.svg
    do
      echo "Processing ${file}..."
      fn=${file%.svg}
      python svg2tex.py -i "${fn}" -t "${fn}.tl.svg" "${file}" "${fn}.tex"
      inkscape --export-pdf="${fn}.pdf" "${fn}.tl.svg"

      rm "${fn}.tl.svg"
    done

## More info

The [documentation file](http://github.com/downloads/Oni/svg2tex/svg2tex_doc.pdf) also has a step-by-step example on how to use svg2tex with inkscape.

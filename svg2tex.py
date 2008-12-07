#!/usr/bin/env python
# -*- coding: latin-1 -*-

"""
Svg2tex, a python script that exports text from *.svg files to LaTeX picture environment
Copyright (C) 2008 Lorenzo Tozzi

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

# Part 1: Extract data from SVG
#####################################

import math, re

from copy import deepcopy

try: # maybe lxml is not installed
  from lxml import etree
except:
  sys.stderr.write("The lxml wrapper missing: download it from <http://cheeseshop.python.org/pypi/lxml/> or use your package manager typing: sudo apt-get install python-lxml")
  sys.exit(2)

"""
Extracts all text from a SVG document and exports it to a LaTeX picture
environment
"""

def ProcessSvg(svg_tree, background):
  """
  Translate SVG text into LaTeX picture environment
  """

  raw_text = [] # this will be populated with the text to be exported
                # it's a list of dictionaries:
                # {"text":<text>           the actual text
                #  "x":<x coordinate>
                #  "y":<y coordinate>      those coordinates takes into
                #                          account all transformations
                #  "rotation":<rotation>
                #  "anchor":<text anchor>} it defines if the text begins,
                #                          ends or is centered in x, y

  # maybe there are some <use> tags that links other elements in the document
  # so we have to traverse the document and hard copy those referenced
  # elements under the respective <use> tags
  for child in svg_tree.iterdescendants():
    if child.tag == "{http://www.w3.org/2000/svg}use":
      href = child.get("{http://www.w3.org/1999/xlink}href")
      if href and href.strip():
        # href has a "#" char at the beginning, the real "id"
        # we are looking for is href[1:]
        href = href[1:]
        # maybe the SVG file is corrupted and the referenced element
        # doesn't exist so we need a check
        linked_tree = svg_tree.xpath("//*[@id='%s']" % href) # find the referenced tree using its id
        if linked_tree:
          child.append(deepcopy(linked_tree[0]))
        else:
          sys.stderr.write("Warning: corrupted SVG file. Referenced element with id = %s doesn't exist\n" % href)

  # now we are ready to extract text from the SVG
  # all text is now located in <text> and <tspan> tags
  for child in svg_tree.iterdescendants():
    if child.tag in ("{http://www.w3.org/2000/svg}text", "{http://www.w3.org/2000/svg}tspan") and child.text and child.text.strip():
      raw_text.append(ExtractText(child))

  return FormatLatexPicture(svg_tree, raw_text, background)

def ExtractText(node):
  """
  We have just found some text, we have to return a dictionary
  that will be appended to raw_text with its coordinates
  """

  this_text = {"text":"", "x":0, "y":0, "rotation":0, "anchor":""} # prepare the dictionary that
                                                                   # will be returned
  this_text["text"] = node.text
  this_text["anchor"] = GetAnchor(node)  # get text anchor point
  this_text.update(GetCoordinates(node)) # those are the initial coordinates

  transform_stack = [] # all transformations will be queued here

  for child in AncestorsList(node): # climb the ancestors tree (including node)
    transform = child.get("transform")
    if transform and transform.strip():
      transform_stack[:0] = MakeMatrix(transform) # and add the new transformation(s) at the BEGINNING of the stack

  # transform_stack is now complete: finally we transform the coordinates
  if transform_stack:
    transform_matrix = ProcessStack(transform_stack) # make transform_stack a single matrix (combine all transformations)
    direction = {"x":this_text["x"]+100, "y":this_text["y"]} # this vector is used to compute text rotation
                                                             # (direction - this_text) is an horizontal vector
    this_text.update(ApplyTransform(this_text, transform_matrix)) # apply transformations
    direction.update(ApplyTransform(direction, transform_matrix))

    if (direction["x"] - this_text["x"]) == 0:
      rotation = 90 # vertical text has rotation = 90
    else:
      rotation = (direction["y"] - this_text["y"]) / (direction["x"] - this_text["x"])
      rotation = math.degrees(math.atan(rotation))

    this_text["rotation"] = rotation

  return this_text

def MakeMatrix(transformation):
  """
  Translate the transform attribute into a list of matrices and return them
  """

  # make "transformation" a list of transformations
  regex = re.compile ("\s*([a-z]+\s*\(\s*[0-9\s,\.-]+\s*\))\s*", re.IGNORECASE)
  # this matches some text, then a "(", then some numbers with ",", "." and "-" and finally ")"
  # whitespaces can be everywhere
  transformation_list = regex.split(transformation) # now we split where regex is found
  # transformation_list is a list like:
  # [<text that didn't match>, <text that matched re inside "(" and ")">, <text that didn't match>, etc.]
  # what didn't match should be empty strings or something with invalid syntax.
  # Either way, we get rid of them
  if transformation_list:
    for i in range(len(transformation_list)/2+1):
      del transformation_list[i] # this will delete all odd indexed values

  # for further information on how SVG handles transformations, here it is the official
  # reference: http://www.w3.org/TR/SVG/coords.html#TransformAttribute

  matrix_list = []
  for i in range(len(transformation_list)): # what kind of transformation is it?
                                            # we are testing against all of them
    # first we look for a "translate"
    regex = re.compile ("\s*translate\s*\(\s*(-?[0-9]+\.?[0-9]*)\s*(,\s*(-?[0-9]+\.?[0-9]*))?\s*\)\s*", re.IGNORECASE)
    # this matches "translate" then "(", then a number with or without a "-" or a ".", then (optionally) a ","
    # and another number. Then a closing ")"
    m = regex.match(transformation_list[i])
    if m:
      t_x = float(m.group(1))
      if m.group(2): # the second argument is optional
        t_y = float(m.group(3))
      else:
        t_y = 0 # default t_y value
      matrix_list.append([[1,0,t_x], [0,1,t_y], [0,0,1]])

    # then we look for a "scale"
    regex = re.compile ("\s*scale\s*\(\s*(-?[0-9]+\.?[0-9]*)\s*(,\s*(-?[0-9]+\.?[0-9]*))?\s*\)\s*", re.IGNORECASE)
    m = regex.match(transformation_list[i])
    if m:
      s_x = float(m.group(1))
      if m.group(2): # again, the second argument is optional
        s_y = float(m.group(3))
      else:
        s_y = s_x # but this time the default s_y value is like s_x
      matrix_list.append([[s_x,0,0], [0,s_y,0], [0,0,1]])

    # then we look for a "rotate"
    regex = re.compile ("\s*rotate\s*\(\s*(-?[0-9]+\.?[0-9]*)\s*(,\s*(-?[0-9])+\.?[0-9]*\s*,\s*(-?[0-9]+\.?[0-9]*))?\s*\)\s*", re.IGNORECASE)
    m = regex.match(transformation_list[i])
    if m:
      rot = float(m.group(1))
      rot = math.radians(rot)
      cos_r = math.cos(rot)
      sin_r = math.sin(rot)
      if m.group(2): # optional argument
        c_x = float(m.group(3))
        c_y = float(m.group(4))
      else:
        c_x = 0
        c_y = 0
      matrix_list.append([[1,0,c_x], [0,1,c_y], [0,0,1]])              # go to c_x, c_y
      matrix_list.append([[cos_r,-sin_r,0], [sin_r,cos_r,0], [0,0,1]]) # rotate
      matrix_list.append([[1,0,-c_x], [0,1,-c_y], [0,0,1]])            # go back where you were

    #then we look for a "skewX"
    regex = re.compile ("\s*skewX\s*\(\s*(-?[0-9]+\.?[0-9]*)\s*\)\s*", re.IGNORECASE)
    m = regex.match(transformation_list[i])
    if m:
      skw_x = float(m.group(1))
      tan_skw_x = math.tan(radians(skw_x))
      matrix_list.append([[1,tan_skw_x,0], [0,1,0], [0,0,1]])

    # then we look for a "skewY"
    regex = re.compile ("\s*skewY\s*\(\s*(-?[0-9]+\.?[0-9]*)\s*\)\s*", re.IGNORECASE)
    m = regex.match(transformation_list[i])
    if m:
      skw_y = float(m.group(1))
      tan_skw_y = math.tan(radians(skw_y))
      matrix_list.append([[1,0,0], [tan_skw_y,1,0], [0,0,1]])
    # text will never be skewed in LaTeX

    # and if we are lucky we have directly a matrix
    regex = re.compile ("\s*matrix\s*\(\s*(-?[0-9]+\.?[0-9]*)\s*,\s*(-?[0-9]+\.?[0-9]*)\s*,\s*(-?[0-9]+\.?[0-9]*)\s*,\s*(-?[0-9]+\.?[0-9]*)\s*,\s*(-?[0-9]+\.?[0-9]*)\s*,\s*(-?[0-9]+\.?[0-9]*)\s*\)\s*", re.IGNORECASE)
    m = regex.match(transformation_list[i])
    if m:
      a = float(m.group(1))
      b = float(m.group(2))
      c = float(m.group(3))
      d = float(m.group(4))
      e = float(m.group(5))
      f = float(m.group(6))
      matrix_list.append([[a,c,e], [b,d,f], [0,0,1]])

  return matrix_list

def ProcessStack(transform_stack):
  """
  Combine all transformations (matrix multiplication, nothing more)
  """

  if transform_stack:
    while len(transform_stack) > 1: # get the last two transformations and combine them
                                    # until we have only one
      matrix = [[0,0,0], [0,0,0], [0,0,0]]
      matrix_a = transform_stack[-2]
      matrix_b = transform_stack[-1]
      for i in range(3):
        for j in range(3):
          sum_var = 0
          for r in range(3):
            sum_var += matrix_a[i][r] * matrix_b[r][j] # do the math
            matrix[i][j] = sum_var
      del transform_stack[-2:]       # ok, we are done with those two
      transform_stack.append(matrix) # substitute them with the resulting matrix
  return transform_stack[0]

def GetCoordinates(node):
  """
  Find x and y coordinates of the text
  """

  coordinates = {"x":0, "y":0}

  for child in AncestorsList(node):
    if child.tag != "{http://www.w3.org/2000/svg}text" and child.tag != "{http://www.w3.org/2000/svg}tspan":
      return coordinates # whoops we are outside text tags: return
    x = child.get("x")
    if x and x.strip():
      coordinates["x"] = float(x)
    y = child.get("y")
    if y and y.strip():
      coordinates["y"] = float(y)

  return coordinates

def ApplyTransform(vector, matrix):
  """
  Transform a vector given a matrix
  """

  transformed_vector = {"x":0, "y":0}
  # simple geometry in action
  transformed_vector["x"] = vector["x"] * matrix[0][0] + vector["y"] * matrix[0][1] + matrix[0][2]
  transformed_vector["y"] = vector["x"] * matrix[1][0] + vector["y"] * matrix[1][1] + matrix[1][2]

  return transformed_vector

def GetAnchor(node):
  """
  Translate the style attribute and get the anchor point
  """

  alignment = ""

  for child in AncestorsList(node):
    alignment_attribute = child.get("style")

    if alignment_attribute and alignment_attribute.strip():
      regex = re.compile("\s*;?\s*text-align\s*:\s*([a-z]*)", re.IGNORECASE) # first we look for "text-align:"
      m = regex.search(alignment_attribute)
      if m:
        alignment_attribute = m.group(1)
      else:
        regex = re.compile("\s*;?\s*text-anchor\s*:\s*([a-z]*)", re.IGNORECASE) # then (if nothing was found)
        m = regex.search(alignment_attribute)                                   # we look for "text-anchor:"
        if m:
          alignment_attribute = m.group(1)

      if alignment_attribute in ("center", "middle"):
        alignment = "bc" # TTTT.TTTT  text is centered at x, y coordinates
      if alignment_attribute == "end":
        alignment = "br" # TTTTTTTT.  text is on the left of x, y coordinates
      if alignment_attribute == "start":
        alignment = "bl" # .TTTTTTTT  text is on the right of x, y coordinates

      if alignment:      # if we have found a valid alignment
        return alignment # return it, otherwise keep looping among ancestors

  alignment = "bl" # default value

  return alignment

def FormatLatexPicture(svg_tree, raw_text, background):
  """
  Generate the LaTeX picture environment with -optionally- a background image
  """

  conversion_constant = 1./3.543307 # px (user units) to mm. Reference on units: http://www.w3.org/TR/SVG/coords.html#Units

  picture_environment = "\setlength{\unitlength}{%smm}\n" % conversion_constant

  svg_height = float(svg_tree.get("height"))
  svg_width = float(svg_tree.get("width"))

  picture_environment += "\\begin{picture}(%s, %s)(0, %s)\n" % (svg_width, svg_height, -svg_height)

  if background and background.strip(): # first, draw the background so the text will be over it
    picture_environment += "  \put(0,%s){\includegraphics[height=%smm, width=%smm]{%s}}\n" % (-svg_height, svg_height * conversion_constant, svg_width * conversion_constant, background)

  for text in raw_text: # turnbox is taken from the "rotating" LaTeX package
    text["text"] = "\makebox(0,0)[%s]{%s}" % (text["anchor"], text["text"])
    if text["rotation"] != 0:
      text["text"] = "\\turnbox{%s}{%s}" % (-text["rotation"], text["text"])
    picture_environment += "  \put(%s,%s){%s}\n" % (text["x"], -text["y"], text["text"])

  picture_environment += "\end{picture}"

  return picture_environment

def AncestorsList(node):
  """
  lxml's node.iterancestors() doesn't include node itself, but only the ancestors. This function
  returns node's ancestors and node itself
  """

  ancestors_tree = [node]

  for child in node.iterancestors():
    ancestors_tree.append(child)

  return ancestors_tree

# Part 2: Delete text from svg
#####################################

def DeleteSvgText(svg_tree):
  """
  Delete all text and tspan tags from the SVG and return it as a string
  """

  for child in svg_tree.iterdescendants():
    if child.tag in ("{http://www.w3.org/2000/svg}text", "{http://www.w3.org/2000/svg}tspan"):
      child.text = ""

  return etree.tostring(svg_tree)

# Part 3: Command line processing
#####################################

import sys, os, getopt

def Usage():
  """
  Explains how to use this script
  """

  sys.stdout.write("Usage:\n")
  sys.stdout.write("Type 'python svg2tex.py <options> <svg-input-file> <tex-output-file>'\n")
  sys.stdout.write("If <tex-output-file> is not given, output is written on stdout.'\n")
  sys.stdout.write("Options:\n")
  sys.stdout.write("-i --include <filename>\t\tinclude <filename> as the LaTeX picture\n")
  sys.stdout.write("\t\t\t\tenvironment background\n")
  sys.stdout.write("-t --textless <filename>\tmake a copy of the original SVG file\n")
  sys.stdout.write("\t\t\t\twithout text and save it as <filename>\n")
  sys.stdout.write("Required packages for the LaTeX document:\n")
  sys.stdout.write("  includegraphics\n")
  sys.stdout.write("  rotating\n")

  sys.exit(2)

include_background = None
svg_output_filename = None
svg_input_filename = None
tex_filename = None
write_on_stdout = False

if __name__ == "__main__":
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hi:t:", ["help", "include=", "textless="])
  except getopt.GetoptError:
    Usage() # this happens if user gives wrong options
  for opt, arg in opts:
    if opt in ("-h", "--help"):
      Usage()
    elif opt in ("-i", "--include"):
      include_background = arg
    elif opt in ("-t", "--textless"):
      svg_output_filename = arg

  try: # maybe args[0] (<svg-input-file>) is missing...
    svg_input_filename = args[0]
  except:
    Usage()

  try: # maybe args[1] (<tex-output-file>) is missing...
    tex_filename = args[1]
  except:
    write_on_stdout = True

  if not os.path.isfile(svg_input_filename):
    sys.stderr.write("Error: %s not found\n" % svg_input_filename)
    sys.exit(2)

  f = open(svg_input_filename, "r") # open the SVG file
  svg_file = f.read()
  f.close()

  try:
    svg_tree = etree.fromstring(svg_file) # make an etree object out of it
  except:
    sys.stderr.write("Error: %s is not a valid SVG file\n" % svg_input_filename)
    sys.exit(2)

  latex_picture = ProcessSvg(svg_tree, include_background) # process it

  if not write_on_stdout:
    f = open(tex_filename, "w") # and save the result
    f.writelines(latex_picture)
    f.close()
  else:
    sys.stdout.write(latex_picture)

  if svg_output_filename: # if a textless file is requested
    textless_svg = DeleteSvgText(svg_tree) # process the original SVG
    f = open(svg_output_filename, "w")
    f.writelines(textless_svg) # and write the result
    f.close()

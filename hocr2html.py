#!/usr/bin/python

import sys
from pyhtml import parse
from pyhtml import html
from pyhtml import css

def hocr2html(syntax, parent = None, left = None):
	if isinstance(syntax, html.Tag):
		if 'class' in syntax.attrs:
			if syntax.attrs['class'][0:3] == 'ocr':
				style = css.Style()

				attrs = syntax.attrs['title'].split(';')
				for attr in attrs:
					elems = attr.strip().split(' ')
					if elems[0] == 'x_wconf':
						wconf = float(int(elems[1]))/100.0
						#style.set("background-color", css.Rgb(1.0-wconf, wconf, 0.0))
					elif elems[0] == 'bbox':
						startx = 0
						starty = 0
						width = None
						height = None
						if parent and 'title' in parent.attrs:
							parent_attrs = parent.attrs['title'].split(';')
							for parent_attr in parent_attrs:
								parent_elems = parent_attr.strip().split(' ')
								if parent_elems[0] == 'bbox':
									startx = int(parent_elems[1])
									starty = int(parent_elems[2])
									width = int(parent_elems[3]) - int(parent_elems[1])
									height = int(parent_elems[4]) - int(parent_elems[2])

						width = int(elems[3]) - int(elems[1])
						height = int(elems[4]) - int(elems[2])
						startx = int(elems[1]) - startx
						starty = int(elems[2]) - starty

						style.set("position", "absolute")
						style.set("left", str(startx)+"px")
						style.set("top", str(starty)+"px")
						style.set("width", str(width)+"px")
						style.set("height", str(height)+"px")
				
				syntax.attrs['style'] = style
							
			
		for i,elem in enumerate(syntax.content):
			syntax.content[i] = hocr2html(elem, syntax, syntax.content[i-1] if i > 0 else left)

		#if 'class' in syntax.attrs and syntax.attrs['class'] == 'ocrx_word' and len(syntax.content) == 1:
		#	return syntax.content[0]
		#else:
		return syntax
	else:
		return syntax



parser = parse.Parser()
          
with open(sys.argv[1], 'r') as fptr:
	parser.feed(fptr.read())

print hocr2html(parser.syntax).content[0]

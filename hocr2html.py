#!/usr/bin/python3

import sys
from lxml import etree
from pyhtml import parse
from pyhtml import html
from pyhtml import css

def parse_ocr_attrs(syntax, parent=None, left=None):
	syntax.ocr = dict()
	if 'class' in syntax.attrs and syntax.attrs['class'][0:3] == 'ocr' and 'title' in syntax.attrs:
		attrs = syntax.attrs['title'].split(';')
		for attr in attrs:
			elems = attr.strip().split(' ')
			if elems:
				if elems[0] == 'bbox':
					syntax.ocr['bbox'] = [int(e) for e in elems[1:]]
				else:
					syntax.ocr[elems[0]] = elems[1:]
		del syntax.attrs['title']
	return syntax

def fix_contractions(syntax, parent=None, left=None):
	if 'class' in syntax.attrs and syntax.attrs['class'] == 'ocrx_word' and len(syntax.content) > 1:
		if syntax.content[1][0] in ['s', 't']:
			syntax.content[0] += '\'' + syntax.content[1]
			del syntax.content[1]
	return syntax

def set_position(syntax, parent=None, left=None):
	if 'bbox' in syntax.ocr:
		if 'style' not in syntax.attrs:
			syntax.attrs['style'] = css.Style()
		width = syntax.ocr['bbox'][2] - syntax.ocr['bbox'][0]
		height = syntax.ocr['bbox'][3] - syntax.ocr['bbox'][1]
		if parent and 'bbox' in parent.ocr:
			pwidth = parent.ocr['bbox'][2] - parent.ocr['bbox'][0]
			pheight = parent.ocr['bbox'][3] - parent.ocr['bbox'][1]
			offx = syntax.ocr['bbox'][0] - parent.ocr['bbox'][0]
			offy = syntax.ocr['bbox'][1] - parent.ocr['bbox'][1]
			syntax.attrs['style'].set("left", str(100*offx/pwidth)+"%")
			syntax.attrs['style'].set("top", str(100*offy/pheight)+"%")
			syntax.attrs['style'].set("width", str(width)+"px")
			syntax.attrs['style'].set("height", str(height)+"px")
		else:
			offx = syntax.ocr['bbox'][0]
			offy = syntax.ocr['bbox'][1]
			syntax.attrs['style'].set("left", str(offx) + "px")
			syntax.attrs['style'].set("top", str(offy)+"px")
			syntax.attrs['style'].set("width", str(width) + "px")
			syntax.attrs['style'].set("height", str(height) + "px")
	return syntax

def align_lines(syntax, parent=None, left=None):
	if 'bbox' in syntax.ocr:
		if 'class' in syntax.attrs and syntax.attrs['class'] == 'ocr_par':
			height = syntax.ocr['bbox'][3] - syntax.ocr['bbox'][1]
			line_height = 0
			for line in syntax.content:
				if isinstance(line, html.Tag) and 'class' in line.attrs and line.attrs['class'] == 'ocr_line' and 'bbox' in line.ocr:
					line_height = max(line_height, line.ocr['bbox'][3] - line.ocr['bbox'][1])
	
			if line_height == 0:
				line_height = height

			num_lines = int(round(float(height)/float(line_height)))
			line_height = height/num_lines
			#if 'style' not in syntax.attrs:
			#	syntax.attrs['style'] = css.Style()
			#syntax.attrs['style'].set("font-size", str(line_height) + "px")

			center = False
			for i,line in enumerate(syntax.content):
				if isinstance(line, html.Tag) and 'class' in line.attrs and line.attrs['class'] == 'ocr_line' and 'bbox' in line.ocr:
					loff = abs(line.ocr['bbox'][0] - syntax.ocr['bbox'][0])
					roff = abs(line.ocr['bbox'][2] - syntax.ocr['bbox'][2])
					if min(loff, roff) > 2 and abs(loff-roff) < 5:
						center = True

					idx = int(round(float(i*num_lines)/float(len(syntax.content))))
					#line.ocr['bbox'][0] = syntax.ocr['bbox'][0]
					#line.ocr['bbox'][2] = syntax.ocr['bbox'][2]
					line.ocr['bbox'][1] = idx*line_height + syntax.ocr['bbox'][1]
					line.ocr['bbox'][3] = (idx+1)*line_height + syntax.ocr['bbox'][1]
			#if center:
			#	syntax.attrs['style'].set("text-align", "center")

	return syntax

def align_words(syntax, parent=None, left=None):
	if 'bbox' in syntax.ocr:
		if 'class' in syntax.attrs and syntax.attrs['class'] == 'ocr_line':
			width = syntax.ocr['bbox'][2] - syntax.ocr['bbox'][0]
			for i,word in enumerate(syntax.content):
				if isinstance(word, html.Tag) and 'class' in word.attrs and word.attrs['class'] == 'ocrx_word' and 'bbox' in word.ocr:
					word.ocr['bbox'][1] = syntax.ocr['bbox'][1]
					word.ocr['bbox'][3] = syntax.ocr['bbox'][3]
	return syntax

def trim_empty(syntax, parent=None, left=None):
	if 'class' in syntax.attrs and syntax.attrs['class'] in ['ocr_line', 'ocr_par', 'ocr_carea']:
		for i,elem in reversed(list(enumerate(syntax.content))):
			if isinstance(elem, html.Tag) and not elem.content:
				del syntax.content[i]
	
	if 'class' in syntax.attrs and syntax.attrs['class'] in ['ocr_carea']:
		if not syntax.content:
			if 'style' not in syntax.attrs:
				syntax.attrs['style'] = css.Style()
			syntax.attrs['style'].set("background-color", "#000000")

	return syntax

def consolidate_lines(syntax, parent=None, left=None):
	if 'class' in syntax.attrs and syntax.attrs['class'] == 'ocr_line':
		min_sep = syntax.ocr['bbox'][2] - syntax.ocr['bbox'][0]
		last_x = None
		for word in syntax.content:
			if isinstance(word, (html.Tag, html.STag)):
				if last_x:
					sep = word.ocr['bbox'][0] - last_x
					if sep > 0:
						min_sep = min(min_sep, sep)
				last_x = word.ocr['bbox'][2]
		
		if min_sep < 60:
			for i in reversed(range(0, len(syntax.content))):
				word = syntax.content[i]
				if i > 0:
					if not isinstance(syntax.content[i-1], (html.Tag, html.STag)) and not isinstance(word, (html.Tag, html.STag)):
						syntax.content[i-1] += word
						del syntax.content[i]
					elif not isinstance(syntax.content[i-1], (html.Tag, html.STag)):
						word.content = [syntax.content[i-1]] + word.content
						del syntax.content[i-1]
					elif not isinstance(word, (html.Tag, html.STag)):
						syntax.content[i-1].content += [word]
						del syntax.content[i]
					else:
						sep = word.ocr['bbox'][0] - syntax.content[i-1].ocr['bbox'][2]
						if abs(sep - min_sep) < 30:
							syntax.content[i-1].content += word.content
							#syntax.content[i-1].content = ' '.join(syntax.content[i-1].content)
							syntax.content[i-1].ocr['bbox'][2] = max(syntax.content[i-1].ocr['bbox'][2], word.ocr['bbox'][2])
							del syntax.content[i]
		if len(syntax.content) == 1:
			syntax.content = syntax.content[0].content
			
	return syntax

def consolidate_paras(syntax, parent=None, left=None):
	if 'class' in syntax.attrs and syntax.attrs['class'] == 'ocr_par':
		min_sep = syntax.ocr['bbox'][3] - syntax.ocr['bbox'][1]
		last_x = None
		for word in syntax.content:
			if isinstance(word, (html.Tag, html.STag)):
				if last_x:
					sep = word.ocr['bbox'][1] - last_x
					if sep > 0:
						min_sep = min(min_sep, sep)
				last_x = word.ocr['bbox'][3]
		
		if min_sep < 60:
			for i in reversed(range(0, len(syntax.content))):
				word = syntax.content[i]
				if i > 0:
					if not isinstance(syntax.content[i-1], (html.Tag, html.STag)) and not isinstance(word, (html.Tag, html.STag)):
						syntax.content[i-1] += word
						del syntax.content[i]
					elif not isinstance(syntax.content[i-1], (html.Tag, html.STag)):
						word.content = [syntax.content[i-1]] + word.content
						del syntax.content[i-1]
					elif not isinstance(word, (html.Tag, html.STag)):
						syntax.content[i-1].content += [word]
						del syntax.content[i]
					else:
						sep = word.ocr['bbox'][1] - syntax.content[i-1].ocr['bbox'][3]
						if abs(sep - min_sep) < 50:
							syntax.content[i-1].content += word.content
							#syntax.content[i-1].content = ' '.join(syntax.content[i-1].content)
							syntax.content[i-1].ocr['bbox'][3] = max(syntax.content[i-1].ocr['bbox'][3], word.ocr['bbox'][3])
							del syntax.content[i]
		if len(syntax.content) == 1:
			syntax.content = syntax.content[0].content
			
	return syntax


parser = etree.HTMLParser(target = parse.Parser())
with open(sys.argv[1], 'r') as fptr:
	parser.feed(fptr.read())
syntax = parser.close().syntax.content[0]

syntax = parse.walk(syntax, parse_ocr_attrs)
syntax = parse.walk(syntax, fix_contractions)
syntax = parse.walk(syntax, trim_empty)
syntax = parse.walk(syntax, consolidate_lines)
syntax = parse.walk(syntax, consolidate_paras)
#syntax = parse.walk(syntax, align_lines)
#syntax = parse.walk(syntax, align_words)
syntax = parse.walk(syntax, set_position)

headStyle = css.Css()
allocr = css.Style()
allocr.set("position", "absolute")
allocr.set("margin-top", "0px")
allocr.set("margin-bottom", "0px")
allocr.set("margin-left", "0px")
allocr.set("margin-right", "0px")
headStyle.elems['.ocr_page,.ocr_carea,.ocr_par,.ocr_line,.ocrx_word'] = allocr
syntax['head'][0] << (html.Style() << headStyle)

print(syntax)

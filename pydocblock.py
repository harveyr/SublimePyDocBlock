import re
import textwrap

import sublime
import sublime_plugin


DOCSTRING_SELECTOR = 'string.quoted.double.block.python'
COMMENT_SELECTOR = 'comment.line.number-sign.python'

COMMENT_REX = re.compile(r'^(\s*)(#|##)', re.MULTILINE)
DOCSTRING_START_REX = re.compile(r'^(\s*)"""|\'\'\'', re.MULTILINE)

LINE_LENGTH = 79


class BaseCommand(sublime_plugin.TextCommand):
    @property
    def sel_start(self):
        return self.view.sel()[0].a

    @property
    def current_scope(self):
        return self.view.scope_name(self.sel_start)

    @property
    def in_docstring(self):
        return DOCSTRING_SELECTOR in self.current_scope

    @property
    def in_comment(self):
        return (
            COMMENT_SELECTOR in self.current_scope or
            COMMENT_REX.match(self.view.substr(self.view.line(self.sel_start)))
        )


class ReformatPyCommentCommand(BaseCommand):
    def run(self, edit):
        if self.in_docstring:
            replace_region, replace_str = self.reformat_docstring()
        elif self.in_comment:
            replace_region, replace_str = self.reformat_comment()
        else:
            raise RuntimeError(
                'Inoperable scope: {}'.format(self.current_scope)
            )
        self.view.replace(edit, replace_region, replace_str)

    def paragraphs(self, source):
        paragraphs = [[]]
        for line in source.splitlines():
            line_words = [w for w in line.split(' ') if w]
            if not line_words and paragraphs[-1]:
                paragraphs += [[]]
            else:
                paragraphs[-1] += line_words

        return paragraphs

    def reformat_docstring(self):
        """

        Reformats doctring.
    
        This docstring doesn't look so good.

        Here is some more text that will help me test stuff because testing stuff is important and stuff.

        And here's another paragraph asdf asd fa sdf asdf asd fas dfas dfsa df
        asf asdf pineapple"""
        if self.view.sel()[0].size():
            region = self.view.sel()[0]
        else:
            region = self.full_docstring_region()

        source = self.view.substr(region)
        whitespace = re.search(r'^\s+', source).group(0)
        first_line = ''.join([whitespace, '"""'])

        paragraphs = self.paragraphs(re.sub(r'"""|\'\'\'', '', source))
        while not paragraphs[-1]:
            paragraphs.pop(-1)
        paragraphs += [['"""']]

        buf = ''
        for idx, para in enumerate(paragraphs):
            para_text = textwrap.fill(
                ' '.join(para),
                width=LINE_LENGTH,
                initial_indent=first_line if idx == 0 else whitespace,
                subsequent_indent=whitespace
            )
            buf += '\n'.join([para_text, '\n'])

        return region, buf.rstrip()

    def reformat_comment(self):
        if self.view.sel()[0].size():
            region = self.view.sel()[0]
        else:
            region = self.full_comment_region()
        leading_whitespace = COMMENT_REX.search(
            self.view.substr(self.view.lines(region)[0])
        ).group(1)

        source = COMMENT_REX.sub('', self.view.substr(region))
        paragraphs = self.paragraphs(source)
        line_start = ''.join([leading_whitespace, '# '])

        buf = ''
        for para in paragraphs:
            if not para:
                buf += '\n\n'
            else:
                buf += textwrap.fill(
                    ' '.join(para),
                    width=LINE_LENGTH,
                    initial_indent=line_start,
                    subsequent_indent=line_start
                )

        return region, buf

    def next_line(self, region, direction):
        if direction == 'backward':
            return self.view.line(region.begin() - 1)
        elif direction == 'forward':
            return self.view.line(region.end() + 1)
        else:
            raise RuntimeError('Unexpected direction: {}'.format(direction))

    def expanded_region_by_rex(self, region, rex, direction):
        expanded_region = sublime.Region(region.a, region.b)
        next_line = self.next_line(expanded_region, direction)
        while rex.match(self.view.substr(next_line)):
            expanded_region = expanded_region.cover(next_line)
            next_line = self.next_line(expanded_region, direction)

        return expanded_region

    def expand_cursor_region(self, rex):
        region = self.view.line(self.sel_start)
        for direction in ['forward', 'backward']:
            region = self.expanded_region_by_rex(
                region, rex, direction
            )

        return region

    def full_comment_region(self):
        return self.expand_cursor_region(COMMENT_REX)

    def full_docstring_region(self):
        region = self.full_region_by_selector(DOCSTRING_SELECTOR)
        lines = self.view.lines(region)
        return region.cover(self.view.line(lines[0].begin()))

    def full_region_by_selector(self, selector):
        cursor = self.sel_start
        regions = self.view.find_by_selector(selector)
        for region in regions:
            if region.contains(cursor):
                return region
        return None

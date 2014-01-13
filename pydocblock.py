import re
import textwrap

import sublime
import sublime_plugin


DOCSTRING_SELECTOR = 'string.quoted.double.block.python'
COMMENT_SELECTOR = 'comment.line.number-sign.python'

COMMENT_REX = re.compile(r'^(\s*)(#|##)', re.MULTILINE)
DOCSTRING_START_REX = re.compile(r'^(\s*)"""|\'\'\'', re.MULTILINE)
FUNC_DEF_REX = re.compile(r'^\s*def [_\w]+\((.+)\):')
WHITESPACE_REX = re.compile(r'^\s+', re.MULTILINE)
RAISES_REX = re.compile(r'raise (\w+)\b')

LINE_LENGTH = 79


class BaseCommand(sublime_plugin.TextCommand):
    @property
    def sel_start(self):
        return self.view.sel()[0].a

    @property
    def current_line(self):
        return self.view.line(self.sel_start)

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

    def next_line(self, region, direction):
        if direction == 'backward':
            return self.view.line(region.begin() - 1)
        elif direction == 'forward':
            return self.view.line(region.end() + 1)
        else:
            raise RuntimeError('Unexpected direction: {}'.format(direction))

    def format_sphinx_paragraph(self, paragraph, indent):
        """Returns formatted text for a sphinx paragraph.

        :param list paragraph: List of words in the sphinx doc section
                               (including param, type).
        :param str indent: Whitespace indent.
        :return: Formatted text super long asd fasdf amdf asdflkasdfl kasdflk
                 adlskf a.

        """
        sections = [[]]
        for word in paragraph:
            if word[0] == ':' and sections[-1]:
                sections.append([])
            sections[-1].append(word)

        buf = ''
        section_count = len(sections)
        for idx, section in enumerate(sections):
            start_words = [section[0]]
            while start_words[-1][-1] != ':':
                start_words.append(section[len(start_words)])
            start = ' '.join(start_words)
            rest = section[len(start_words):]
            extra_ident = ' '.join(['' for _ in range(len(start) + 2)])
            buf += textwrap.fill(
                ' '.join(rest),
                width=LINE_LENGTH,
                initial_indent=''.join([indent, start, ' ']),
                subsequent_indent=indent + extra_ident
            )
            if idx < section_count - 1:
                buf += '\n'

        return buf

    def reformat_docstring(self):
        """Reformats doctring.

        This docstring doesn't look so good but is useful for testing this plugin.

        Here is some more text that will help me test stuff because testing stuff is important and stuff.

        And here's another paragraph asdf asd fa sdf asdf asd fas dfas dfsa df asd fa sdf kadsflakf 
        asf asdf pineapple

        :param self: Normally we wouldn't document 'self' but we're sorta testing some
                     stuffs out Here is the next line of the self thing.
        :type self: blah asdf
        :return: str

        """
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
            if para[0][0] == ':':
                para_text = self.format_sphinx_paragraph(
                    para,
                    indent=whitespace
                )
            else:
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
            para_text = textwrap.fill(
                ' '.join(para),
                width=LINE_LENGTH,
                initial_indent=line_start,
                subsequent_indent=line_start
            )
            buf += '\n'.join([para_text, '\n'])

        return region, buf.rstrip()

    # This is a funky comment. Supa fly funky style. Because with comments like these, who needs comments?
    # Here's some more.
    # The other thing is that things.

    def paragraphs(self, source):
        paragraphs = [[]]
        for line in source.splitlines():
            line_words = [w for w in line.split(' ') if w]
            if not line_words and paragraphs[-1]:
                paragraphs += [[]]
            else:
                paragraphs[-1] += line_words

        return paragraphs

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

    def split_docstring(self, docstring):
        intro = []
        sphinx = []
        for l in docstring.splitlines():
            if l[0] == ':':
                sphinx.append(l)
            else:
                intro.append(l)
        return '\n'.join(intro), '\n'.join(sphinx)

    def whitespace(self, line=None, region=None):
        if not any([line, region]):
            raise ValueError('Must provide line or region')
        if region:
            line = self.view.substr(region).splitlines()[0]
        match = WHITESPACE_REX.search(line)
        if match:
            return match.group(0)
        return None

    def full_function_region(self, region=None):
        region = region or self.current_line
        start_line = self.view.line(region.begin())
        while not FUNC_DEF_REX.match(self.view.substr(start_line)):
            start_line = self.next_line(start_line, 'backward')

        end_line = self.next_line(start_line, 'forward')
        while (
            not FUNC_DEF_REX.match(self.view.substr(end_line)) and
            end_line.end() < self.view.size() - 1
        ):
            end_line = self.next_line(end_line, 'forward')

        return start_line.cover(end_line)

    def find_raises(self, region):
        return RAISES_REX.findall(self.view.substr(region))


class GenerateSphinxDocstringCommand(BaseCommand):
    """WIP"""
    def run(self, edit):
        func_args = self.find_func_args()
        docstring_region = self.full_docstring_region()
        whitespace = self.whitespace(region=docstring_region)
        docs = self.spinx_docs(
            func_args,
            exceptions=self.find_raises(self.full_function_region()),
            whitespace=whitespace
        )
        self.view.insert(edit, self.sel_start, docs)

    def spinx_docs(self, args, exceptions, whitespace):
        p_template = ':param {0}: \n:type {0}: '
        exceptions_template = ':raises {}: '
        sections = (
            [p_template.format(a) for a in args] +
            [':return: description\n:rtype: '] +
            [exceptions_template.format(e) for e in exceptions]
        )
        text = '\n'.join(sections)
        return '\n'.join(
            [(whitespace + l) for l in text.splitlines()]
        )

    def find_func_args(self, bingo='Flase', tester=None):
        """

        """
        test_line = self.current_line
        args = []
        while True:
            line_text = self.view.substr(test_line)
            match = FUNC_DEF_REX.match(line_text)
            if match:
                args = [a.strip() for a in match.group(1).split(',') if a]
                break
            if test_line.begin() == 0:
                raise RuntimeError('No func definition found!')
            test_line = self.next_line(test_line, 'backward')

        if args:
            args = [a.split('=')[0] for a in args]

        if 'self' in args:
            args.pop(args.index('self'))

        return args


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

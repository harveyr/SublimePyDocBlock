import sublime
import sublime_plugin
import re


DOCSTRING_SELECTOR = 'string.quoted.double.block.python'
COMMENT_SELECTOR = 'comment.line.number-sign.python'

COMMENT_REX = re.compile(r'^(\s*)(#|##)', re.MULTILINE)

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

        # adf as dfa sdfa sdfa f f asdf asd fasd dfs asd f asdf asdf asdf sdaf
        # asd fa sdf asdf asdf a sdf asdf asdf asd fas dfa sdf asdf


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

    def reformat_docstring(self):
        region = self.full_region_by_selector(DOCSTRING_SELECTOR)

    def reformat_comment(self):
        if self.view.sel()[0].size():
            region = self.view.sel()[0]
        else:
            region = self.full_comment_region()
        leading_whitespace = COMMENT_REX.search(
            self.view.substr(self.view.lines(region)[0])
        ).group(1)

        lines = COMMENT_REX.sub('', self.view.substr(region)).splitlines()
        joined = ' '.join([l.strip() for l in lines if l.strip()])

        line_start = ''.join([leading_whitespace, '#'])
        buf = line_start
        for word in [w for w in joined.split(' ') if w]:
            current_line = buf.splitlines()[-1]
            if len(current_line) + len(word) + 1 <= LINE_LENGTH:
                buf += ''.join([' ', word])
            else:
                buf += ''.join(['\n', line_start, ' ', word])

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

    def full_comment_region(self):
        region = self.view.line(self.sel_start)
        for direction in ['forward', 'backward']:
            region = self.expanded_region_by_rex(
                region, COMMENT_REX, direction
            )

        return region

    def full_region_by_selector(self, selector):
        cursor = self.sel_start
        regions = self.view.find_by_selector(selector)
        for region in regions:
            if region.contains(cursor):
                return region
        return None


    def insert_docblock(self, edit):
        """
        DESCRIPTION

        :param edit: [edit Description]
        :type edit: [edit Type]
        """


        def indented (text): return "{}{}".format(self.leading_whitespace, text)
        buffer = '\n'
        buffer += indented('"""\n')
        buffer += indented('DESCRIPTION')
        buffer += '\n'

        for arg in self.args:
            buffer += '\n'
            buffer += indented(':param {0}: [{0} Description]\n'.format(arg))
            buffer += indented(':type {0}: [{0} Type]\n'.format(arg))

        buffer += indented('"""\n')

        view = self.active_view()
        eol = view.line(self.end_region).end()
        self.view.insert(edit, eol, buffer)


    def extract_args(self):
        view = self.active_view()
        text = view.substr(self.start_region.cover(self.end_region))
        self.args = [arg.strip() for arg in re.split(r'\(|,|\)|:', text)[1:] \
            if arg.strip() != '' and arg.strip() != 'self']
        print(self.args)


    def find_start_region(self):
        view = self.active_view()
        starting_region = view.sel()[0]

        max_search = 30
        region = view.sel()[0]
        target_region = None
        for x in range(1, max_search):
            line = view.line(region)
            line_text = view.substr(line)
            matches = re.match(r'(\s*?)def \S+\(', line_text)
            if matches:
                self.leading_whitespace = matches.group(1) + '    '
                return line
            region = sublime.Region(
                line.begin() - 1,
                line.begin() - 1)

        print('No function definition found within {} lines'.format(max_search))
        return None

    def find_end_region(self):
        if self.start_region is None:
            return None

        view = self.active_view()
        region = self.start_region
        for x in range(1, 30):
            line = view.line(region)
            line_text = view.substr(line)
            if re.search(r'\):', line_text):
                return line
            region = sublime.Region(
                line.end() + 1,
                line.end() + 1)

        print('Is there any end to these arguments?')
        return None

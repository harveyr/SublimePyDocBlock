# http://www.sublimetext.com/docs/commands
# http://www.sublimetext.com/docs/2/api_reference.html

import sublime, sublime_plugin
import re


class PydocblockCommand(sublime_plugin.TextCommand):
    start_region = None
    end_region = None

    def run(self, edit):
        self.start_region = self.find_start_region()
        if self.start_region is None:
            print('No start region found')
            return

        self.end_region = self.find_end_region()
        if self.end_region is None:
            print('No end region found.')

        self.extract_args()

        self.insert_docblock(edit)

        # text = ' '.join(text.split('\n'))
        # print(text)
        # args_string = re.findall(r'\((.*)\)', text)
        # args = [arg.trim() for arg in args_matches]

    def test_case(
        arg1,
        arg2,
        arg3):
        pass

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

    def log_str(self, var_name):
        ws = self.leading_whitespace()
        trimmed = self.trim_quoted_output(var_name)
        print(var_name)
        print(trimmed)
        if self.in_python():
            return ("{0}logger.debug('{1}: ' + str({2}))").format(ws,
                trimmed, var_name)

        if self.in_js():
            return (
                "{0}console.log('{1}:', {2});").format(ws, trimmed,
                var_name)

        if self.in_coffee():
            return (
                "{0}console.log '{1}:', {2}").format(ws, trimmed, var_name)

        if self.in_php():
            return (
                '{0}print("\\n-----\\n" . \'{1}:\'); ' +
                'var_dump({2}); ' +
                'print("\\n-----\\n"); ' +
                "ob_flush();").format(ws, trimmed, var_name)

    def trim_quoted_output(self, output):
        return re.sub(r'\'|\"', '', output)

    def insert_with_newline(self, edit, text):
        view = self.active_view()
        eol = view.line(view.sel()[0]).end()
        self.view.insert(edit, eol, "\n{}".format(text))

    def get_cursor_word(self):
        view = self.active_view()
        word = view.substr(view.sel()[0]).strip()
        if len(word) == 0:
            return None
        return word

    def leading_whitespace(self):
        view = self.active_view()
        line = view.substr(view.line(view.sel()[0]))
        matches = re.findall(r'(\s*)\S+', line)
        return matches[0]

    def in_python(self):
        return 'python' in self.current_scope()

    def in_php(self):
        return 'source.php' in self.current_scope()

    def in_js(self):
        return 'source.js' in self.current_scope()

    def in_coffee(self):
        return 'source.coffee' in self.current_scope()

    def current_scope(self):
        print(self.active_view().scope_name(0))
        return self.active_view().scope_name(0)

    def active_view(self):
        return sublime.active_window().active_view()

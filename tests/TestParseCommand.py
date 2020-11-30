import unittest
import shlex

from easyfuse.parse_command import parse_command, ParserError


class TestParseCommand(unittest.TestCase):
    def test_parse_plain(self):
        cmd = parse_command('command argument argument', {})
        self.assertEqual(cmd, ['command', 'argument', 'argument'])

    def test_parse_mapping(self):
        cmd = parse_command('command {argument1} {argument2}', {
            'argument1': 'value1',
            'argument2': 'value2'
        })
        self.assertEqual(cmd, ['command', 'value1', 'value2'])

    def test_parse_optional(self):
        cmd = parse_command('command [{argument1}] {argument2}', {
            'argument1': 'value1',
            'argument2': 'value2'
        })
        self.assertEqual(cmd, ['command', 'value1', 'value2'])
        cmd = parse_command('command [{argument1}] {argument2}', {
            'argument1': '',
            'argument2': 'value2'
        })
        self.assertEqual(cmd, ['command', 'value2'])
        cmd = parse_command('command [{argument1}] {argument2}',
                            {'argument2': 'value2'})
        self.assertEqual(cmd, ['command', 'value2'])

    def test_parse_unroll(self):
        cmd = parse_command('command [tag {argument1}] {argument2}', {
            'argument1': 'value1\nvalue2',
            'argument2': 'value3'
        })
        self.assertEqual(
            cmd, ['command', 'tag', 'value1', 'tag', 'value2', 'value3'])
        
    def test_parse_escaped(self):
        test = "import sys; open(sys.argv[1], 'w').write(repr(sys.argv))"
        ctest = f"/usr/bin/env python {shlex.quote(test)}"
        cmd = parse_command(ctest, {})
        self.assertEqual(cmd, ["/usr/bin/env", "python", test])

    def test_errors(self):
        with self.assertRaises(ParserError) as ctx:
            parse_command('cmd [tag', {})
        self.assertEqual(str(ctx.exception), 'unterminated [')
        with self.assertRaises(ParserError) as ctx:
            parse_command('cmd tag]', {})
        self.assertEqual(str(ctx.exception), 'misplaced ]')
        with self.assertRaises(ParserError) as ctx:
            parse_command('cmd [tag [tag]]', {})
        self.assertEqual(str(ctx.exception), 'nested [')
        with self.assertRaises(ParserError) as ctx:
            parse_command('cmd {tag tag}', {})
        self.assertEqual(str(ctx.exception), 'missing }')
        with self.assertRaises(ParserError) as ctx:
            parse_command('cmd {', {})
        self.assertEqual(str(ctx.exception), 'invalid {variable} token')


if __name__ == '__main__':
    unittest.main()

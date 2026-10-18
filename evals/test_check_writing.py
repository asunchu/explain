import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_writing import long_sentences
class WritingTests(unittest.TestCase):
    def test_flags_long_prose(self):
        self.assertEqual(long_sentences(' '.join(['word'] * 26) + '.')[0]['words'], 26)
    def test_protected_code_quotes_and_links(self):
        text = '```\n' + 'word ' * 40 + '\n```\n'
        text += 'Keep `' + 'word ' * 40 + '` unchanged.\n'
        text += 'The message says "' + 'word ' * 40 + '".\n'
        text += 'See [the source](https://example.com/' + 'long/' * 40 + ').'
        self.assertEqual(long_sentences(text), [])
    def test_headings_do_not_join_sentences(self):
        self.assertEqual(long_sentences('**A short title.** Read the file.', 4), [])

    def test_quoted_sentence_boundary_is_preserved(self):
        text = 'The error says "Stop." ' + ' '.join(['word'] * 25) + '.'
        self.assertEqual(long_sentences(text), [])

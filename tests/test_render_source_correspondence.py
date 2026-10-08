"""Pinned primitive formatting and persistent-state correspondence controls."""
import unittest
from src.semantic_contract.public_adapters import (
    Comment, RenderCase, render_parent, render_child,
    ParentRenderSession, ChildRenderSession,
)


class SourceCorrespondenceTests(unittest.TestCase):
    def test_multiline_string_prefixes_only_once(self):
        for level in (0, 1, 3):
            c = RenderCase('multiline', 'a\nb', indent_level=level)
            expected = '  ' * level + 'a\nb'
            self.assertEqual(render_parent(c), expected)
            self.assertEqual(render_child(c), expected)

    def test_multiline_comment_prefixes_only_once(self):
        c = RenderCase('comment', Comment('a\nb'), indent_level=1)
        self.assertEqual(render_parent(c), '  // a\nb')
        self.assertEqual(render_child(c), '  // a\nb')

    def test_suppression_persists_across_calls(self):
        calls = [RenderCase('first', Comment('visible')),
                 RenderCase('enable', 'statement', no_comments=True),
                 RenderCase('later', Comment('hidden'), no_comments=False)]
        for renderer in (ParentRenderSession(), ChildRenderSession()):
            self.assertEqual([renderer.render(c) for c in calls],
                             ['// visible', 'statement', ''])
            self.assertTrue(renderer.no_comments)


if __name__ == '__main__':
    unittest.main()

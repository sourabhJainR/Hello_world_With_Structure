#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".ai-harness"))

from runtime.context_cache import ContextPageCache


class ContextPageCacheTests(unittest.TestCase):
    def test_same_content_reuses_page(self):
        cache = ContextPageCache(page_chars=256)
        first = cache.put("repository", "stable instructions", stable=True)
        second = cache.put("repository", "stable instructions", stable=True)
        self.assertEqual(first.page_id, second.page_id)
        self.assertEqual(cache.hits, 1)
        self.assertEqual(cache.misses, 1)

    def test_changed_content_gets_new_page(self):
        cache = ContextPageCache(page_chars=256)
        first = cache.put("repository", "version one", stable=True)
        second = cache.put("repository", "version two", stable=True)
        self.assertNotEqual(first.page_id, second.page_id)
        self.assertEqual(cache.misses, 2)

    def test_pagination_is_bounded(self):
        cache = ContextPageCache(page_chars=256)
        pages = cache.paginate("history", "x" * 700)
        self.assertEqual([len(page.text) for page in pages], [256, 256, 188])
        selected = cache.select(pages, 520)
        self.assertEqual(len(selected), 2)
        self.assertLessEqual(sum(len(page.text) + 1 for page in selected), 520)


if __name__ == "__main__":
    unittest.main()

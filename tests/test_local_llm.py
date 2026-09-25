import os,unittest
from unittest.mock import patch
from portable.local_llm import LocalLLMConfig, fallback_allowed, generate

class LocalLLMTests(unittest.TestCase):
    def test_fallback_is_read_only(self):
        self.assertTrue(fallback_allowed("Read-only: True"))
        self.assertTrue(fallback_allowed("patch_allowed: false"))
        self.assertFalse(fallback_allowed("Read-only: False"))

    def test_config_has_small_default_budget(self):
        cfg=LocalLLMConfig()
        self.assertEqual(cfg.num_ctx,4096)
        self.assertEqual(cfg.num_predict,768)

    def test_generate_uses_ollama_payload(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return b'{"response":"ok"}'
        with patch("urllib.request.urlopen", return_value=Response()) as opened:
            self.assertEqual(generate("hello"),"ok")
            body=opened.call_args.args[0].data.decode()
            self.assertIn('"stream": false',body)
            self.assertIn('"num_ctx": 4096',body)

if __name__=="__main__":
    unittest.main()

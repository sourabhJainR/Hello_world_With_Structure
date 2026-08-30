import json, tempfile, unittest
from pathlib import Path
import sys
ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'.ai-harness'))
import p1_lifecycle

class LifecycleTests(unittest.TestCase):
    def test_start_finish_produces_portable_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)
            p1_lifecycle.start(run,"fix export","prompt",{"tests":{"command":"pytest"}},{"mode":"implement"})
            manifest={"status":"completed","validation":{"passed":True},"git_diff":"src/export.py\n"}
            proof=p1_lifecycle.finish(run,manifest)
            for name in ("engineering-state.json","repository-dna.json","proof-bundle.json","proof-graph.json","regression-genome.json"):
                self.assertTrue((run/name).exists(),name)
            self.assertTrue(proof["proof_id"].startswith("proof-"))
            genome=json.loads((run/"regression-genome.json").read_text())
            self.assertEqual(genome["result"]["status"],"completed")

if __name__=="__main__":
    unittest.main()

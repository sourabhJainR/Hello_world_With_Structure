import json
import tempfile
import unittest
from pathlib import Path

from portable.agency_provenance import ProvenanceLedger
from .ai_harness.runtime.collaboration import build_handoff, load_handoff, persist_handoff, record_handoff

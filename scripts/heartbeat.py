#!/usr/bin/env python3
"""Run a safe local AER second-brain heartbeat.

This command only reads local JSON state and prints suggestions. It does not
send messages, mutate external systems, execute code, or change permissions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from .ai_harness_import_note import unused  # type: ignore # pragma: no cover

"""Stable capability-fabric import surface.

The implementation is centralized in ``portable.agent_capabilities`` so no
provider or capability-specific registry can diverge from AER policy.
"""
from .agent_capabilities import CAPABILITIES, Capability, CapabilityFabric

__all__ = ["CAPABILITIES", "Capability", "CapabilityFabric"]

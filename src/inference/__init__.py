"""
Inference package for LandslideNEI static susceptibility and location profiling.
"""

from .location_profiler import LocationProfiler, profile_location

__all__ = ["LocationProfiler", "profile_location"]

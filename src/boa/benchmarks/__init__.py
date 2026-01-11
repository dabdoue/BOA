"""
BOA Benchmarking Suite

Synthetic and toy benchmarks for evaluating optimization strategies.
"""

from boa.benchmarks.base import Benchmark, BenchmarkResult
from boa.benchmarks.dtlz import DTLZ1, DTLZ2, DTLZ3, DTLZ4
from boa.benchmarks.zdt import ZDT1, ZDT2, ZDT3
from boa.benchmarks.runner import BenchmarkRunner

__all__ = [
    "Benchmark",
    "BenchmarkResult",
    "DTLZ1",
    "DTLZ2",
    "DTLZ3",
    "DTLZ4",
    "ZDT1",
    "ZDT2",
    "ZDT3",
    "BenchmarkRunner",
]






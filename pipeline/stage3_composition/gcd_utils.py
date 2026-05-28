"""Utilities for GCD-like computations on float step sizes.

Stage 3 Step 5 (paper): derive a *base tick* as the greatest common divisor (GCD)
across per-FMU step sizes, then schedule each FMU at an integer multiple of that
base tick.

Floats are tricky: binary floating point rarely represents decimal steps
exactly. This module implements a deterministic, best-effort approach:

1) If all step sizes are compatible with a fixed decimal grid of 1e-6 (i.e.
   scaling by 1e6 yields integers within a tight tolerance), compute an integer
   GCD in that scaled space.

2) Otherwise, approximate each step as a rational using `Fraction(str(x))`
   limited to denominator <= 1e6, then compute a rational GCD via a common
   denominator LCM.

Safeguards:
- Always returns a positive float when possible.
- If the computed GCD collapses to 0 (numerical/pathological inputs), callers
  should fall back to `min(steps)` and record a warning.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd
from typing import Iterable, List, Tuple


MICRO_SCALE = 10**6


def _lcm(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return abs(a // gcd(a, b) * b)


def _all_microgrid(steps: List[float], *, scale: int = MICRO_SCALE, tol: float = 1e-9) -> bool:
    """Return True if each step is (approximately) an integer multiple of 1/scale."""

    for h in steps:
        if h <= 0:
            return False
        x = h * scale
        xi = round(x)
        if abs(x - xi) > tol:
            return False
    return True


def gcd_like_base_tick(steps: Iterable[float], *, max_den: int = MICRO_SCALE) -> Tuple[float, str]:
    """Compute a GCD-like base tick from float step sizes.

    Args:
        steps: positive float step sizes.
        max_den: maximum denominator for rational approximation.

    Returns:
        (base_tick, method) where method is one of:
        - 'microgrid_gcd'
        - 'fraction_gcd'

    Note:
        This function does not emit warnings; callers should validate that the
        returned base_tick is > 0 and reasonable.
    """

    arr = [float(x) for x in steps if float(x) > 0]
    if not arr:
        return 0.0, "microgrid_gcd"

    # Path 1: integer GCD on a 1e-6 grid
    if _all_microgrid(arr, scale=MICRO_SCALE):
        ints = [int(round(h * MICRO_SCALE)) for h in arr]
        g = 0
        for v in ints:
            g = gcd(g, abs(v))
        return (float(g) / float(MICRO_SCALE)) if g > 0 else 0.0, "microgrid_gcd"

    # Path 2: rational approximation (deterministic)
    fracs = [Fraction(str(h)).limit_denominator(max_den) for h in arr]

    # common denominator via LCM
    den = 1
    for f in fracs:
        den = _lcm(den, f.denominator)
        if den == 0:
            break

    if den <= 0:
        return 0.0, "fraction_gcd"

    nums = [f.numerator * (den // f.denominator) for f in fracs]
    g = 0
    for n in nums:
        g = gcd(g, abs(int(n)))

    base = Fraction(g, den) if g > 0 else Fraction(0, 1)
    return float(base), "fraction_gcd"

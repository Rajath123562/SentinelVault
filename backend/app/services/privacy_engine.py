"""Differential Privacy Engine implementing real Laplace noise for HOTFIX."""

import math
import secrets
import sys
import types
from typing import Optional

EPSILON_ALLOWLIST = {0.1, 0.2, 0.5, 1.0}
SENSITIVITY = 1.0
MECHANISM_NAME = "Laplace"
DEMO_ACCOUNTING_NOTICE = "DEMO ACCOUNTING ACTIVE — OFFICIAL CONFORMANCE NOT VERIFIED"

# Safely import IBM diffprivlib's Laplace mechanism
try:
    if "diffprivlib" not in sys.modules:
        sys.modules["diffprivlib.models"] = types.ModuleType("diffprivlib.models")
    from diffprivlib.mechanisms import Laplace as DiffprivlibLaplace
    HAS_DIFFPRIVLIB = True
except Exception:
    HAS_DIFFPRIVLIB = False


def _csprng_laplace_sample(scale: float) -> float:
    """
    Generates a Laplace noise sample using cryptographically secure random bits
    and inverse transform sampling:
    Laplace(0, b) = -sgn(U) * b * ln(1 - 2|U|), where U in (-0.5, 0.5)
    """
    # Sample 53 bits of cryptographic entropy for standard IEEE 754 float precision
    u_int = secrets.randbits(53)
    u_float = u_int / (1 << 53)  # Uniform in [0, 1)

    # Shift to (-0.5, 0.5), guarding against exact 0
    u = u_float - 0.5
    if u == 0:
        u = 1e-15

    sign = 1.0 if u > 0 else -1.0
    return -sign * scale * math.log(1.0 - 2.0 * abs(u))


def apply_laplace_noise(exact_count: int, epsilon: float, seed: Optional[int] = None) -> int:
    """
    Applies the differential privacy Laplace mechanism to a count query.

    Parameters:
    - exact_count: Ground truth count of distinct protected privacy units.
    - epsilon: Privacy expenditure parameter (must be in approved allowlist).
    - seed: Optional deterministic seed strictly reserved for isolated tests.

    Returns:
    - Noisy count clamped to non-negative integer via valid post-processing.
    """
    if epsilon not in EPSILON_ALLOWLIST:
        raise ValueError(
            f"Invalid epsilon: {epsilon}. Must be one of approved values: {sorted(list(EPSILON_ALLOWLIST))}"
        )
    if exact_count < 0:
        raise ValueError(f"Exact count cannot be negative, got {exact_count}")

    scale = SENSITIVITY / epsilon

    try:
        if HAS_DIFFPRIVLIB and seed is None:
            # Production execution using IBM diffprivlib with system entropy
            mech = DiffprivlibLaplace(epsilon=epsilon, sensitivity=SENSITIVITY)
            noisy_val = mech.randomise(float(exact_count))
        elif HAS_DIFFPRIVLIB and seed is not None:
            # Deterministic test execution
            mech = DiffprivlibLaplace(epsilon=epsilon, sensitivity=SENSITIVITY, random_state=seed)
            noisy_val = mech.randomise(float(exact_count))
        else:
            # CSPRNG fallback
            noise = _csprng_laplace_sample(scale)
            noisy_val = exact_count + noise

        # Valid post-processing: Clamp to non-negative integer
        clamped_count = max(0, int(round(noisy_val)))
        return clamped_count

    except Exception as e:
        # FAIL-CLOSED: Never expose the exact count if noise generation fails!
        raise RuntimeError(f"Differential privacy mechanism execution failed: {e}") from e

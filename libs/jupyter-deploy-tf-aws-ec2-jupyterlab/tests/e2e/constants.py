"""Constants for E2E test ordering (jupyterlab template).

Test Execution Order
====================

1. **Deployment test** (order=1) — verifies the app is reachable the moment `jd up` finishes.
2. **Mutating tests** (order >= 10) — two in-place `jd up` cycles on the SAME deployment.
3. **Non-ordered tests** — run LAST (pytest-order runs positive-ordinal tests first).

The mutating ordinals are load-bearing, not cosmetic: this suite deliberately mutates ONE
deployment in place rather than deploying one project per configuration, because the
transitions are the coverage — terraform replacing the instance under a persisted data
volume, the volume reattaching at boot, the package-manager environment rebuilding, the app
returning on the same pinned cert. Apply #2 (`pixi -> uv`) is only meaningful after apply #1
(`uv -> pixi` + GPU), so `-k test_mutating_cpu_uv` on its own is NOT a valid entry point.
Do not "optimize" these into two independent runs.
"""

# Deployment test — runs first
ORDER_DEPLOYMENT = 1

# Mutating tests — after the deployment test, before the non-ordered tests
_MUTATING_BASE = 10

# Apply #1: t3.medium + uv  ->  GPU + pixi + external EBS/EFS mounts + larger log retention
ORDER_MUTATING_GPU_PIXI = _MUTATING_BASE  # 10

# Apply #2: GPU + pixi  ->  CPU + uv (external volumes stay mounted)
ORDER_MUTATING_CPU_UV = _MUTATING_BASE + 10  # 20

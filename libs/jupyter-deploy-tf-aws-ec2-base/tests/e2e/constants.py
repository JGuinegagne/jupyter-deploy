"""Constants for E2E test ordering.

Test Execution Order
====================

E2E tests run in the following sequence:

1. **Deployment test** (order=1):
   - Initial deployment and setup

2. **Non-ordered tests** (no order marker):
   - Run in arbitrary order after deployment
   - Cover: application, config_set, host, open, org_and_teams, server, show,
     undeployed_project, users, utils

3. **Mutating tests** (order >= 100):
   - Run LAST to avoid interfering with non-mutating tests
   - Only run with flag `mutate=true` in `just test-e2e`
   - Run in specific order with controlled dependencies
   - Each group starts at base + (group_number * 10)
"""

# Deployment test - runs first
ORDER_DEPLOYMENT = 1

# Mutating tests - run last, in specific order
# Base starting point for all mutating tests (chosen to run after ~53 non-ordered tests)
_MUTATING_BASE = 100
ORDER_CONFIG_APPLY = _MUTATING_BASE
ORDER_UV = _MUTATING_BASE + 10
ORDER_PIXI = _MUTATING_BASE + 20
ORDER_EXTERNAL_VOLUMES = _MUTATING_BASE + 30
ORDER_GPU = _MUTATING_BASE + 40

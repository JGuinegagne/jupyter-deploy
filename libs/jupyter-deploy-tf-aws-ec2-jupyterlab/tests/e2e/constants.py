"""Constants for E2E test ordering (jupyterlab template).

The deployment test runs first (order=1) to verify the app is reachable the moment
`jd up` finishes. All other tests are unordered and run after it (pytest-order runs
positive-ordinal tests before unordered ones).
"""

# Deployment test — runs first
ORDER_DEPLOYMENT = 1

import os

# Maximum number of user+assistant turn pairs kept in the sliding window.
# Each pair = 2 messages; older pairs are evicted when the limit is exceeded.
MAX_TURNS: int = int(os.getenv("MAX_TURNS", "6"))

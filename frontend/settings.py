import os

# Where your FastAPI backend runs
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Demo user id (until you wire auth)
DEFAULT_USER_ID = int(os.getenv("DEMO_USER_ID", "1"))

# Requests timeout (seconds)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))

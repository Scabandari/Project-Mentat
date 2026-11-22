"""Print the OpenAPI schema to stdout without running the server."""

import json
import sys

from app.main import app

if __name__ == "__main__":
    json.dump(app.openapi(), sys.stdout, indent=2)
    sys.stdout.write("\n")

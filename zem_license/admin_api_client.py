"""Re-export admin client from admin_tools (not for end-user builds)."""

import os
import sys

_admin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_tools")
if _admin_dir not in sys.path:
    sys.path.insert(0, _admin_dir)

from admin_api_client import AdminAPIClient, resolve_admin_key  # noqa: F401

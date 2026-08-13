import os
import sys

os.environ.pop("BACKUP_API_KEY", None)
os.environ["EXPLORERFRAME_WINDOWS_ONLY"] = "false"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["MONGO_URI"] = "mongodb://127.0.0.1:1"

import app as explorer_app

client = explorer_app.app.test_client()
response = client.get("/", headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
assert response.status_code in {200, 302}, response.status_code
assert explorer_app._is_blocked_platform() is False
print("EXPLORERFRAME_IMPORT_OK")
print(f"INDEX_STATUS={response.status_code}")
print("WINDOWS_ONLY_DEFAULT_OFF_OK")

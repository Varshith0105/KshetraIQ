import sys
sys.path.insert(0, 'backend')
print("Importing config...", flush=True)
from app.core.config import Settings
print("Importing main...", flush=True)
from app.main import create_app
print("Creating app...", flush=True)
app = create_app(Settings(environment='test', _env_file=None))
print("App created! Testing direct function call...", flush=True)
print("Routes:", [r.path for r in app.routes if hasattr(r, 'path')])
from starlette.testclient import TestClient
print("Creating TestClient...", flush=True)
client = TestClient(app)
print("Sending GET /health...", flush=True)
resp = client.get("/health")
print("Response:", resp.status_code, resp.json(), flush=True)

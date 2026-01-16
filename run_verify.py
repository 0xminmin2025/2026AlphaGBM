
import sys
import os
sys.path.append(os.getcwd())

print(f"CWD: {os.getcwd()}")
print(f"Path: {sys.path}")

try:
    from refactor.backend.app import create_app
    app = create_app()
    print("Backend App created successfully")
    print("Registered Blueprints:", list(app.blueprints.keys()))
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

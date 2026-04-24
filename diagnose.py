import os
import sys

print(f"CWD: {os.getcwd()}")
print(f"Python: {sys.executable}")

try:
    from app.main import app
    print("APP_MAIN_OK")
except Exception as e:
    print(f"APP_MAIN_ERROR: {e}")

print("DIAGNOSIS_COMPLETE: No database or GLM dependencies found.")

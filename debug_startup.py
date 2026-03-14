
import uvicorn
import sys
import traceback

if __name__ == "__main__":
    try:
        from api import app
        print("Successfully imported app from api.py")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")
    except Exception as e:
        print("CRITICAL ERROR DURING STARTUP:")
        traceback.print_exc()
        sys.exit(1)

import threading

from configs.supabase import run_websocket_listener
from main import app

if __name__ == "__main__":
    websocket_thread = threading.Thread(target=run_websocket_listener)
    websocket_thread.start()
    app.run()

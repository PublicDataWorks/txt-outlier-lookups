from realtime.connection import Socket

import time
SUPABASE_ID = "pshrrdazlftosdtoevpf"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBzaHJyZGF6bGZ0b3NkdG9ldnBmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcwMTg5MTgzMiwiZXhwIjoyMDE3NDY3ODMyfQ.G-3C1vARyYT6CtIP_0qaHwwTu-g60afVw9akeabQA2g"

def callback1(payload):
    print("Callback 1: ", payload)


if __name__ == "__main__":
    URL = f"wss://{SUPABASE_ID}.supabase.co/realtime/v1/websocket?apikey={API_KEY}&vsn=1.0.0"
    s = Socket(URL)
    s.connect()

    channel_1 = s.set_channel("realtime:public:lookup_template")
    channel_1.join().on("*", callback1)
    # s.listen()

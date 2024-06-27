import os

from dotenv import load_dotenv
from realtime import Channel
from realtime.connection import Socket
import asyncio
from typing import cast
import logging


from configs.cache_template import update_lookup_templates_cache

load_dotenv(override=True)

supabase_id = os.environ.get("SUPABASE_ID")
api_key = os.environ.get("API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def callback1(payload):
    print(payload)
    if payload.get('message') != "Subscribed to PostgreSQL":
        update_lookup_templates_cache()


async def connect_to_supabase():
    while True:
        URL = f"wss://{supabase_id}.supabase.co/realtime/v1/websocket?apikey={api_key}&vsn=1.0.0"
        s = Socket(URL)
        await s._connect()
        # channel_1 = s.set_channel("realtime:public:lookup_template")
        channel_1 = cast(Channel, s.set_channel("realtime:public:lookup_template"))

        await asyncio.create_task(channel_1._join())

        channel_1.on("*", callback1)
        listen_task = asyncio.create_task(s._listen())
        keep_alive_task = asyncio.create_task(s._keep_alive())

        await asyncio.wait([listen_task, keep_alive_task], return_when=asyncio.FIRST_COMPLETED)
        print("Connection closed unexpectedly. Reconnecting...")


def run_websocket_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(connect_to_supabase())
    loop.run_forever()

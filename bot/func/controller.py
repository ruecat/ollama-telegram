import json
import logging
import os
from asyncio import Lock

import aiohttp
from dotenv import load_dotenv

load_dotenv()
system_info = os.uname()
token = os.getenv("TOKEN")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
allowed_ids = list(map(int, os.getenv("USER_IDS", "").split(",")))
admin_ids = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
# Will be implemented soon
# content = []

log_level_str = os.getenv("LOG_LEVEL", "INFO")
log_levels = list(logging._levelToName.values())
# ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']

# Set default level to be INFO
if log_level_str not in log_levels:
    log_level = logging.DEBUG
else:
    log_level = logging.getLevelName(log_level_str)

logging.basicConfig(level=log_level)


async def model_list():
    async with aiohttp.ClientSession() as session:
        url = f"http://{ollama_base_url}:11434/api/tags"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data["models"]
            else:
                return []


async def generate(payload: dict, modelname: str, prompt: str):
    # try:
    async with aiohttp.ClientSession() as session:
        url = f"http://{ollama_base_url}:11434/api/chat"

        # Stream from API
        async with session.post(url, json=payload) as response:
            async for chunk in response.content:
                if chunk:
                    decoded_chunk = chunk.decode()
                    if decoded_chunk.strip():
                        yield json.loads(decoded_chunk)


# Telegram-related
def md_autofixer(text: str) -> str:
    # In MarkdownV2, these characters must be escaped: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r"_[]()~>#+-=|{}.!"
    # Use a backslash to escape special characters
    return "".join("\\" + char if char in escape_chars else char for char in text)


class contextLock:
    lock = Lock()

    async def __aenter__(self):
        await self.lock.acquire()

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        self.lock.release()

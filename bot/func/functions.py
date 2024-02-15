import logging
import os
import aiohttp
import json
from aiogram import types
from asyncio import Lock
from functools import wraps
from dotenv import load_dotenv

# --- Environment
load_dotenv()
# --- Environment Checker
token = os.getenv("TOKEN")
allowed_ids = list(map(int, os.getenv("USER_IDS", "").split(",")))
admin_ids = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
log_level_str = os.getenv("LOG_LEVEL", "INFO")

# --- Other
log_levels = list(logging._levelToName.values())
# ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']

# Set default level to be INFO
if log_level_str not in log_levels:
    log_level = logging.DEBUG
else:
    log_level = logging.getLevelName(log_level_str)

logging.basicConfig(level=log_level)


# Ollama API
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


# Aiogram functions & wraps
def perms_allowed(func):
    @wraps(func)
    async def wrapper(message: types.Message = None, query: types.CallbackQuery = None):
        user_id = message.from_user.id if message else query.from_user.id
        if user_id in admin_ids or user_id in allowed_ids:
            if message:
                return await func(message)
            elif query:
                return await func(query=query)
        else:
            if message:
                if message and message.chat.type in ["supergroup", "group"]:
                    return
                await message.answer("Access Denied")
            elif query:
                if message and message.chat.type in ["supergroup", "group"]:
                    return
                await query.answer("Access Denied")

    return wrapper


def perms_admins(func):
    @wraps(func)
    async def wrapper(message: types.Message = None, query: types.CallbackQuery = None):
        if message and message.chat and message.chat.type in ["supergroup", "group"]:
            pass
        user_id = message.from_user.id if message else query.from_user.id
        if user_id in admin_ids:
            if message:
                return await func(message)
            elif query:
                return await func(query=query)
        else:
            if message:
                if message and message.chat.type in ["supergroup", "group"]:
                    return
                await message.answer("Access Denied")
                logging.info(
                    f"[MSG] {message.from_user.first_name} {message.from_user.last_name}({message.from_user.id}) is not allowed to use this bot."
                )
            elif query:
                if message and message.chat.type in ["supergroup", "group"]:
                    return
                await query.answer("Access Denied")
                logging.info(
                    f"[QUERY] {message.from_user.first_name} {message.from_user.last_name}({message.from_user.id}) is not allowed to use this bot."
                )

    return wrapper


def md_autofixer(text: str) -> str:
    # In MarkdownV2, these characters must be escaped: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r"_[]()~>#+-=|{}.!"
    # Use a backslash to escape special characters
    return "".join("\\" + char if char in escape_chars else char for char in text)


# Context-Related
class contextLock:
    lock = Lock()

    async def __aenter__(self):
        await self.lock.acquire()

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        self.lock.release()

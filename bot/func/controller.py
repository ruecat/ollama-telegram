import aiohttp
import json
from dotenv import load_dotenv
import os

load_dotenv()
system_info = os.uname()
token = os.getenv("TOKEN")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
allowed_ids = list(map(int, os.getenv('USER_IDS', '').split(',')))
admin_ids = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))
# Will be implemented soon
# content = []


async def model_list():
    async with aiohttp.ClientSession() as session:
        url = f'http://{ollama_base_url}:11434/api/tags'
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data['models']
            else:
                return []


async def generate(prompt: str, modelname: str):
    # try:
    async with aiohttp.ClientSession() as session:
        url = f'http://{ollama_base_url}:11434/api/generate'
        # content.append(prompt)
        # print(f'Content updated: {content}')
        data = {
            "model": modelname,
            "prompt": prompt,
            "stream": True,
            # "context": content
        }
        print(f"DEBUG\n{modelname}\n{prompt}")
        # Stream from API
        async with session.post(url, json=data) as response:
            async for chunk in response.content:
                if chunk:
                    decoded_chunk = chunk.decode()
                    if decoded_chunk.strip():
                        yield json.loads(decoded_chunk)
# Telegram-related
def md_autofixer(text: str) -> str:
    # In MarkdownV2, these characters must be escaped: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'_[]()~>#+-=|{}.!'
    # Use a backslash to escape special characters
    return ''.join('\\' + char if char in escape_chars else char for char in text)


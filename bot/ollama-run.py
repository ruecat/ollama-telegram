import aiogram
import aiohttp
import asyncio
import json
import os
from dotenv import load_dotenv
load_dotenv()
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message
token = os.environ['TOKEN']
uid_get = os.environ['ADMIN_IDS'].split(",")
allowed_ids = [int(x) for x in uid_get]
idsu_env = os.environ['USER_IDS']
modelname = os.environ['INITMODEL']
if token == "yourtoken":
    print("Uh-Oh!\nPlease enter your Telegram bot TOKEN in .env file")
    exit("FATAL: NO_TOKEN_PROVIDED")
# --- --- --- --- --- --- --- ---
bot = Bot(token=token)
dp = Dispatcher()
builder = InlineKeyboardBuilder()
builder.row(types.InlineKeyboardButton(text="🤔️ Information", callback_data="info"),
            types.InlineKeyboardButton(text="⚙️ Change Model", callback_data="modelmanager"))
# Kernel swap options


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if message.from_user.id in allowed_ids:
        await message.answer(
            f"Hello, {message.from_user.full_name}\nChoose action",
            parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await message.answer(
            f"{message.from_user.full_name} - <code>[Auth-Blocked]</code>\nContact staff to whitelist you.",
            parse_mode="HTML")

@dp.callback_query(lambda query: query.data == 'modelmanager')
async def modelmanager_callback_handler(query: types.CallbackQuery):
    try:
        models = await fetch_models()

        # Create a new InlineKeyboardBuilder for the fetched models
        modelmanager_builder = InlineKeyboardBuilder()
        for model in models:
            modelname = model['name']
            # Add a button for each model
            modelmanager_builder.row(
                types.InlineKeyboardButton(text=modelname, callback_data=f"model_{modelname}")
            )

        # Send a new message with the new keyboard or edit the existing message
        await query.message.edit_text(
            "Choose model:",
            reply_markup=modelmanager_builder.as_markup()
        )
    except:
        await query.message.edit_text("<b>[Ollama-API ERROR]</b>\nNON_DOCKER: Make sure your Ollama API server is running ('ollama serve' command).\nDOCKER: Check Ollama container and try again", parse_mode="HTML")

@dp.callback_query(lambda query: query.data.startswith('model_'))
async def model_callback_handler(query: types.CallbackQuery):
    global modelname
    modelname = query.data.split('model_')[1]  # This will modify the modelname in the bot_state instance
    print(modelname)
    await query.answer(f"Chosen model: {modelname}")


@dp.callback_query(lambda query: query.data == 'info')
async def systeminfo_callback_handler(query: types.CallbackQuery):
    # Handle the callback query for button1 here
    await query.answer("Fetching info...")
    await bot.send_message(chat_id=query.message.chat.id,
                           text=f"<b>📦 About System</b>\n⚙️ Current model: <code>{modelname}</code>\n<i>(Other options will be added soon..)</i>",
                           parse_mode="HTML")

def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
async def fetch_models():
    async with aiohttp.ClientSession() as session:
        url = 'http://localhost:11434/api/tags'
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data['models']
            else:
                return []
async def stream_request(prompt: str):
    try:
        async with aiohttp.ClientSession() as session:
            global modelname
            # Default link to OllamaAPI
            url = 'http://localhost:11434/api/generate'
            # Ollama parameters
            data = {
                "model": modelname,
                "prompt": prompt,
                "stream": True
            }
            # Stream from API
            async with session.post(url, json=data) as response:  # Use json=data to send JSON
                async for chunk in response.content:
                    if chunk:
                        decoded_chunk = chunk.decode()
                        if decoded_chunk.strip():  # Avoid empty lines
                            yield json.loads(decoded_chunk)
    except:
        print("---------\n[Ollama-API ERROR]\nNON_DOCKER: Make sure your Ollama API server is running ('ollama serve' command)\nDOCKER: Check Ollama container and try again\n---------")


@dp.message()
async def handle_message(message: types.Message):
    botinfo = await bot.get_me()
    is_allowed_user = message.from_user.id in allowed_ids
    is_private_chat = message.chat.type == "private"
    is_supergroup = message.chat.type == "supergroup"
    bot_mentioned = any(
        entity.type == "mention" and message.text[entity.offset:entity.offset + entity.length] == f"@{botinfo.username}"
        for entity in message.entities or [])
    if is_allowed_user and message.text and (is_private_chat or (is_supergroup and bot_mentioned)):
        if is_supergroup and bot_mentioned:
            cutmention = len(botinfo.username) + 2
            text = message.text[cutmention:]  # + ""
            print(text)
        else:
            text = message.text
            print(text)
        await bot.send_chat_action(message.chat.id, "typing")
        full_response = ""
        sent_message = None
        last_sent_text = None
        async for response_data in stream_request(text):
            chunk = response_data.get("response", "")
            full_response += chunk
            if '.' in chunk or '\n' in chunk or '!' in chunk or '?' in chunk:
                if sent_message:
                    if last_sent_text != full_response:
                        try:
                            await sent_message.edit_text(full_response)
                            last_sent_text = full_response
                        except aiogram.exceptions.TelegramBadRequest as e:
                            if "message is not modified" in str(e):
                                pass
                            else:
                                raise
                else:
                    sent_message = await message.answer(full_response)
                    last_sent_text = full_response
            if response_data.get("done"):
                if full_response.strip() and last_sent_text != full_response:
                    if sent_message:
                        try:
                            await sent_message.edit_text(full_response)
                        except aiogram.exceptions.TelegramBadRequest as e:
                            if "message is not modified" in str(e):
                                pass
                            else:
                                raise
                    else:
                        sent_message = await message.answer(full_response)
                escaped_response = escape_html(full_response)
                await sent_message.edit_text(escaped_response + "<pre>Model: </pre>",
                                             parse_mode="HTML")
                break


async def main():
    await dp.start_polling(bot, skip_update=True)


if __name__ == "__main__":
    asyncio.run(main())

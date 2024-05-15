from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters.command import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from func.interactions import *
import asyncio
import traceback
import io
import base64
import telegramify_markdown
from telegramify_markdown.customize import markdown_symbol
markdown_symbol.head_level_1 = "📌"  # If you want, Customizing the head level 1 symbol
markdown_symbol.link = "🔗"  # If you want, Customizing the link symbol

bot = Bot(token=token)
dp = Dispatcher()
start_kb = InlineKeyboardBuilder()
settings_kb = InlineKeyboardBuilder()
start_kb.row(
    types.InlineKeyboardButton(text="ℹ️ About", callback_data="about"),
    types.InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
)
settings_kb.row(
    types.InlineKeyboardButton(text="🔄 Switch LLM", callback_data="switchllm"),
    types.InlineKeyboardButton(text="✏️ Edit system prompt", callback_data="editsystemprompt"),
)

commands = [
    types.BotCommand(command="start", description="Start"),
    types.BotCommand(command="reset", description="Reset Chat"),
    types.BotCommand(command="history", description="Look through messages"),
]
ACTIVE_CHATS = {}
ACTIVE_CHATS_LOCK = contextLock()
modelname = os.getenv("INITMODEL")
mention = None
CHAT_TYPE_GROUP = "group"
CHAT_TYPE_SUPERGROUP = "supergroup"

def escape_markdown_v2(text):
    # List of Markdown v2 special characters that need escaping
    escape_chars = "_*[]()~`>#+-=|{}.!"
    # Escaping each special character with a backslash
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

def is_mentioned_in_group_or_supergroup(message):
    return message.chat.type in [CHAT_TYPE_GROUP, CHAT_TYPE_SUPERGROUP] and (
        (message.text is not None and message.text.startswith(mention))
        or (message.caption is not None and message.caption.startswith(mention))
    )
async def get_bot_info():
    global mention
    if mention is None:
        get = await bot.get_me()
        mention = f"@{get.username}"
    return mention
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    start_message = f"Welcome, <b>{message.from_user.full_name}</b>!"
    await message.answer(
        start_message,
        parse_mode=ParseMode.HTML,
        reply_markup=start_kb.as_markup(),
        disable_web_page_preview=True,
    )
@dp.message(Command("reset"))
async def command_reset_handler(message: Message) -> None:
    if message.from_user.id in allowed_ids:
        if message.from_user.id in ACTIVE_CHATS:
            async with ACTIVE_CHATS_LOCK:
                ACTIVE_CHATS.pop(message.from_user.id)
            logging.info(f"Chat has been reset for {message.from_user.first_name}")
            await bot.send_message(
                chat_id=message.chat.id,
                text="Chat has been reset",
            )
@dp.message(Command("history"))
async def command_get_context_handler(message: Message) -> None:
    if message.from_user.id in allowed_ids:
        if message.from_user.id in ACTIVE_CHATS:
            messages = ACTIVE_CHATS.get(message.chat.id)["messages"]
            context = ""
            for msg in messages:
                context += f"*{msg['role'].capitalize()}*: {msg['content']}\n"
            await bot.send_message(
                chat_id=message.chat.id,
                text=context,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text="No chat history available for this user",
            )
@dp.callback_query(lambda query: query.data == "settings")
async def settings_callback_handler(query: types.CallbackQuery):
    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"Choose the right option.",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=settings_kb.as_markup()
    )

@dp.callback_query(lambda query: query.data == "switchllm")
async def switchllm_callback_handler(query: types.CallbackQuery):
    models = await model_list()
    switchllm_builder = InlineKeyboardBuilder()
    for model in models:
        modelname = model["name"]
        modelfamilies = ""
        if model["details"]["families"]:
            modelicon = {"llama": "🦙", "clip": "📷"}
            try:
                modelfamilies = "".join(
                    [modelicon[family] for family in model["details"]["families"]]
                )
            except KeyError as e:
                modelfamilies = f"✨"
        switchllm_builder.row(
            types.InlineKeyboardButton(
                text=f"{modelname} {modelfamilies}", callback_data=f"model_{modelname}"
            )
        )
    await query.message.edit_text(
        f"{len(models)} models available.\n🦙 = Regular\n🦙📷 = Multimodal", reply_markup=switchllm_builder.as_markup(),
    )


@dp.callback_query(lambda query: query.data.startswith("model_"))
async def model_callback_handler(query: types.CallbackQuery):
    global modelname
    global modelfamily
    modelname = query.data.split("model_")[1]
    await query.answer(f"Chosen model: {modelname}")


@dp.callback_query(lambda query: query.data == "about")
@perms_admins
async def about_callback_handler(query: types.CallbackQuery):
    dotenv_model = os.getenv("INITMODEL")
    global modelname
    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"<b>Your LLMs</b>\nCurrently using: <code>{modelname}</code>\nDefault in .env: <code>{dotenv_model}</code>\nThis project is under <a href='https://github.com/ruecat/ollama-telegram/blob/main/LICENSE'>MIT License.</a>\n<a href='https://github.com/ruecat/ollama-telegram'>Source Code</a>",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
@dp.message()
@perms_allowed
async def handle_message(message: types.Message):
    await get_bot_info()
    if message.chat.type == "private":
        await ollama_request(message)
    if is_mentioned_in_group_or_supergroup(message):
        if message.text is not None:
            text_without_mention = message.text.replace(mention, "").strip()
            prompt = text_without_mention
        else:
            text_without_mention = message.caption.replace(mention, "").strip()
            prompt = text_without_mention
        await ollama_request(message, prompt)


async def process_image(message):
    image_base64 = ""
    if message.content_type == "photo":
        image_buffer = io.BytesIO()
        await bot.download(message.photo[-1], destination=image_buffer)
        image_base64 = base64.b64encode(image_buffer.getvalue()).decode("utf-8")
    return image_base64

async def add_prompt_to_active_chats(message, prompt, image_base64, modelname):
    async with ACTIVE_CHATS_LOCK:
        if ACTIVE_CHATS.get(message.from_user.id) is None:
            ACTIVE_CHATS[message.from_user.id] = {
                "model": modelname,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": ([image_base64] if image_base64 else []),
                    }
                ],
                "stream": True,
            }
        else:
            ACTIVE_CHATS[message.from_user.id]["messages"].append(
                {
                    "role": "user",
                    "content": prompt,
                    "images": ([image_base64] if image_base64 else []),
                }
            )

async def begin_response(message, init_response):
    await bot.send_chat_action(message.chat.id, "typing")
    init_response = init_response.strip()
    if init_response == "":
        return
    text = telegramify_markdown.convert(init_response)
    return await send_response(message, text)

async def edit_response(message, follow_response):
    follow_response = follow_response.strip()
    if follow_response == "":
        return
    text = telegramify_markdown.convert(follow_response)
    await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    return True

async def handle_response(message, response_data, full_response):
    full_response_stripped = full_response.strip()
    if full_response_stripped == "":
        return
    if not response_data.get("done"):
        await bot.send_chat_action(message.chat.id, "typing")
        text = telegramify_markdown.convert(full_response_stripped)
        await send_response(message, text)
        return False
    else:
        text = f"{full_response_stripped}\n\n⚙️ {modelname}\nGenerated in {response_data.get('total_duration') / 1e9:.2f}s."
        text = telegramify_markdown.convert(text)
        await send_response(message, text)
        async with ACTIVE_CHATS_LOCK:
            if ACTIVE_CHATS.get(message.from_user.id) is not None:
                ACTIVE_CHATS[message.from_user.id]["messages"].append(
                    {"role": "assistant", "content": full_response_stripped}
                )
        logging.info(
            f"[Response]: '{full_response_stripped}' for {message.from_user.first_name} {message.from_user.last_name}"
        )
        return True
    return False


async def send_response(message, text):
    bot_message = None
    if message.chat.id == message.from_user.id:
        bot_message = await bot.send_message(
            chat_id=message.chat.id, 
            text=text, 
            parse_mode=ParseMode.MARKDOWN_V2)
    else:
        bot_message = await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    return bot_message


async def ollama_request(message: types.Message, prompt: str = None):
    try:
        full_response = ""
        initial_response = True
        chunk = ""
        await bot.send_chat_action(message.chat.id, "typing")
        image_base64 = await process_image(message)
        if prompt is None:
            prompt = message.text or message.caption

        await add_prompt_to_active_chats(message, prompt, image_base64, modelname)
        logging.info(
            f"[OllamaAPI]: Processing '{prompt}' for {message.from_user.first_name} {message.from_user.last_name}"
        )
        payload = ACTIVE_CHATS.get(message.from_user.id)
        async for response_data in generate(payload, modelname, prompt):
            msg = response_data.get("message")
            if msg is None:
                continue
            token = msg.get("content", "")
            chunk += token
            # print('token: ', token.encode())

            if any([c in token for c in ".\n!?"]) or response_data.get("done"):
                full_response += chunk
                print('chunk: ', chunk)
                chunk = ""
                if initial_response and not response_data.get("done"):
                    initial_response = False
                    message = await begin_response(message, full_response)
                elif await handle_response(message, response_data, full_response):
                    print('message is done!')
                    break

    except Exception as e:
        print(f"-----\n[OllamaAPI-ERR] CAUGHT FAULT!\n{traceback.format_exc()}\n-----")
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"Something went wrong.",
            parse_mode=ParseMode.HTML,
        )


async def main():
    await bot.set_my_commands(commands)
    await dp.start_polling(bot, skip_update=True)


if __name__ == "__main__":
    asyncio.run(main())

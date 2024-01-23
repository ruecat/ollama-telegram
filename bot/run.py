from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters.command import Command, CommandStart
from aiogram.types import Message
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from func.functions import *
# Other
import asyncio
import traceback
import io
import base64

bot = Bot(token=token)
dp = Dispatcher()
builder = InlineKeyboardBuilder()
builder.row(
    types.InlineKeyboardButton(text="🤔️ Information", callback_data="info"),
    types.InlineKeyboardButton(text="⚙️ Settings", callback_data="modelmanager"),
)

commands = [
    types.BotCommand(command="start", description="Start"),
    types.BotCommand(command="reset", description="Reset Chat"),
    types.BotCommand(command="history", description="Look through messages"),
]

# Context variables for OllamaAPI
ACTIVE_CHATS = {}
ACTIVE_CHATS_LOCK = contextLock()
modelname = os.getenv("INITMODEL")
mention = None


async def get_bot_info():
    global mention
    if mention is None:
        get = await bot.get_me()
        mention = (f"@{get.username}")
    return mention


# /start command
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    start_message = f"Welcome to OllamaTelegram Bot, ***{message.from_user.full_name}***!\nSource code: https://github.com/ruecat/ollama-telegram"
    start_message_md = md_autofixer(start_message)
    await message.answer(
        start_message_md,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=builder.as_markup(),
        disable_web_page_preview=True,
    )


# /reset command, wipes context (history)
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


# /history command | Displays dialogs between LLM and USER
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
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text="No chat history available for this user",
            )


@dp.callback_query(lambda query: query.data == "modelmanager")
async def modelmanager_callback_handler(query: types.CallbackQuery):
    models = await model_list()
    modelmanager_builder = InlineKeyboardBuilder()
    for model in models:
        modelname = model["name"]
        modelfamilies = ""
        if model["details"]["families"]:
            modelicon = {"llama": "🦙", "clip": "📷"}
            modelfamilies = "".join([modelicon[family] for family in model['details']['families']])
        # Add a button for each model
        modelmanager_builder.row(
            types.InlineKeyboardButton(
                text=f"{modelname} {modelfamilies}", callback_data=f"model_{modelname}"
            )
        )
    await query.message.edit_text(
        f"Choose model:", reply_markup=modelmanager_builder.as_markup()
    )


@dp.callback_query(lambda query: query.data.startswith("model_"))
async def model_callback_handler(query: types.CallbackQuery):
    global modelname
    global modelfamily
    modelname = query.data.split("model_")[1]
    await query.answer(f"Chosen model: {modelname}")


@dp.callback_query(lambda query: query.data == "info")
@perms_admins
async def systeminfo_callback_handler(query: types.CallbackQuery):
    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"<b>📦 LLM</b>\n<code>Model: {modelname}</code>\n\n",
        parse_mode="HTML",
    )


# React on message | LLM will respond on user's message or mention in groups
@dp.message()
@perms_allowed
async def handle_message(message: types.Message):
    await get_bot_info()
    if message.chat.type == "private":
        await ollama_request(message)
    if message.chat.type == "supergroup" and message.text.startswith(mention):
        # Remove the mention from the message
        text_without_mention = message.text.replace(mention, "").strip()
        # Pass the modified text and bot instance to ollama_request
        await ollama_request(types.Message(
            message_id=message.message_id,
            from_user=message.from_user,
            date=message.date,
            chat=message.chat,
            text=text_without_mention
        ))


...
async def ollama_request(message: types.Message):
    try:
        await bot.send_chat_action(message.chat.id, "typing")
        prompt = message.text or message.caption
        image_base64 = ''
        if message.content_type == 'photo':
            image_buffer = io.BytesIO()
            await bot.download(
                message.photo[-1],
                destination=image_buffer
            )
            image_base64 = base64.b64encode(image_buffer.getvalue()).decode('utf-8')
        full_response = ""
        sent_message = None
        last_sent_text = None

        async with ACTIVE_CHATS_LOCK:
            # Add prompt to active chats object
            if ACTIVE_CHATS.get(message.from_user.id) is None:
                ACTIVE_CHATS[message.from_user.id] = {
                    "model": modelname,
                    "messages": [{"role": "user", "content": prompt, "images": [image_base64]}],
                    "stream": True,
                }
            else:
                ACTIVE_CHATS[message.from_user.id]["messages"].append(
                    {"role": "user", "content": prompt, "images": [image_base64]}
                )
        logging.info(
            f"[Request]: Processing '{prompt}' for {message.from_user.first_name} {message.from_user.last_name}"
        )
        payload = ACTIVE_CHATS.get(message.from_user.id)
        async for response_data in generate(payload, modelname, prompt):
            msg = response_data.get("message")
            if msg is None:
                continue
            chunk = msg.get("content", "")
            full_response += chunk
            full_response_stripped = full_response.strip()

            # avoid Bad Request: message text is empty
            if full_response_stripped == "":
                continue

            if "." in chunk or "\n" in chunk or "!" in chunk or "?" in chunk:
                if sent_message:
                    if last_sent_text != full_response_stripped:
                        await bot.edit_message_text(chat_id=message.chat.id, message_id=sent_message.message_id,
                                                    text=full_response_stripped)
                        last_sent_text = full_response_stripped
                else:
                    sent_message = await bot.send_message(
                        chat_id=message.chat.id,
                        text=full_response_stripped,
                        reply_to_message_id=message.message_id,
                    )
                    last_sent_text = full_response_stripped

            if response_data.get("done"):
                if (
                        full_response_stripped
                        and last_sent_text != full_response_stripped
                ):
                    if sent_message:
                        await bot.edit_message_text(chat_id=message.chat.id, message_id=sent_message.message_id,
                                                    text=full_response_stripped)
                    else:
                        sent_message = await bot.send_message(chat_id=message.chat.id,
                                                                text=full_response_stripped)
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=sent_message.message_id,
                    text=md_autofixer(
                        full_response_stripped
                        + f"\n\nCurrent Model: `{modelname}`**\n**Generated in {response_data.get('total_duration') / 1e9:.2f}s"
                    ),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )

                async with ACTIVE_CHATS_LOCK:
                    if ACTIVE_CHATS.get(message.from_user.id) is not None:
                        # Add response to active chats object
                        ACTIVE_CHATS[message.from_user.id]["messages"].append(
                            {"role": "assistant", "content": full_response_stripped}
                        )
                        logging.info(
                            f"[Response]: '{full_response_stripped}' for {message.from_user.first_name} {message.from_user.last_name}"
                        )
                    else:
                        await bot.send_message(
                            chat_id=message.chat.id, text="Chat was reset"
                        )

                break
    except Exception as e:
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"""Error occurred\n```\n{traceback.format_exc()}\n```""",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def main():
    await bot.set_my_commands(commands)
    await dp.start_polling(bot, skip_update=True)


if __name__ == "__main__":
    asyncio.run(main())

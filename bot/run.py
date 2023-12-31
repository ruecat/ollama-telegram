import asyncio
import traceback

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters.command import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from func.controller import *

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
    types.BotCommand(command="getcontext", description="Get chat context json"),
]


ACTIVE_CHATS = {}
ACTIVE_CHATS_LOCK = contextLock()

modelname = os.getenv("INITMODEL")


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if message.from_user.id in allowed_ids:
        start_message = f"Welcome to OllamaTelegram Bot, ***{message.from_user.full_name}***!\nSource code: https://github.com/ruecat/ollama-telegram"
        start_message_md = md_autofixer(start_message)
        await message.answer(
            start_message_md,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True,
        )
    else:
        await message.answer(
            f"{message.from_user.full_name} [AuthBlocked]\nContact staff to whitelist you",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        logging.info(
            f"[Interactions] {message.from_user.first_name} {message.from_user.last_name}({message.from_user.id}) is not allowed to use this bot. Value in environment: {allowed_ids}"
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


@dp.message(Command("getcontext"))
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
    if query.from_user.id in admin_ids:
        models = await model_list()
        modelmanager_builder = InlineKeyboardBuilder()
        for model in models:
            modelname = model["name"]
            # Add a button for each model
            modelmanager_builder.row(
                types.InlineKeyboardButton(
                    text=modelname, callback_data=f"model_{modelname}"
                )
            )
        await query.message.edit_text(
            f"Choose model:", reply_markup=modelmanager_builder.as_markup()
        )
    else:
        await query.answer("Access Denied")


@dp.callback_query(lambda query: query.data.startswith("model_"))
async def model_callback_handler(query: types.CallbackQuery):
    global modelname
    modelname = query.data.split("model_")[1]
    await query.answer(f"Chosen model: {modelname}")


@dp.callback_query(lambda query: query.data == "info")
async def systeminfo_callback_handler(query: types.CallbackQuery):
    if query.from_user.id in admin_ids:
        await bot.send_message(
            chat_id=query.message.chat.id,
            text=f"<b>📦 LLM</b>\n<code>Current model: {modelname}</code>\n\n🔧 Hardware\n<code>Kernel: {system_info[0]}\n</code>\n<i>(Other options will be added soon..)</i>",
            parse_mode="HTML",
        )
    else:
        await query.answer("Access Denied")


@dp.message()
async def handle_message(message: types.Message):
    try:
        botinfo = await bot.get_me()
        is_allowed_user = message.from_user.id in allowed_ids
        is_private_chat = message.chat.type == "private"
        is_supergroup = message.chat.type == "supergroup"
        bot_mentioned = any(
            entity.type == "mention"
            and message.text[entity.offset : entity.offset + entity.length]
            == f"@{botinfo.username}"
            for entity in message.entities or []
        )
        if (
            is_allowed_user
            and message.text
            and (is_private_chat or (is_supergroup and bot_mentioned))
        ):
            if is_supergroup and bot_mentioned:
                cutmention = len(botinfo.username) + 2
                prompt = message.text[cutmention:]  # + ""
            else:
                prompt = message.text
            await bot.send_chat_action(message.chat.id, "typing")
            full_response = ""
            sent_message = None
            last_sent_text = None

            async with ACTIVE_CHATS_LOCK:
                # Add prompt to active chats object
                if ACTIVE_CHATS.get(message.from_user.id) is None:
                    ACTIVE_CHATS[message.from_user.id] = {
                        "model": modelname,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True,
                    }
                else:
                    ACTIVE_CHATS[message.from_user.id]["messages"].append(
                        {"role": "user", "content": prompt}
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
                            await sent_message.edit_text(full_response_stripped)
                            last_sent_text = full_response_stripped
                    else:
                        sent_message = await message.answer(
                            full_response_stripped,
                            reply_to_message_id=message.message_id,
                        )
                        last_sent_text = full_response_stripped

                if response_data.get("done"):
                    if (
                        full_response_stripped
                        and last_sent_text != full_response_stripped
                    ):
                        if sent_message:
                            await sent_message.edit_text(full_response_stripped)
                        else:
                            sent_message = await message.answer(full_response_stripped)
                    await sent_message.edit_text(
                        md_autofixer(
                            full_response_stripped
                            + f"\n\nCurrent Model: `{modelname}`**\n**Generated in {response_data.get('total_duration')/10e9:.2f}s"
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
            text=f"""Error occured\n```\n{traceback.format_exc()}\n```""",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def main():
    await bot.set_my_commands(commands)

    await dp.start_polling(bot, skip_update=True)


if __name__ == "__main__":
    asyncio.run(main())

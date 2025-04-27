import random, string, os, asyncio

from asyncio import sleep
from pymongo.errors import PyMongoError

from pyrogram import enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto,InputMediaAnimation
from pyrogram.types import CallbackQuery
from pyrogram.errors import ChannelInvalid
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.filters import regex, command, reply

from bot import config_dict, bot, LOGGER, bot_name, validate_and_format_url
from bot.database.db_utils import get_file_details, get_size
from bot.helper.extra.bot_utils import new_task, delete_file_after_delay, checking_access, format_time, format_duration
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.database.db_file_handler import Media
from bot.database.db_handler import DbManager
from bot.helper.extra.help_string import STATUS_TXT, WEB_PAGE_MANUAL, AUTO_FILTER_MANUAL, INDEX_FILE_MANUAL, USER_SETTING_MANUAL, BOT_SETTING_MANUAL, USER_CMD, ADMIN_CMD
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendFile, send_message, send_log_message, forcesub, convert_seconds_to_minutes, get_status, delete_message, edit_message, send_message
from bot.helper.extra.media_info import extract_media_info, MAX_FILE_SIZE, download_first_10mb
from bot.helper.extra.telegraph_helper import telegraph

db = DbManager()


async def authorize_user_start_cmd(client, message):
    user = await db.find_pm_users(message.from_user.id)
    new_user = None
    button_maker = ButtonMaker()
    if len(message.command) > 1 and (message.command[1].startswith("file") or message.command[1].startswith("resendfile")):
        #if not user:
        #    s = await message.reply_sticker("CAACAgIAAxkBAAENgiRniM8Eh4p_1AqqfqJTp14DqNThdAACVQADQbVWDHgpYBWAAc-pNgQ")
        #    await sleep(1)
        #    await delete_message(s)
        #    text = "🚫 ɪᴛ ꜱᴇᴇᴍꜱ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇꜱꜱ ᴛᴏ ᴜꜱᴇ ᴍᴇ. ᴛᴏ ɢᴀɪɴ ᴀᴄᴄᴇꜱꜱ, ᴘʟᴇᴀꜱᴇ ʀᴇɢɪꜱᴛᴇʀ ʏᴏᴜʀꜱᴇʟꜰ ɪɴ ᴏᴜʀ ᴅᴀᴛᴀʙᴀꜱᴇ ʙʏ ꜱᴇɴᴅɪɴɢ ᴛʜᴇ /ꜱᴛᴀʀᴛ ᴄᴏᴍᴍᴀɴᴅ ᴏʀ ʙʏ ᴄʟɪᴄᴋɪɴɢ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ. ᴛʜᴀɴᴋ ʏᴏᴜ! 🙌"
        #    button_maker.add_button(f"Start {bot.me.first_name}", callback_data=f"iron {message.from_user.id} private")
        #    button = button_maker.build()
        #    return await send_message(message, text=text, buttons=button)
        iron_cmd = message.command[1]
        pre, file_id = iron_cmd.split("_", 1)
        await start_file_sender(client, message, pre, file_id)
    else:
        # Create buttons using InlineKeyboardButton
        if not user:
            m = await message.reply_sticker("CAACAgUAAxkBAAENS1xnVboNBPNdI3Dz6LFvQjWji6I3aAACAhIAAtnisFZ0ElP0nL43izYE")
        else:
            m = await message.reply_sticker("CAACAgIAAxkBAAENS11nVboN1pDp3u_nYcv9mLQmaV5cwQAC8DUAAlXR-EikRveMrnUwszYE")
        await sleep(2)
        await delete_message(m)

        msg, ibuttons = await get_start_msg_buttons()
        
        # Send the photo with the caption and the keyboard
        await send_message(message, msg.format(message.from_user.first_name, message.from_user.last_name), ibuttons, config_dict['START_PICS'])
    if not user:
        new_user = await db.update_pm_users(message.from_user.id)
        if new_user != None and new_user != False:
            await send_log_message(message, True)


async def normal_user_start_cmd(client, message):
    user = await db.find_pm_users(message.from_user.id)
    new_user = None
    button_maker = ButtonMaker()
    if len(message.command) > 1 and (message.command[1].startswith("file") or message.command[1].startswith("resendfile")):
        #useless
        #if not user:
        #    s = await message.reply_sticker("CAACAgIAAxkBAAENgiRniM8Eh4p_1AqqfqJTp14DqNThdAACVQADQbVWDHgpYBWAAc-pNgQ")
        #    await sleep(1)
        #    await delete_message(s)
        #    text = "🚫 ɪᴛ ꜱᴇᴇᴍꜱ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇꜱꜱ ᴛᴏ ᴜꜱᴇ ᴍᴇ. ᴛᴏ ɢᴀɪɴ ᴀᴄᴄᴇꜱꜱ, ᴘʟᴇᴀꜱᴇ ʀᴇɢɪꜱᴛᴇʀ ʏᴏᴜʀꜱᴇʟꜰ ɪɴ ᴏᴜʀ ᴅᴀᴛᴀʙᴀꜱᴇ ʙʏ ꜱᴇɴᴅɪɴɢ ᴛʜᴇ /ꜱᴛᴀʀᴛ ᴄᴏᴍᴍᴀɴᴅ ᴏʀ ʙʏ ᴄʟɪᴄᴋɪɴɢ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ. ᴛʜᴀɴᴋ ʏᴏᴜ! 🙌"
        #    button_maker.add_button(f"Start {bot.me.first_name}", callback_data=f"iron {message.from_user.id} private")
        #    button = button_maker.build()
        #    return await send_message(message, text=text, buttons=button)
        msg, button = await checking_access(message.from_user.id, button_maker)
        if msg is not None:
            return await send_message(message, msg, buttons=button)
        iron_cmd = message.command[1]
        pre, file_id = iron_cmd.split("_", 1)
        await start_file_sender(client, message, pre, file_id)
    else:
        #get commands for verify
        if not user:
            m = await message.reply_sticker("CAACAgUAAxkBAAENS1xnVboNBPNdI3Dz6LFvQjWji6I3aAACAhIAAtnisFZ0ElP0nL43izYE")
        else:
            m = await message.reply_sticker("CAACAgIAAxkBAAENNihnRCglpIFQNj9-e-xbgqpjNvFznAAC9hIAAin9SElmvNqzuDEHKjYE")
        await sleep(2)
        await delete_message(m)

        msg, ibuttons = await get_start_msg_buttons()
        # Send the photo with the caption and the keyboard
        await send_message(message, msg.format(message.from_user.first_name, message.from_user.last_name), ibuttons, config_dict['START_PICS'])
    if not user:
        new_user = await db.update_pm_users(message.from_user.id)
        if new_user != None:
            await send_log_message(message, True)

@new_task
async def start_file_sender(client, message, pre, file_id):
    button_maker = ButtonMaker()
    # Get the file ID from the command arguments and send file to user
    #pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
    files_ = await get_file_details(file_id)
    # Check if the file details were found
    if not files_:
        await message.reply(
            "Sorry, I couldn't find the requested file because file have some data problem."
            "I reported to owner to fix this issue."
            "Please kindly consider other file."
        )
        return
    files = files_[0]
    title = files.file_name
    size=get_size(files.file_size)
    f_caption=files.caption
    if config_dict['CUSTOM_FILE_CAPTION']:
        try:
            f_caption=config_dict['CUSTOM_FILE_CAPTION'].format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except Exception as e:
            LOGGER.exception(e)
            f_caption=f_caption
    if f_caption is None:
        f_caption = f"{files.file_name}"
    
    if ids := config_dict['FSUB_IDS']:
        mode = config_dict['REQ_JOIN_FSUB']
        msg, button = await forcesub(message=message, pre=pre, file_id=file_id, ids=ids, request_join=mode)
        if msg:
            await message.reply(msg, reply_markup=button.build())
            return
    if len(config_dict['UPDT_BTN_URL']) != 0:
        button_maker.add_button(text="📰 ᴜᴘᴅᴀᴛᴇꜱ 📰", url=config_dict['UPDT_BTN_URL'])
    iron_button = button_maker.build()
    msg = await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=config_dict['FILE_SECURE_MODE'],
        reply_markup=iron_button if iron_button.inline_keyboard else None
    )
    if config_dict['AUTO_FILE_DELETE_MODE'] == True and not config_dict['FILE_SECURE_MODE']:
        btn = [[
            InlineKeyboardButton("❗ ɢᴇᴛ ꜰɪʟᴇ ᴀɢᴀɪɴ ❗", callback_data=f'resendfile#{file_id}#{pre}')
        ]]
        if config_dict['AUTO_FILE_DELETE_MODE_TIMEOUT'] > 60:
            MINUTE = await convert_seconds_to_minutes(config_dict['AUTO_FILE_DELETE_MODE_TIMEOUT'])
            k = await send_message(msg, text=f"<b>❗️ <u>ɪᴍᴘᴏʀᴛᴀɴᴛ</u> ❗️</b>\n\n<b>ᴛʜɪꜱ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ</b> <b><u>{MINUTE} ᴍɪɴᴜᴛᴇꜱ</u> </b><b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪꜱꜱᴜᴇꜱ).</b>\n\n<b><i>📌 ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴛᴏ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ.</i></b>", buttons = None)
        else:
            k = await send_message(msg, text=f"<b>❗️ <u>ɪᴍᴘᴏʀᴛᴀɴᴛ</u> ❗️</b>\n\n<b>ᴛʜɪꜱ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ</b> <b><u>{config_dict['AUTO_FILE_DELETE_MODE_TIMEOUT']} ꜱᴇᴄᴏɴᴅꜱ</u> </b><b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪꜱꜱᴜᴇꜱ).</b>\n\n<b><i>📌 ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴛᴏ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ.</i></b>", buttons = None)
        await sleep(config_dict['AUTO_FILE_DELETE_MODE_TIMEOUT'])
        await delete_message(msg)
        if pre == 'resendfile':
            await edit_message(k, text=f"<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nᴏᴏᴘꜱ! ʏᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ᴜꜱᴇᴅ ❗ ɢᴇᴛ ꜰɪʟᴇ ᴀɢᴀɪɴ ❗ ʙᴜᴛᴛᴏɴ. ɴᴏᴡ ʏᴏᴜ ᴅᴏ ɴᴏᴛ ᴀʙʟᴇ ᴛᴏ ᴜꜱᴇ ❗ ɢᴇᴛ ꜰɪʟᴇ ᴀɢᴀɪɴ ❗ ʙᴜᴛᴛᴏɴ.\n\nᴘʟᴇᴀꜱᴇ ᴋɪɴᴅʟʏ ʀᴇQᴜᴇꜱᴛ ɴᴇᴡ ꜰᴏʀ ɢᴇᴛ ʏᴏᴜʀ ꜰɪʟᴇ.</b>",buttons=None)
            await sleep(15)
            await delete_message(k)
        elif pre == 'file':
            if len(config_dict['TOKEN_TIMEOUT']) == 0 or config_dict['TOKEN_TIMEOUT'] is None or config_dict['TOKEN_TIMEOUT'] in ['0', 0]:
                return await delete_message(k)
            await edit_message(k, text=f"<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nꜰɪʟᴇɴᴀᴍᴇ: {f_caption}\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇</b>", buttons=InlineKeyboardMarkup(btn))
  
@new_task
async def get_ststs(bot, message):
    rju = await message.reply('Fetching stats..')

    total_files = await Media.count_documents()
    file_db_size = await db.get_db_size(file_db=True)
    file_db_free = 536870912 - file_db_size
    file_db_size = get_size(file_db_size)
    file_db_free = get_size(file_db_free)

    total_users = await db.total_users_count()
    #totl_chats = await db.total_chat_count()
    other_db_size = await db.get_db_size()
    free = 536870912 - other_db_size
    other_db_size = get_size(other_db_size)
    other_db_free = get_size(free)
    await edit_message(rju, STATUS_TXT.format(
        total_files=total_files, 
        file_db_size=file_db_size, 
        file_db_free=file_db_free, 
        total_users=total_users, 
        other_db_size=other_db_size, 
        other_db_free=other_db_free
        )
    )
    
async def get_sticker_id(client, message):
    # Check if the message is a reply and if the replied message contains a sticker
    if message.reply_to_message and message.reply_to_message.sticker:
        sticker_id = message.reply_to_message.sticker.file_id
        await send_message(message, f"The sticker ID is:\n<code>{sticker_id}</code>")
    else:
        await send_message(message, "Please reply to a sticker with the command /getstickerid to get its ID.")
    return

async def get_id(client, message):
    # Check if there is text after the command
    if len(message.command) > 1:
        return await send_message(
            message,
            "Please do not add any text after the command. Only reply to a forwarded message.",
        )

    # Case 1: Command in private chat
    if message.chat.type == enums.ChatType.PRIVATE:
        if not message.reply_to_message:
            # No reply to any message, reply with the user's ID
            await send_message(message, f"Your user ID: <code>{message.from_user.id}</code>")
            return
        
        elif message.reply_to_message and message.reply_to_message.forward_from:
            return await send_message(message, f"Your user ID: <code>{message.from_user.id}</code>\nYour Forward User ID: <code>{message.reply_to_message.forward_from.id}</code>")
        elif message.reply_to_message and message.reply_to_message.forward_from_chat and message.reply_to_message.forward_from_chat.type == enums.ChatType.CHANNEL:
            return await send_message(message, f"Your user ID: <code>{message.from_user.id}</code>\nYour Forwared Channel ID: <code>{message.reply_to_message.forward_from_chat.id}</code>")
        else:
            return await send_message(message, f"Your user ID: <code>{message.from_user.id}</code>")
    elif message.chat.type == enums.ChatType.SUPERGROUP:
        if not message.reply_to_message:
            # No reply to any message, reply with the user's ID
            await send_message(message, f"Your user ID: <code>{message.from_user.id}</code>\nYour Chat ID: <code>{message.chat.id}</code>")
            return
        elif message.reply_to_message and (not message.reply_to_message.forward_from_chat or message.reply_to_message.forward_from) and message.from_user.id != message.reply_to_message.from_user.id:
            return await send_message(message, f"Your user ID: <code>{message.from_user.id}</code>\nYour Replied User ID: <code>{message.reply_to_message.from_user.id}</code>")
        elif message.reply_to_message and message.reply_to_message.forward_from_chat and message.reply_to_message.forward_from_chat.type == enums.ChatType.CHANNEL:
            return await send_message(message, f"Your user ID: <code>{message.from_user.id}</code>\nYour Forwared Channel ID: <code>{message.reply_to_message.forward_from_chat.id}</code>")
        elif message.reply_to_message and message.reply_to_message.forward_from:
            return await send_message(message, f"Your user ID: <code>{message.from_user.id}</code>\nYour Forwared User ID: <code>{message.reply_to_message.forward_from.id}</code>")
        else:
            return await send_message(message, f"Your user ID: <code>{message.from_user.id}\nYour Chat ID: <code>{message.chat.id}</code>")
        
async def check_bot_rights(client, message):
    print(f"message: {message}")
    msg = message.text.split()
    if len(msg) < 2:
        return await send_message(message, text="Please add chat_id and user_id after the command Example: /checkrights <chat_id> <user_id>")
    
    if len(msg) == 2:
        chat_id = int(msg[1])
        user_id = None
    if len(msg) == 3:
        chat_id = int(msg[1])
        user_id = int(msg[2])
    try:
        if user_id == None and str(chat_id).startswith("-100"):
            chat = await bot.get_chat(chat_id)
            users_permissions = chat.permissions
            if users_permissions:
                UP_MSG = (
                    f"can_send_messages: {users_permissions.can_send_messages}\n"
                    f"can_send_media_messages : {users_permissions.can_send_media_messages}\n"
                    f"can_send_other_messages: {users_permissions.can_send_other_messages}\n"
                    f"can_send_polls: {users_permissions.can_send_polls}\n"
                    f"can_add_web_page_previews: {users_permissions.can_add_web_page_previews}\n"
                    f"can_change_info: {users_permissions.can_change_info}\n"
                    f"can_invite_users: {users_permissions.can_invite_users}\n"
                    f"can_pin_messages: {users_permissions.can_pin_messages}"
                )
            await send_message(message, text=UP_MSG)
        else:
            if str(user_id).startswith('-100'):
                return await send_message(message, text="Please always add chat_id first and after user_id\nExample: /checkrights <chat_id> <user_id>")
            elif not str(chat_id).startswith('-100'):
                return await send_message(message, text="chat_id wrong: make sure you add correct chat_id")
            user_chat = await bot.get_chat_member(chat_id, user_id)

            if user_chat.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                ADMNP = user_chat.privileges
                if ADMNP:
                    ADMIN_RIGHTS = (
                        f"can_manage_chat: {ADMNP.can_manage_chat}\n"
                        f"can_delete_messages: {ADMNP.can_delete_messages}\n"
                        f"can_manage_video_chats: {ADMNP.can_manage_video_chats}\n"
                        f"can_restrict_members: {ADMNP.can_restrict_members}\n"
                        f"can_promote_members: {ADMNP.can_promote_members}\n"
                        f"can_change_info: {ADMNP.can_change_info}\n"
                        f"can_post_messages: {ADMNP.can_post_messages}\n"
                        f"can_edit_messages: {ADMNP.can_edit_messages}\n"
                        f"can_invite_users: {ADMNP.can_invite_users}\n"
                        f"can_pin_messages: {ADMNP.can_pin_messages}\n"
                        f"is_anonymous: {ADMNP.is_anonymous}"
                    )
                return await send_message(message, text=ADMIN_RIGHTS)
            elif user_chat.status == enums.ChatMemberStatus.MEMBER:
                chat = await bot.get_chat(chat_id)
                users_permissions = chat.permissions
                if users_permissions:
                    UP_MSG = (
                        f"can_send_messages: {users_permissions.can_send_messages}\n"
                        f"can_send_media_messages : {users_permissions.can_send_media_messages}\n"
                        f"can_send_other_messages: {users_permissions.can_send_other_messages}\n"
                        f"can_send_polls: {users_permissions.can_send_polls}\n"
                        f"can_add_web_page_previews: {users_permissions.can_add_web_page_previews}\n"
                        f"can_change_info: {users_permissions.can_change_info}\n"
                        f"can_invite_users: {users_permissions.can_invite_users}\n"
                        f"can_pin_messages: {users_permissions.can_pin_messages}"
                    )
                await send_message(message, text=UP_MSG)
    except ChannelInvalid as c:
        LOGGER.error({"ChannelInvalid": c})
        await send_message(message, text="Error: Make sure i am present in Chat or Chat_id is correct.")
    except Exception as e:
        LOGGER.error({"error": str(e)})

async def get_file_info(client, message):
    if message.reply_to_message and (message.reply_to_message.document or message.reply_to_message.video or message.reply_to_message.audio):
        file = message.reply_to_message.document or message.reply_to_message.video or message.reply_to_message.audio
        file_size = file.file_size
        telegram_text_limit = 4096

        if file_size > telegram_text_limit:
            random_number = ''.join(random.choices(string.digits, k=6))
            unique_filename = f"file_{random_number}.txt"
            file_path = os.path.join("downloads/info_files/", unique_filename)

            with open(file_path, 'w') as f:
                f.write(f"File data: {file}\n")  # Customize what data to save

            base_url = config_dict['BOT_BASE_URL']  # Replace with your actual base URL
            i_file = await sendFile(
                message,
                file_path,
                caption=f"File is too large. You can access it [here]({base_url}open/{unique_filename})\n\nFile will delete in 10 minutes",
            )

            # Start a background task to delete the file after 10 minutes (600 seconds)
            asyncio.create_task(delete_file_after_delay(file_path, 600, i_file))
        else:
            await message.reply(
                f"File data: {file}",
                quote=True
            )

async def delete_pm_user(client, message):
    try:
        # Extract user ID from the command arguments
        command_parts = message.text.split()
        if len(command_parts) != 2:
            await send_message(message, "Usage: /delpmuser user_id")
            return
        user_id = int(command_parts[1])  # Parse user_id as an integer
        # Call the rm_pm_user function
        await db.rm_pm_user(user_id)
        await send_message(message, f"User with ID {user_id} has been deleted.")
    except ValueError:
        await send_message(message, "Please provide a valid user ID.")
    except Exception as e:
        await send_message(message, f"An error occurred: {str(e)}")

async def delete_fsub_user(client, message):
    """
    Delete a user from the MongoDB collection based on user_id provided in the command.

    :param client: The client instance for MongoDB.
    :param message: The message object containing the command and user_id.
    """
    # Split the message text to extract the command and user_id
    command_parts = message.text.split()
    
    # Check if user_id is provided
    if len(command_parts) < 2:
        await message.reply("Please provide user_id after the command.")
        return

    user_id = command_parts[1]  # Get the user_id from the command

    try:
        if 'FSUB_IDS' in config_dict and config_dict['FSUB_IDS']:
            for chnl_id in config_dict['FSUB_IDS'].split():
                result= await db.delete_fsub_user(chnl_id, user_id)
                if result:
                    await message.reply(f"User {user_id} succesfully deleted for {chnl_id} from mongodb.")
                else:
                    await message.reply(f"User {user_id} not found in mongodb for channel {chnl_id}.")
        else:
            await message.reply("No FSUB_IDS configured.")
            LOGGER.warning("No FSUB_IDS configured.")
    except PyMongoError as e:
        await message.reply(f"Database connection error: {e}")
        LOGGER.error(f"Database connection error: {e}")
    except Exception as e:
        await message.reply(f"Error deleting user with user_id {user_id}: {e}")
        LOGGER.error(f"Error deleting user with user_id {user_id}: {e}")

async def get_start_msg_buttons(key=None, query=None):
    button_maker = ButtonMaker()
    text = None
    if key is None:
        text = config_dict['START_TEXT']
        button_maker.add_button("⋆  🎀  𝒜ᴅᴅ 𝑀ᴇ 𝒯ᴏ 𝒴ᴏᴜʀ 𝒢ʀᴏᴜᴘ  🎀  ⋆", url=f"http://t.me/{bot_name}?startgroup=start")
        # Add rows of callback data buttons
        button_maker.add_row([("⚙️ Hᴇʟᴘ ⚙️", "sbthelp help"), ("💌 Aʙᴏᴜᴛ 💌", "sbthelp about")])
        button_maker.add_button("😎 ꧁・┆✦ʚ FEATURES ɞ✦ ┆・꧂ 😎", "sbthelp futures")
        if len(config_dict['MAIN_CHNL_USRNM']) != 0:
            button_maker.add_button("Visit Channel", url=f"https://t.me/{config_dict['MAIN_CHNL_USRNM']}")
        button_maker.add_button('✘ • ᴄʟᴏsᴇ • ✘', callback_data='sbthelp close_data')
    
    elif key == 'about':
        text = config_dict['ABOUT_TEXT']

        button_maker.add_button('‼️ ᴅɪꜱᴄʟᴀɪᴍᴇʀ ‼️', callback_data='sbthelp disclaimer')
        button_maker.add_row([('Sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ', 'sbthelp source'), ('My Developers 😎', 'sbthelp mydevelopers')])
        button_maker.add_row([('⋞ ʜᴏᴍᴇ', 'sbthelp back'), ('• ᴄʟᴏsᴇ •', 'sbthelp close_data')])

    elif key == 'disclaimer':
        text = config_dict['DISCLAIMER_TXT'] if len(config_dict['DISCLAIMER_TXT']) != 0 else 'None'
        if len(config_dict['OWNER_CONTACT_LNK']) != 0:
            is_true, url = validate_and_format_url(config_dict['OWNER_CONTACT_LNK'])
            if is_true:
                url = config_dict['OWNER_CONTACT_LNK']
            else:
                url = "https://t.me/xxxxxx"
        else:
            url = "https://t.me/xxxxxx"
        button_maker.add_button('📲 ᴄᴏɴᴛᴀᴄᴛ ᴛᴏ ᴏᴡɴᴇʀ', url=url)
        button_maker.add_row([('⇋ ʙᴀᴄᴋ ⇋', "sbthelp about"), ('• ᴄʟᴏsᴇ •', 'sbthelp close_data')])
    elif key == 'source':
        is_valid, url = validate_and_format_url(config_dict['REPO_URL'])
        if is_valid:
            repo_url = config_dict['REPO_URL']
        else:
            LOGGER.error("Invalid REPO_URL, Using defult REPO_URL")
            repo_url = "https://github.com"
        button_maker.add_button('Repo', url=repo_url)
        button_maker.add_row([('⋞ ʙᴀᴄᴋ', 'sbthelp about'), ('• ᴄʟᴏsᴇ •', 'sbthelp close_data')])
        text = config_dict['SOURCE_TXT'] if len(config_dict['SOURCE_TXT']) != 0 else 'None'
    elif key == 'mydevelopers':
        text ="""🎯 𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 𝐏𝐫𝐨𝐟𝐢𝐥𝐞\n\n👨‍💻 𝗡𝗮𝗺𝗲: <a href="https://t.me/yt_farman"> ут fαямαи </a>\n🐍 𝗦𝗸𝗶𝗹𝗹: ᴘʏᴛʜᴏɴ ᴅᴇᴠᴇʟᴏᴘᴇʀ\n📚 𝗟𝗲𝗮𝗿𝗻𝗶𝗻𝗴 𝗣𝗮𝘁𝗵: sᴇʟғ-ᴛᴀᴜɢʜᴛ — ɴᴏ ғᴏʀᴍᴀʟ ᴄᴏᴜʀsᴇs, ᴊᴜsᴛ ᴄᴏᴅᴇ ᴀɴᴅ ᴄᴜʀɪᴏsɪᴛʏ! 🚀\n\n📡 𝗖𝗵𝗮𝗻𝗻𝗲𝗹: <a href="https://t.me/Nkdcrazy"> KDI DRAMA </a>\n🔧 𝗣𝗿𝗼𝗷𝗲𝗰𝘁𝘀: ʙᴏᴛ ᴅᴇᴠᴇʟᴏᴘᴍᴇɴᴛ, ᴀᴜᴛᴏᴍᴀᴛɪᴏɴ, ᴀɴᴅ ᴄʀᴇᴀᴛɪᴠᴇ ᴄᴏᴅɪɴɢ!\n\n💡 𝗧𝗲𝗰𝗵 𝗦𝘁𝗮𝗰𝗸: ᴘʏᴛʜᴏɴ (ᴍᴀɪɴ), ғʟᴀsᴋ & ғᴀsᴛᴀᴘɪ, ᴍᴏɴɢᴏᴅʙ & ᴅᴏᴄᴋᴇʀ\n\n✨ ᴄᴏᴅᴇ ʙʏ ᴘᴀssɪᴏɴ, ɴᴏᴛ ʙʏ ᴄʜᴏɪᴄᴇ — ʟᴇᴛ ᴛʜᴇ ʟɪɴᴇs sᴘᴇᴀᴋ! ✨"""
        button_maker.add_row([('⋞ ʙᴀᴄᴋ', 'sbthelp about'), ('• ᴄʟᴏsᴇ •', 'sbthelp close_data')])
    elif key == 'futures':
        text = config_dict['START_TEXT']
        button_maker.add_button("🎗️༒☬༒ ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ  ༒☬༒🎗️", "sbthelp af_feature")
        button_maker.add_row([("༒ ᴜꜱᴇʀ ꜱᴇᴛᴛɪɴɢ ༒", "sbthelp user_set_feature"), ("༒ ʙᴏᴛ ꜱᴇᴛᴛɪɴɢ ༒", "sbthelp bot_set_feature")])
        button_maker.add_row([("🎗️☬ ᴡᴇʙ ᴘᴀɢᴇ ☬🎗️", "sbthelp web_log_feature"), ("🎗️☬ ɪɴᴅᴇx ꜰɪʟᴇ ☬🎗️", "sbthelp index_featrue")])
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp back"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == "af_feature":
        text = AUTO_FILTER_MANUAL
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp futures"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == "bot_set_feature":
        text = BOT_SETTING_MANUAL
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp futures"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == "user_set_feature":
        text = USER_SETTING_MANUAL
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp futures"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == "web_log_feature":
        text = WEB_PAGE_MANUAL
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp futures"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == "index_featrue":
        text = INDEX_FILE_MANUAL
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp futures"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == "help":
        text = config_dict['HELP_TXT']
        button_maker.add_row([('🙍 ᴜꜱᴇʀ ᴄᴏᴍᴍᴀɴᴅ 🙍', "sbthelp user_cmd"), ('🤴 ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅ 🤴', "sbthelp admin_cmd")])
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp back"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == "user_cmd":
        text = USER_CMD
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp help"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == "admin_cmd":
        text = ADMIN_CMD
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", "sbthelp help"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    elif key == 'chats_btn':
        text = "Please select below button which type chats want to see"
        button_maker.add_row([("CHANNELS", "sbthelp chnl"), ("GROUPS", "sbthelp grp")])
        button_maker.add_button("• ᴄʟᴏsᴇ •", callback_data="sbthelp close_data")
    elif key == 'chnl':
        text, button_maker = await get_chat_list(1, True, False)
      
    elif key == 'grp':
        text, button_maker = await get_chat_list(1, False, True)

    elif key.startswith('next_'):
        page_number = int(key.split('_')[1])  # Extract the page number
        ichat = key.split('_')[2]
        chnl = True if ichat == 'chnl' else False
        grp = True if ichat == 'grp' else False
        text, button_maker = await get_chat_list(page_number, chnl, grp)
        
    # Build the keyboard markup
    iron_btn = button_maker.build()
    return text, iron_btn



async def start_msg_update_buttons(query, key=None):
    msg, button = await get_start_msg_buttons(key, query.message)
    await edit_message(query.message, msg, button)

async def start_msg_callback_handler(client, query: CallbackQuery):
    data = query.data.split()
    message = query.message
    callbacks = [
        "futures", "af_feature", 
        "index_featrue", "user_set_feature", 
        "bot_set_feature", "web_log_feature",
        'about', 'disclaimer', 'source', 'help',
        'mydevelopers', 'user_cmd', 'admin_cmd',
        'chats_btn', 'chnl', 'grp'
    ]
    if data[1] == 'close_data':
        await query.answer()
        await delete_message(query.message)
        await delete_message(query.message.reply_to_message)
    elif data[1] == 'back':
        await query.answer()
        if len(data) == 2:
            await start_msg_update_buttons(query, None)
    elif data[1].startswith("next_"):
        await query.answer()
        await start_msg_update_buttons(query, data[1])
    elif data[1] in callbacks:
        await query.answer()
        await start_msg_update_buttons(query, data[1])

async def get_chat_list(page=1, chnl=False, grp=False):
    query = {}
    
    chats = await db.get_all_chats(chnl, grp)

    if chnl == True:
        ichat = 'chnl'
    if grp == True:
        ichat = 'grp'

    if not chats:
        return "No chats found."

    # Define the number of chats per page
    chats_per_page = 5
    start_index = (page - 1) * chats_per_page
    end_index = start_index + chats_per_page
    total_page = len(chats) / chats_per_page

    # Slice the chats list to get only the chats for the current page
    paginated_chats = chats[start_index:end_index]

    message_list = []
    for index, chat in enumerate(paginated_chats, start=start_index + 1):
        message_list.append(f"""
---------------------------------
{index}.  _id: <code>{chat['_id']}</code>
    title: "<code>{chat['title']}</code>" 
    chat_type: "<code>{chat['chat_type']}</code>" 
    status: "<code>{chat['status']}</code>" 
    promoted_user_id: <code>{chat.get('promoted_user_id', 'null')}</code>
---------------------------------
""")

    # Prepare the response text
    response_text = "\n".join(message_list) + f"\n\nTOTAL CHATS: {len(chats)}"

    # Add pagination buttons
    button_maker = ButtonMaker()  # Assuming you have a ButtonMaker class
    if len(chats) > chats_per_page:
        if page == 1:
            button_maker.add_row([("⋞ ʙᴀᴄᴋ", f"sbthelp chats_btn"), ("Next", f"sbthelp next_{page + 1}_{ichat}")])
        elif page != 1 and end_index < len(chats):  # Check if there is a previous page
            button_maker.add_row([("⋞ ʙᴀᴄᴋ", f"sbthelp next_{page - 1}_{ichat}"), ("Next", f"sbthelp next_{page + 1}_{ichat}")])
        elif end_index >= len(chats):  # Check if there are more chats to show
            button_maker.add_button("⋞ ʙᴀᴄᴋ", callback_data=f"sbthelp next_{page - 1}_{ichat}")
        button_maker.add_button("• ᴄʟᴏsᴇ •", callback_data="sbthelp close_data")
    else:
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", f"sbthelp chats_btn"), ("• ᴄʟᴏsᴇ •", "sbthelp close_data")])
    return response_text, button_maker 

async def get_chats_ids(client, message):
    msg, button = await get_start_msg_buttons(key="chats_btn")
    await send_message(message, msg, button)


async def handle_extract_data(client, message):
    download_path = "downloads/temp"
    os.makedirs(download_path, exist_ok=True)
    try:
        if not message.reply_to_message:
            return await send_message(message, "❗ Please reply to a video or media file")
        replied_msg = message.reply_to_message
        
        if not (replied_msg.video or replied_msg.document):
            return await message.reply_text("❗ Please reply to a video or media file")
        
        m = await message.reply_sticker("CAACAgUAAxkBAAInAAFn2bDf2ce46H2xWWDXcs8M9A1f_AACNQADwSQxMbv6A1ITynAfHgQ")
        media = replied_msg.video or replied_msg.document
        original_filename = media.file_name
        download_path = f"downloads/temp/temp_{message.id}.mp4"
        
        await download_first_10mb(replied_msg, download_path)
        media_info = await extract_media_info(download_path, original_filename)

        # Build Telegram response
        telegram_response = [
            f"📁 *File:* {media_info['file_name']}",
            f"📦 *Container:* {media_info.get('container', 'N/A')}",
            f"🖼 *Res:* {media_info['video'].get('resolution', 'N/A')}",
            f"🔧 *Codec:* {media_info['video'].get('codec', 'N/A')}",
            f"🎞 *FPS:* {media_info['video'].get('fps', 'N/A')}",
            f"⏱ *Duration:* {format_time(media_info['video'].get('duration', 0))}\n",
        ]

        # Build Telegraph content
        telegraph_content = [
            f"<b>File:</b> {media_info['file_name']}<br>",
            f"<b>Container:</b> {media_info.get('container', 'N/A')}<br>",
            f"<b>Resolution:</b> {media_info['video'].get('resolution', 'N/A')}<br>",
            f"<b>Codec:</b> {media_info['video'].get('codec', 'N/A')}<br>",
            f"<b>FPS:</b> {media_info['video'].get('fps', 'N/A')}<br>",
            f"<b>Duration:</b> {format_time(media_info['video'].get('duration', 0))}<br>",
        ]

        if media_info['video'].get('bitrate'):
            bitrate = media_info['video']['bitrate'] / 1000000
            telegram_response.insert(4, f"⚡ *Bitrate:* {bitrate:.1f} Mbps")
            telegraph_content.insert(4, f"<b>Bitrate:</b> {bitrate:.1f} Mbps<br>")

        if media_info['video'].get('hdr'):
            telegram_response.insert(5, f"🌈 *HDR:* {media_info['video']['hdr']}")
            telegraph_content.insert(5, f"<b>HDR:</b> {media_info['video']['hdr']}<br>")

        # Audio tracks
        if media_info['audio_tracks']:
            audio_telegram = []
            audio_telegraph = []
            for t in media_info['audio_tracks']:
                tg = f"• {t['title'][:12]} ({t['language']}) [{t['codec']}]"
                if t.get('channels'):
                    tg += f" {t['channels']}ch"
                if t.get('sample_rate'):
                    tg += f" @{t['sample_rate']/1000:.1f}kHz"
                audio_telegram.append(tg)
                audio_telegraph.append(f"• {tg.replace('@', 'at ')}<br>")
            
            telegram_response.append(f"\n🔊 *Audio ({len(media_info['audio_tracks'])}):*\n" + "\n".join(audio_telegram))
            telegraph_content.append(f"<br><b>Audio Tracks ({len(media_info['audio_tracks'])}):</b><br>" + "".join(audio_telegraph))

        # Subtitles
        if media_info['subtitle_tracks']:
            sub_telegram = []
            sub_telegraph = []
            for t in media_info['subtitle_tracks']:
                tg = f"• {t['title'][:12]} ({t['language']}) [{t['codec']}]"
                sub_telegram.append(tg)
                sub_telegraph.append(f"• {tg}<br>")
            
            telegram_response.append(f"\n📝 *Subtitles ({len(media_info['subtitle_tracks'])}):*\n" + "\n".join(sub_telegram))
            telegraph_content.append(f"<br><b>Subtitles ({len(media_info['subtitle_tracks'])}):</b><br>" + "".join(sub_telegraph))

        # Chapters
        if media_info['chapters']:
            chap_telegram = []
            chap_telegraph = []
            for i, c in enumerate(media_info['chapters'], 1):
                start = format_time(c['start'])
                end = format_time(c['end'])
                duration = f"({int((c['end'] - c['start'])//60)}m"
                line = f"{i}. {c['title'][:12]} {start}➔{end} {duration}"
                chap_telegram.append(line)
                chap_telegraph.append(f"{line}<br>")
            
            telegram_response.append("\n📚 *Chapters:*\n" + "\n".join(chap_telegram))
            telegraph_content.append("<br><b>Chapters:</b><br>" + "".join(chap_telegraph))

        formatted_telegram = "\n".join(telegram_response)
        formatted_telegraph = "".join(telegraph_content)

        await delete_message(m)
        
        if len(formatted_telegram) > 2048:
            tele = await telegraph.create_page(
                f"Media Info: {media_info['file_name'][:80]}",
                formatted_telegraph
            )
            await send_message(message, f"📁 *File:* {media_info['file_name']}\n\nFull Media Info: {tele['url']})")
        else:
            await send_message(message, formatted_telegram)
        
    except Exception as e:
        await send_message(message, f"❌ Error: {str(e)}")
    finally:
        if download_path and os.path.exists(download_path):
            os.remove(download_path)

async def fsub_reqest_checker(client, query: CallbackQuery):
    data = query.data.split()
    if len(data) < 3:
        await query.answer("Invalid data.")
        return
    pre = data[1]
    file_id = data[2]
    await delete_message(query.message)
    await delete_message(query.message.reply_to_message)
    await query.answer(url=f"https://t.me/{bot_name}?start={pre}_{file_id}")


bot.add_handler(
    CallbackQueryHandler(start_msg_callback_handler, filters= regex("^sbthelp"))
)

bot.add_handler(MessageHandler(get_ststs, filters= command(BotCommands.StatsCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(handle_extract_data, filters= command(BotCommands.GetMediaInfoCommand)))

bot.add_handler(
    MessageHandler(
        delete_fsub_user, filters= command(BotCommands.DeleteFsubUserCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    MessageHandler(
        get_chats_ids, filters= command(BotCommands.GetChatsListCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    MessageHandler(
        get_file_info, filters= command(BotCommands.GetFileInfoCommand)
    )
)
bot.add_handler(
    MessageHandler(
        get_sticker_id, filters= command(BotCommands.GetStickerIDCommand)
    )
)
bot.add_handler(
    MessageHandler(
        check_bot_rights, filters= command(BotCommands.CheckRightsCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    MessageHandler(
        delete_pm_user, filters= command(BotCommands.DeletePMUserCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    MessageHandler(
        get_id, filters= command(BotCommands.GetIDCommand)
    )
)
bot.add_handler(
    CallbackQueryHandler(
        fsub_reqest_checker, filters=regex("^fsub_check")
    )
)
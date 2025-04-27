from io import BytesIO
import asyncio
from collections import OrderedDict
from pyrogram.enums import ChatType
from pyrogram.filters import regex, command, private
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    LOGGER,
    DATABASE_URL,
    bot,
    config_dict,
    handler_dict,
    validate_and_format_url
)

from bot.helper.extra.bot_utils import (
    new_thread,
    chnl_check,
    check_bot_connection
)
from bot.database.db_handler import DbManager

from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    sendFile,
    edit_message,
    send_message,
    delete_message
)
from bot.helper.extra.help_string import *


START = 0
STATE = "view"
event_data = {}

default_values = {
    "PORT": 8080,
    "ALRT_TXT":  IRON_ALRT_TXT,
    "AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT": 300,
    "AUTO_FILE_DELETE_MODE_TIMEOUT": 300,
    'CHK_MOV_ALRT': IRON_CHK_MOV_ALRT,
    "START_TEXT": IRON_START_TEXT,
    "RESULT_TEXT": IRON_RESULT_TEXT,
    "CUSTOM_FILE_CAPTION": IRON_CUSTOM_FILE_CAPTION,
    "IMDB_TEMPLATE_TXT": IRON_IMDB_TEMPLATE_TXT,
    "FILE_NOT_FOUND": IRON_FILE_NOT_FOUND,
    "OLD_ALRT_TXT": IRON_OLD_ALRT_TXT,
    "NORSLTS": IRON_NORSLTS,
    "MOV_NT_FND": IRON_MOV_NT_FND,
    "DISCLAIMER_TXT": IRON_DISCLAIMER_TXT,
    "SOURCE_TXT": IRON_SOURCE_TXT,
    "HELP_TXT": IRON_HELP_TXT,
    "ABOUT_TEXT": IRON_ABOUT_TEXT,
    "ADMIN_CMD_TXT": IRON_ADMIN_CMD_TXT,
    "MAX_LIST_ELM": 10,
    "UPSTREAM_REPO": "https://github.com/IronmanHUB4VF/IRON-FILTER-BOT",
    "UPSTREAM_BRANCH": "main",
}
bool_vars = [
    "USE_CAPTION_FILTER",
    "LONG_IMDB_DESCRIPTION",
    "NO_RESULTS_MSG",
    "SET_COMMANDS",
    "USENEWINVTLINKS",
    "REQ_JOIN_FSUB",
    "AUTO_FILE_DELETE_MODE",
    "IMDB_RESULT",
    "FILE_SECURE_MODE"
]

digit_vars = [
    "LOG_CHANNEL",
    "AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT",
    "AUTO_FILE_DELETE_MODE_TIMEOUT",
    "OWNER_ID",
    "FILE_BIN_CHANNEL",
    "TELEGRAM_API",
    "PORT"
]

dev_vars = [
    "OWNER_ID",
    "USER_SESSION_STRING",
    "TELEGRAM_HASH",
    "TELEGRAM_API",
    "DATABASE_URL",
    "BOT_TOKEN",
    "PORT"
]

bset_display_dict = {
    "AUTO_FILE_DELETE_MODE": "Set to true if you want the bot to automatically delete the given file after the specified time; otherwise, set it to false.\n\n⚠️ NOTE: This command will not work if FILE_SECURE_MODE is true. If you want to use this mode, set it to true, then go back and set FILE_SECURE_MODE to false.",
    "AUTO_FILE_DELETE_MODE_TIMEOUT": "This is the auto delete file timeout. This help you to set the auto delete file after given seconds.\n\nExample: <code>300</code>.\n\n⚠️ NOTE: This command will not work if AUTO_FILE_DELETE_MODE is false.",
    "BOT_TOKEN" : "get bot token from @BotFather",
    "DATABASE_URL": "Your mongodb databse url with password added",
    "FILE_SECURE_MODE": "Set to true if you want to restrict file handling to forward files only; otherwise, set it to false.\n\n⚠️ NOTE: If you set this to true, the AUTO_FILE_DELETE_MODE will not work, even if AUTO_FILE_DELETE_MODE is set to true.",
    "TELEGRAM_API": "This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.",
    "TELEGRAM_HASH": "This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.",
    "OWNER_ID": "Your user id, add only one id.",
    "RESULT_TEXT": "This text show on result when IMDB_RESULT False\n\nAdd only this variable in your text query, user_id, user_first_name, user_last_name, user_mention, query_total_results like this USER_ID: {user_id}",
    "SHORT_URL_API": "add you short domin and api, you can add multiple shortner sites like this domain:apikey, domain:apikey\nExample: <code>ironxyz.com:nfu4r84hd3487yr73h4ed7,instaearn.in:nu43h7hfe84dh348</code>\nDont Forgot to add TOKEN_TIMOUT, otherwise this not work",
    "DATABASE_CHANNEL": f"Your files channel id, where you save your files.\n\n⚠️ NOTE: This is not a bot channel, this is your channel id where you save your files.\n\nfor get channel id, forward any message from your channel with forwared tag to this bot and reply to that message with /{BotCommands.GetIDCommand} and get your channel id.\n\nExample: <code>-1001234567890</code>\n\nMultiple channel ids add by single space.\n\nExample: <code>-1001234567890 -1001234567891</code> ⚠️ NOTE: Make sure bot is admin in this channel with full rights.",
    "BOT_BASE_URL": "Your bot base url, where you host your bot.\n\nExample:\nVPS: http://127.0.0.1:8080/\nHEROKU: https://<app-name>.herokuapp.com\nKOYEB: https://relaxed-mitzi-vegamove-ff5c6c8e.koyeb.app/\nOTHER: https://yourhostingappurl.com/\n\n Note: URL must be not redirect url",
    "LOG_CHANNEL": f"Your log channel id, where you get all logs.\n\nfor get channel id, forward any message from your channel with forwared tag to this bot and reply to that message with /{BotCommands.GetIDCommand} and get your channel id.\n\nExample: <code>-1001234567890</code>\n\n⚠️ NOTE: You can add only one channel id here. Don't add multiple channel ids here and make sure bot is admin in this channel with full rights.",
    "CMD_SUFFIX": "Your bot command suffix, this is used to add suffix to your bot commands.\n\nExample: if you set this value 1 then all your bot command is set like this /id1, /stats1, /bs1,\n\n⚠️ NOTE: Don't add any space here.",
    "SUDO_USERS": "user ids of sudo users, you can add multiple user ids by space.\n\nExample: <code>123456789 987654321</code>\n\n⚠️ NOTE: This is give sudo access to this user, so be careful when you add this user id.This will give all your bot access to sudo user.",
    "FSUB_IDS": f"Channel id which you want to join before using bot.\n\nfor get channel id, forward any message from your channel with forwared tag to this bot and reply to that message with /{BotCommands.GetIDCommand} and get your channel id.\n\nExample: <code>-1001234567890</code>\n\n⚠️ NOTE: You can add multiple channel ids here by space.\n\nExample: <code>-1001234567890 -1001234567891</code> ⚠️ NOTE: Make sure bot is admin in this channel with full rights.",
    "OWNER_CONTACT_LNK": "A owner contact link, this is used to add contact link to your bot so user able to contact to you by contact link.\n\nExample: <code>https://t.me/LazyIron</code>.",
    "MAIN_CHNL_USRNM": "Your main telegram channel username\nExample: <code>HUB4VF</code>.\n\n⚠️ NOTE: Don't add @ and url here.",
    "UPDT_BTN_URL": "Your update button url, this is used to add update button to below file.\n\nExample: <code>https://t.me/BOT_UPDATE_HUB4VF</code>.\n\n⚠️ NOTE: you can add any type of url here.",
    "REQ_JOIN_FSUB": "Set to true if you want that user will join the channel in Request to join mode.\n\n⚠️ NOTE: This will not work if you not setted the FSUB_IDS variable.",
    "SET_COMMANDS": "Set to true if you want to set the bot commands automatically.",
    "START_PICS": "Your bot start pics url, this is used to add start command pics to your bot.\n\nExample: <code>https://jpcdn.it/img/9c1078d5bb5ff7d526eae590db3d3d27.jpg</code>. \n\nYou can add multiple pics by space.\n\nExample: <code>https://jpcdn.it/img/9c1078d5bb5ff7d526eae590db3d3d27.jpg https://jpcdn.it/img/9c1078d5bb5ff7d526eae590db3d3d27.jpg</code>.\n\n⚠️ NOTE: pic url must be direct image url and not redirect url.",
    "SPELL_IMG": "Your bot spell image url, this is used to add spell pics to your bot.\n\nExample: <code>https://jpcdn.it/img/9c1078d5bb5ff7d526eae590db3d3d27.jpg</code>. \n\nYou can add multiple pics by space.\n\nExample: <code>https://jpcdn.it/img/9c1078d5bb5ff7d526eae590db3d3d27.jpg https://jpcdn.it/img/9c1078d5bb5ff7d526eae590db3d3d27.jpg</code>.\n\n⚠️ NOTE: pic url must be direct image url and not redirect url.",
    "USE_CAPTION_FILTER": "Set to true if you want to use the caption filter.",
    "IMDB_RESULT": "Set to true if you want to use the IMDB result.",
    "LONG_IMDB_DESCRIPTION": "Set to true if you want to use the long IMDB description.",
    "NO_RESULTS_MSG": "Set to true if you want to use the no results message. if you set thisfalse then bot will not send any message if no results found.",
    "START_TEXT": "This is the start text of the bot.",
    "CUSTOM_FILE_CAPTION": "This is the custom file caption of the bot. This help you to add custom caption to the file.",
    "IMDB_TEMPLATE_TXT": "This is the IMDB template text of the bot. This help you to add custom IMDB template to the auto filter result text.",
    "ALRT_TXT": "This is the alert text of the bot. This help you to add custom alert text.",
    "ABOUT_TEXT": "This is the about text of the bot. This help you to add custom about text.",
    "CHK_MOV_ALRT": "This is the check movie alert text of the bot. This help you to add custom check movie alert text.",
    "CUDNT_FND": "This is the couldn't find text of the bot. This help you to add custom couldn't find text.",
    "FILE_NOT_FOUND": "This is the file not found text of the bot. This help you to add custom file not found text.",
    "OLD_ALRT_TXT": "This is the old alert text of the bot. This help you to add custom old alert text.",
    "NORSLTS": "This is the no results text of the bot. This help you to add custom no results text.",
    "MOV_NT_FND": "This is the movie not found text of the bot. This help you to add custom movie not found text.",
    "DISCLAIMER_TXT": "This is the disclaimer text of the bot. This help you to add custom disclaimer text.",
    "SOURCE_TXT": "This is the source text of the bot. This help you to add custom source text.",
    "HELP_TXT": "This is the help text of the bot. This help you to add custom help text.",
    "ADMIN_CMD_TXT": "This is the admin command text of the bot. This help you to add custom admin command text.",
    "MAX_LIST_ELM": "Maximum number of elements in the list.",
    "UPSTREAM_REPO": "Your bot upstream repo url, this is used to update your systeam code on restart bot\n\n⚠️ Note: Add carefully otherwise your bot get error and stopped on restart.\n\nExample: <code>https://github.com/IronmanHUB4VF/IRON-FILTER-BOT</code>",
    "UPSTREAM_BRANCH": "Your bot upstream repo branch name, this is used to update your systeam code on restart bot\n\n⚠️ Note: Add carefully otherwise your bot get error and stopped on restart.\n\nExample: <code>main</code>",
    "USENEWINVTLINKS": "Set to true if you want to use the new invite links in fsub. it will create a new invite link every time for the user when fsub call.",
    "AUTODELICMINGUSERMSG": "Set to true if you want to use the auto delete incoming user message. it will delete the incoming user message after setted sec.",
    "AUTO_DEL_FILTER_RESULT_MSG": "Set to true if you want to use the auto delete filter result message. it will delete the filter result message after setted sec.\n\n⚠️ NOTE: This will not work if you not setted the AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT variable.",
    "AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT": "This is the auto delete filter result message timeout. This help you to set the auto delete filter result message after given seconds.\n\nExample: <code>300</code>.\n\n⚠️ NOTE: This will not work if you not setted the AUTO_DEL_FILTER_RESULT_MSG variable True.",
    "TOKEN_TIMEOUT": "This is the token timeout. This help you to set the token timeout after given seconds.\n\nExample: <code>300</code>.\n\n⚠️ NOTE: This will not work if you not setted the SHORT_URL_API variable.",
    "FILE_BIN_CHANNEL": f"Bin channel id, By using this channel, you can remove many unwanted files from mongodb database.\n\nfor get channel id, forward any message from your channel with forwared tag to this bot and reply to that message with /{BotCommands.GetIDCommand} and get your channel id.\n\nExample: <code>-1001234567890</code>\n\n⚠️ NOTE: Make sure bot is admin in this channel with full rights. Also don't add multiple ids here otherwise this will not work.",    
}

async def get_buttons(key=None, edit_type=None, edit_mode=None, mess=None):
    buttons = ButtonMaker()
    if key is None:
        buttons.callback("Config Variables", "botset var")
        buttons.callback("Close", "botset close")
        msg = "Bot Settings:"
    elif key == "var":
        for k in list(OrderedDict(sorted(config_dict.items())).keys())[
            START : 10 + START
        ]:
            buttons.callback(k, f"botset editvar {k}")
        buttons.callback("Back", "botset back")
        buttons.callback("Close", "botset close")
        for x in range(0, len(config_dict) - 1, 10):
            buttons.callback(
                f"{int(x/10)+1}", f"botset start var {x}", position="footer"
            )
        msg = f"<b>Config Variables<b> | Page: {int(START/10)+1}"
    elif key == "private":
        buttons.callback("Back", "botset back")
        buttons.callback("Close", "botset close")
        msg = "Send private files: config.env, token.pickle, cookies.txt, accounts.zip, terabox.txt, .netrc, or any other files!\n\nTo delete a private file, send only the file name as a text message.\n\n<b>Please note:</b> Changes to .netrc will not take effect for aria2c until it's restarted.\n\n<b>Timeout:</b> 60 seconds"
    elif edit_type == "editvar":
        msg = f"<b>Variable:</b> <code>{key}</code>\n\n"
        msg += f'<b>Description:</b> {bset_display_dict.get(key, "No Description Provided")}\n\n'
        if mess.chat.type == ChatType.PRIVATE:
            msg += f'<b>Value:</b> <code>{config_dict.get(key, "None")}</code>\n\n'
        elif key not in bool_vars:
            buttons.callback(
                "View value", f"botset showvar {key}", position="header"
            )
        buttons.callback("Back", "botset back var", position="footer")
        if key not in bool_vars and key not in dev_vars:
            if not edit_mode:
                buttons.callback("Edit Value", f"botset editvar {key} edit")
            else:
                buttons.callback("Stop Edit", f"botset editvar {key}")
        if (
            key not in dev_vars
            and key not in bool_vars
        ):
            buttons.callback("Reset", f"botset resetvar {key}")
        buttons.callback("Close", "botset close", position="footer")
        if edit_mode and key in [
            "CMD_SUFFIX",
            "DATABASE_CHANNEL",
            "FILE_BIN_CHANNEL",
            "FSUB_IDS",
            "LOG_CHANNEL",
            "OWNER_ID",
            "UPSTREAM_REPO",
            "UPSTREAM_BRANCH",
            "TELEGRAM_API",
            "TELEGRAM_HASH",
            "DATABASE_URL",
            "SET_COMMANDS",
            "SUDO_USERS",
        ]:
            msg += "⚠️ <b>Note:</b> Restart required for this edit to take effect!\n\n"
        if edit_mode and key not in bool_vars:
            msg += "Send a valid value for the above Var. <b>Timeout:</b> 60 sec"
        if key in bool_vars:
            if not config_dict.get(key):
                buttons.callback("Make it True", f"botset boolvar {key} on")
            else:
                buttons.callback("Make it False", f"botset boolvar {key} off")
        if key in dev_vars:
            msg += "<b>Note:</b> Sorry but you are not able to change this var, my developer still working on it, so wait for update.\n\n"
    button = buttons.column(1) if key is None else buttons.column(2)
    return msg, button

async def update_buttons(message, key=None, edit_type=None, edit_mode=None):
    msg, button = await get_buttons(key, edit_type, edit_mode, message)
    await edit_message(message, msg, button)


async def update_variable(message):
    value = message.text
    chat_id = message.from_user.id
    if chat_id in event_data and event_data[chat_id] is not None:
        if 'event_key' in event_data[chat_id] and event_data[chat_id]['event_key'] is not None:
            key = event_data[chat_id]["event_key"]
            initial_message = event_data[chat_id]["event_msg"]
            action = event_data[chat_id]['event_action']
            try:
                if key in digit_vars:
                    value = int(value)
                if key == 'BOT_BASE_URL':
                    # Log the incoming value
                    LOGGER.info(f"Received BOT_BASE_URL value: {value}")
                    
                    is_valid, url = validate_and_format_url(value)
                    if not is_valid:
                        LOGGER.error(f"URL Invalid error when updating key: {key} value: {value}")
                        await update_buttons(initial_message, key, 'editvar', False)
                        handler_dict[chat_id] = False
                        event_data[chat_id] = None
                        alert = await send_message(message, "URL is invalid, please check the URL again.")
                        await asyncio.sleep(4)
                        await delete_message(alert)
                        return
                    else:
                        # Log the formatted URL
                        LOGGER.info(f"Formatted BOT_BASE_URL: {url}")
                        
                        is_connect = await check_bot_connection(url)
                        if not is_connect:
                            LOGGER.error(f"Connection error when updating key: {key} value: {value}")
                            await update_buttons(initial_message, key, 'editvar', False)
                            handler_dict[chat_id] = False
                            event_data[chat_id] = None
                            alert = await send_message(message, "Not able to connect with this URL\n\nPlease verify the URL again.")
                            await asyncio.sleep(4)
                            await delete_message(alert)
                            return
                        else:
                            LOGGER.info(f"Successfully connected to {url}")
                elif key in ['DATABASE_CHANNEL', 'FSUB_IDS', 'LOG_CHANNEL', 'FILE_BIN_CHANNEL']:
                    try:
                        chnl = await chnl_check(channel_id=value)
                        print(chnl)
                        i_list = []
                        for c, v in chnl.items():
                            if not v:
                                i_list.append(c)
                        if len(i_list) > 0:
                            return await send_message(message, f"Invalid channel id: {''.join(i_list)}\n\nIt may possible you not add bot in this channel or bot not have full admin access in this channel.\n\nPlease check the channel id again.")
                    except Exception as e:
                        return await send_message(message, f"Invalid channel id or format: {''.join(i_list)}\n\nIt may possible you not add bot in this channel or bot not have full admin access in this channel.\n\nPlease check the channel id again.")

                if DATABASE_URL:
                    await DbManager().update_config({key: value})
                config_dict[key] = value
                await delete_message(message)
                LOGGER.info(f"Updating key: {key} with value: {value}")
                await update_buttons(initial_message, key, 'editvar', False)
                handler_dict[chat_id] = False
                event_data[chat_id] = None
            except Exception as e:
                LOGGER.error(f"Error updating database or buttons: {e}")


async def wait_for_timeout(chat_id, timeout_duration, event_data):
    try:
        await asyncio.sleep(timeout_duration)
        # If we reach here, the timeout has occurred
        handler_dict[chat_id] = False
        await update_buttons(event_data[chat_id]['event_msg'], event_data[chat_id]['event_key'], 'editvar', False)  # Exit edit mode
    except asyncio.CancelledError:
        # This exception is raised if the task is cancelled
        pass

async def edit_bot_settings(client, query):
    asyncio.create_task(handle_edit_bot_settings(client, query))

async def handle_edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    if data[1] == "close":
        handler_dict[message.chat.id] = False
        await query.answer()
        await delete_message(message)
        await delete_message(message.reply_to_message)
    elif data[1] == "back":
        handler_dict[message.chat.id] = False
        await query.answer()
        key = data[2] if len(data) == 3 else None
        if key is None:
            globals()["START"] = 0
        await update_buttons(message, key)
    elif data[1] == "var":
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        handler_dict[message.chat.id] = False
        await query.answer("Reset done!", show_alert=True)
        value = ""
        if data[2] in default_values:
            value = default_values[data[2]]
        config_dict[data[2]] = value
        await update_buttons(message, data[2], "editvar", False)
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
    elif data[1] == "boolvar":
        handler_dict[message.chat.id] = False
        value = data[3] == "on"
        await query.answer(
            f"Successfully variable	 changed to {value}!", show_alert=True
        )
        print(f"value: {value}{type(value)}")
        config_dict[data[2]] = value
        await update_buttons(message, data[2], "editvar", False)
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
    elif data[1] == "editvar":
        handler_dict[message.chat.id] = False
        edit_mode = len(data) == 4
        await update_buttons(message, data[2], data[1], edit_mode)
        
        if data[2] in bool_vars or not edit_mode:
            return
        
        if edit_mode:
            handler_dict[message.chat.id] = True 
            # Prepare button data to pass to the timeout function
            event_data[message.chat.id] = {
                'event_msg': message,
                'event_key': data[2],
                'event_action': data[1]
            }
            # Create a task for the timeout
            timeout_task = asyncio.create_task(wait_for_timeout(message.chat.id, 60, event_data))
            iron_update = await client.send_message(chat_id=query.from_user.id, text="Hurry Up,\n\nTime Left Is: 60", reply_to_message_id=query.message.id)
            try:
                time_left = 60
                while handler_dict[message.chat.id]:  # Keep checking while it's True
                    await asyncio.sleep(1)  # Sleep to avoid busy waiting
                    time_left -= 1  # Decrease the time by 1 second
                    # When the loop ends, the time is 0 or handler_dict is False
                    if time_left == 1:  
                        await edit_message(iron_update, "Oops,\n\nYou are late buddy,\n\nTime Is Up,\n\nPlease Try Again")
                    if time_left % 2 == 0:  # Update the message every 5 seconds
                        # Update the message with the remaining time                       
                        await edit_message(iron_update, f"Hurry Up,\n\nTime Left Is: {time_left}")
                await asyncio.sleep(0.5)
                await delete_message(iron_update)
                await update_buttons(message, data[2], 'editvar', False)  # Exit edit mode
                event_data[message.chat.id] = None  # Clean up event data
            finally:
                timeout_task.cancel()
    elif data[1] == "showvar":
        value = config_dict[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await sendFile(message, out_file)
            return
        if value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "edit":
        await query.answer()
        globals()["STATE"] = "edit"
        await update_buttons(message, data[2])
    elif data[1] == "view":
        await query.answer()
        globals()["STATE"] = "view"
        await update_buttons(message, data[2])
    elif data[1] == "start":
        await query.answer()
        if int(data[3]) != START:
            globals()["START"] = int(data[3])
            await update_buttons(message, data[2])


async def bot_settings(_, message):
    msg, button = await get_buttons()
    globals()["START"] = 0
    await send_message(message, msg, button)


bot.add_handler(
    MessageHandler(
        bot_settings, filters= private & command(BotCommands.BotSetCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    CallbackQueryHandler(
        edit_bot_settings, filters=regex(r"^botset") & CustomFilters.sudo
    ), group = -1
)

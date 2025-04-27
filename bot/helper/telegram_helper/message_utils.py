import pytz
from pyrogram import enums
from re import match as re_match
from time import time
from random import choice
from asyncio import sleep
from traceback import format_exc
from datetime import datetime
from aiofiles.os import remove as aioremove
from pyrogram.types import InputMediaPhoto, InputMediaAnimation
from pyrogram.errors import (
    RPCError,
    FloodWait,
    MediaEmpty,
    MessageEmpty,
    PeerIdInvalid,
    WebpageCurlFailed,
    MessageNotModified,
    ReplyMarkupInvalid,
    UserNotParticipant,
    PhotoInvalidDimensions,
    exceptions,
    MessageIdInvalid,
    MessageDeleteForbidden
)

from bot import LOGGER, START_PICS, bot,config_dict, LOG_CHANNEL
from .button_build import ButtonMaker
from bot.helper.extra.help_string import NEW_USER_TEMP
from bot.database.db_handler import DbManager
    
IMAGES = [START_PICS]
DELETE_LINKS = None

async def send_log_message(message=None, new_user=False, text=None):
    try:
        if new_user == True:
            ichat = message.chat
            iuser = message.from_user
            await bot.send_message(
                chat_id=config_dict['LOG_CHANNEL'], 
                text=NEW_USER_TEMP.format(
                    ichat.title, ichat.id, 
                    iuser.username, iuser.first_name, iuser.last_name, 
                    iuser.id
                ), 
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        if text != None :
            await bot.send_message(
                chat_id=config_dict['LOG_CHANNEL'],
                text=text
            )
    except Exception as e:
        LOGGER.error(f"send_log_message error: {e}")
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await send_log_message(message, new_user, text)

async def sendFile(message, file, caption=None, buttons=None):
    try:
        return await message.reply_document(
            document=file,
            quote=True,
            caption=caption,
            disable_notification=True,
            reply_markup=buttons,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendFile(message, file, caption, buttons)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)
    

    
async def send_message(message, text, buttons=None, photo=None):
    try:
        if photo:
            try:
                if photo == "Random":
                    photo = choice(IMAGES)
                return await message.reply_photo(
                    photo=photo,
                    reply_to_message_id=message.id,
                    caption=text,
                    reply_markup=buttons,
                    disable_notification=True,
                )
            except IndexError:
                pass
            except Exception:
                LOGGER.error(format_exc())
        return await message.reply(
            text=text,
            quote=True,
            disable_web_page_preview=True,
            disable_notification=True,
            reply_markup=buttons
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await send_message(message, text, buttons, photo)
    except ReplyMarkupInvalid:
        return await send_message(message, text, None, photo)
    except exceptions.flood_420.SlowmodeWait as f:
        LOGGER.warning(f"Slowmode wait: {f.value} seconds. Waiting before retrying...")
        await sleep(f.value * 1.2)  # Wait for the required time
        return await send_message(message, text, buttons, photo) 
    except (MessageDeleteForbidden, MessageEmpty, MessageIdInvalid):
        pass
    except Exception as e:
        LOGGER.error(format_exc())
        return str(e)
    
async def edit_message(message, text, buttons=None, media=None):
    try:
        if message.media:
            if media:
                # Check if the media is an animation or a photo
                if isinstance(media, str) and media.endswith(('.mp4', '.gif')):
                    return await message.edit_media(
                        InputMediaAnimation(media, caption=text),
                        reply_markup=buttons
                    )
                elif isinstance(media, str):
                    return await message.edit_media(
                        InputMediaPhoto(media, caption=text),
                        reply_markup=buttons
                    )
            return await message.edit_caption(caption=text, reply_markup=buttons)
        
        # If no media is provided, edit the text message
        await message.edit(
            text=text, disable_web_page_preview=True, reply_markup=buttons
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await edit_message(message, text, buttons, media)
    except MessageIdInvalid as e:
        LOGGER.error(f"Message Not found or deleted for chat_id {message.chat.id}: {e}")
        return str(e)
    except (MessageNotModified, MessageEmpty, MessageDeleteForbidden):
        pass
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)
    
async def editReplyMarkup(message, reply_markup):
    try:
        return await message.edit_reply_markup(reply_markup=reply_markup)
    except MessageNotModified:
        pass
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)
    
def get_status():
    tz = pytz.timezone('Asia/Colombo')
    hour = datetime.now(tz).time().hour
    if 5 <= hour < 12:
        sts = "𝐺𝑜𝑜𝑑 𝑀𝑜𝑟𝑛𝑖𝑛𝑔"
    elif 12 <= hour < 18:
        sts = "𝐺𝑜𝑜𝑑 𝐴𝑓𝑡𝑒𝑟𝑛𝑜𝑜𝑛"
    else:
        sts = "𝐺𝑜𝑜𝑑 𝐸𝑣𝑒𝑛𝑖𝑛𝑔"
    return sts

    
async def delete_message(message):
    try:
        await message.delete()
    except MessageDeleteForbidden as m:
        pass
    except MessageIdInvalid as m:
        pass
    except Exception as e:
        LOGGER.error(str(e))


async def auto_delete_incoming_user_message(message):
    try:
        if config_dict['AUTODELICMINGUSERMSG']:
            await delete_message(message)
    except Exception as e:
        # Handle the exception (e.g., log it)
        LOGGER.error(f"Error deleting incoming user message: {e}")

async def auto_delete_filter_result_message(message):
    try:
        if config_dict['AUTO_DEL_FILTER_RESULT_MSG']:
            await sleep(config_dict['AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT'])
            await delete_message(message)
    except Exception as e:
        # Handle the exception (e.g., log it)
        LOGGER.error(f"Error deleting filter result message: {e}")

async def one_minute_del(message):
    await sleep(60)
    await delete_message(message)


async def five_minute_del(message):
    await sleep(300)
    await delete_message(message)

async def delete_links(message):
    if DELETE_LINKS:
        if reply_to := message.reply_to_message:
            await delete_message(reply_to)
        await delete_message(message)

async def chat_info(channel_id):
    if channel_id.startswith("-100"):
        channel_id = int(channel_id)
    elif channel_id.startswith("@"):
        channel_id = channel_id.replace("@", "")
    else:
        LOGGER.warning(f"Invalid channel ID format: {channel_id}")
        await send_log_message(text=f"Invalid channel ID format: {channel_id}")
        return None
    try:
        return await bot.get_chat(channel_id)
    except PeerIdInvalid as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        await send_log_message(text=f"{e.NAME}: {e.MESSAGE} for {channel_id}\n\nCheck the channel ID if still true and this error come then please wait for 30 to 60 miniutes, may be bot will fix it automatically. if after 60 miniutes this error still come then remove the channel id or try to add other channel id.")
        return None
    except Exception as e:
        LOGGER.error(f"Unexpected error: {e} for {channel_id}")
        await send_log_message(text=f"Unexpected error: {e} for {channel_id}")
        return None

async def isAdmin(message, user_id=None):
    if message.chat.type == message.chat.type.PRIVATE:
        return None
    if user_id:
        member = await message.chat.get_member(user_id)
    else:
        member = await message.chat.get_member(message.from_user.id)
    return member.status in [member.status.ADMINISTRATOR, member.status.OWNER]

async def forcesub(message, pre, file_id, ids, button=None, request_join=False):
    join_button = {}
    _msg = ""
    all_joined = True  # Flag to check if the user has joined all channels

    for channel_id in ids.split():
        chat = await chat_info(channel_id)
        try:
            if chat == None:
                return '', None
            # Check if the user is a member of the channel
            await chat.get_member(message.from_user.id)
        except UserNotParticipant:
            all_joined = False  # User is not a member of this channel
            if request_join:
                # Check if the user has already joined the channel
                user_id = message.from_user.id
                user_joined, user_data = await DbManager().check_requestjoined_fsub_user(channel_id, user_id)
                if user_joined:
                    continue  # Skip to the next channel if the user has joined
                else:
                    # Generate invite link for the channel
                    if username := chat.username:
                        invite_link = f"https://t.me/{username}"
                    else:
                        try:
                            if config_dict['USENEWINVTLINKS']:
                                invite_link_obj = await bot.create_chat_invite_link(chat_id=channel_id, creates_join_request=True)
                                invite_link = invite_link_obj.invite_link
                            else:
                                invite_link = await DbManager().get_invite_link(channel_id)
                                if not invite_link:
                                    invite_link_obj = await bot.create_chat_invite_link(chat_id=channel_id, creates_join_request=True)
                                    invite_link = invite_link_obj.invite_link
                                    await DbManager().save_invite_link(channel_id, invite_link)
                        except RPCError as e:
                            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
                            invite_link = chat.invite_link
            else:
                if username := chat.username:
                    invite_link = f"https://t.me/{username}"
                else:
                    invite_link = chat.invite_link
            
            # Add the invite link to the join_button dictionary
            join_button[chat.title] = invite_link

        except RPCError as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        except Exception as e:
            LOGGER.error(f"{e} for {channel_id}")

    # If the user has not joined all channels, prepare the message and buttons
    if not all_joined:
        if join_button:
            if button is None:
                button = ButtonMaker()
            _msg = "You haven't joined our channel/group yet!"
            for key, value in join_button.items():
                button.add_button(text=f"Join {key}", url=value)
            button.add_button(text='🔄 ᵀᴿʸ ᴬᴳᴬᴵᴺ 🔄', callback_data=f'fsub_check {pre} {file_id}')
    else:
        _msg = None  # User has joined all channels

    return _msg, button

async def BotPm_check(message, button=None):
    user_id = message.from_user.id
    try:
        temp_msg = await message._client.send_message(
            chat_id=message.from_user.id, text="<b>Checking Access...</b>"
        )
        await temp_msg.delete()
        return None, button
    except Exception:
        if button is None:
            button_maker = ButtonMaker()
        _msg = "ᴘʟᴇᴀꜱᴇ ᴄʟɪᴄᴋ ᴏɴ ꜱᴛᴀʀᴛ ʙᴜᴛᴛᴏɴ ꜰɪʀꜱᴛ ᴛᴏ ꜱᴛᴀʀᴛ ɢᴇᴛᴛɪɴɢ ʏᴏᴜʀ ᴍᴏᴠɪᴇ ᴏʀ ꜱᴇʀɪᴇꜱ"
        button_maker.callback("🎀  𝒞𝐿𝐼𝒞𝒦 𝑀𝐸 𝐹𝐼𝑅𝒮𝒯  🎀", f"iron {user_id} private", "header")
        button = button_maker.column()
        return _msg, button
    
async def convert_seconds_to_minutes(seconds):
    """Convert seconds to a string formatted as 'X minutes Y seconds'."""
    minutes = seconds // 60  # Calculate the number of minutes
    remaining_seconds = seconds % 60  # Calculate the remaining seconds
    return minutes, remaining_seconds


def process_channel(channel_ids):
    # Check if the input is a list
    if isinstance(channel_ids, list):
        processed_channels = []
        for value in channel_ids:
            try:
                # Convert to int if it's a string or leave it as is if it's already an int
                processed_channels.append(int(value))
            except ValueError:
                LOGGER.error(f"Value '{value}' is not a valid integer.")
        return processed_channels
    else:
        LOGGER.warning("Input is not a list.")
        return []

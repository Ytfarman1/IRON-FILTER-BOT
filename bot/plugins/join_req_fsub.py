from pyrogram import filters, enums
from pyrogram.types import ChatJoinRequest, ChatMemberUpdated
from pyrogram.handlers import ChatJoinRequestHandler, ChatMemberUpdatedHandler
from bot.database.db_handler import DbManager
from bot import config_dict, bot, LOGGER, user_bot
from bot.helper.telegram_helper.message_utils import process_channel

db = DbManager()
    
AUTH_CHANNELS = config_dict['FSUB_IDS'].split() if config_dict['FSUB_IDS'] else []
INT_AUTH_CHANNELS = [] 

if AUTH_CHANNELS:
    for AUTH_CHANNEL in AUTH_CHANNELS:
        try:
            if not AUTH_CHANNEL.startswith('-100'):
                print(f"Invalid channel ID: {AUTH_CHANNEL}. Please check your configuration.")
                continue
            AUTH_CHANNEL = INT_AUTH_CHANNELS.append(int(AUTH_CHANNEL))
        except ValueError:
            print(f"Invalid channel ID: {AUTH_CHANNEL}. Please check your configuration.")
            continue
        except Exception as e:
            print(f"An error occurred while processing auth channel ID {AUTH_CHANNEL}: {e}")
            continue

async def join_reqs_c(client, message: ChatJoinRequest):
    if not INT_AUTH_CHANNELS:
        return
    user_check, user_id = await db.check_requestjoined_fsub_user(message.chat.id, message.from_user.id)
    if user_check == True:
        return
    else:
        await db.add_requestjoined_fsub_user(message.chat.id, message.from_user.id)

async def handle_user_join_left(client, chat_member: ChatMemberUpdated):
    if config_dict['REQ_JOIN_FSUB']:
        if chat_member.old_chat_member and not chat_member.new_chat_member:
            await db.delete_fsub_user(chat_member.chat.id, chat_member.old_chat_member.user.id)
        elif chat_member.new_chat_member and not chat_member.old_chat_member:
            await db.delete_fsub_user(chat_member.chat.id, chat_member.new_chat_member.user.id)


bot.add_handler(ChatJoinRequestHandler(join_reqs_c, filters=filters.chat(INT_AUTH_CHANNELS)))
bot.add_handler(ChatMemberUpdatedHandler(handle_user_join_left, filters=filters.chat(INT_AUTH_CHANNELS)), group=1)
from pyrogram.handlers import MessageHandler
from pyrogram.filters import chat, document, video, audio
from bot import bot, LOGGER, config_dict, LOG_CHANNEL
from bot.database.db_file_handler import Media, unpack_new_file_id

file_bin_channel_id = config_dict["FILE_BIN_CHANNEL"]

async def file_bin_channel(_, message):
   try:
      media = message.document if message.document else (
         message.video if message.video else (
               message.audio if message.audio else None
         )
      )
      if media:
         file_id, file_ref = unpack_new_file_id(media.file_id)
         result = await Media.find_one({"file_id": file_id})
         if result:
            await result.delete()
            LOGGER.info(f"File {media.file_name} with ID {file_id} deleted from database")
         else:
            LOGGER.warning(f"File {media.file_name} with ID {file_id} not found in database")
   except Exception as e:
       LOGGER.error(f"Error delete file from file_bin_channel: {e}")
       await bot.send_message(LOG_CHANNEL, f"Error deleting file {media.file_name}: {str(e)}")
       return

media_filter = document | video | audio

if file_bin_channel_id:
   bot.add_handler(MessageHandler(file_bin_channel, filters= chat(file_bin_channel_id) & media_filter))
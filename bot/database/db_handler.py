from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import makedirs
from pymongo.errors import PyMongoError, DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorClient
from bot.database.db_file_handler import fdb

from bot import (
    LOGGER,
    DATABASE_URL,
    bot_id,
    bot_loop,
    user_data,
    config_dict,
)


class DbManager:
    def __init__(self):
        self.__err = False
        self.__db = None
        self.__conn = None
        self.__connect()

    def __connect(self):
        try:
            self.__conn = AsyncIOMotorClient(DATABASE_URL)
            self.__db = self.__conn.HUB4VF
        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self.__err = True

    async def db_load(self):
        if self.__err:
            return
        try:
            await self.__db.settings.config.update_one(
                {"_id": bot_id}, {"$set": config_dict}, upsert=True
            )
            LOGGER.info("Config Data Updated.")
        except Exception as e:
            LOGGER.error(f"Error loading data: {e}")
        finally:
            self.__conn.close()

    async def update_config(self, dict_, user_id=None):
        if self.__err:
            return
        try:
            if user_id:
                result = await self.__db.pm_users[bot_id].update_one(
                    {"_id": user_id}, {"$set": dict_}, upsert=True
                )
            else:
                result = await self.__db.settings.config.update_one(
                    {"_id": bot_id}, {"$set": dict_}, upsert=True
                )
            if result.modified_count > 0:
                LOGGER.info("Configuration updated successfully.")
            else:
                LOGGER.info("No changes made to the configuration.")
        except Exception as e:
            LOGGER.error(f"Error updating configuration: {e}")
        finally:
            self.__conn.close()

    async def update_aria2(self, key, value):
        if self.__err:
            return
        await self.__db.settings.aria2c.update_one(
            {"_id": bot_id}, {"$set": {key: value}}, upsert=True
        )
        self.__conn.close

    async def update_private_file(self, path):
        if self.__err:
            return
        if await aiopath.exists(path):
            async with aiopen(path, "rb+") as pf:
                pf_bin = await pf.read()
        else:
            pf_bin = ""
        path = path.replace(".", "__")
        await self.__db.settings.files.update_one(
            {"_id": bot_id}, {"$set": {path: pf_bin}}, upsert=True
        )
        self.__conn.close()

    async def get_user_data(self, user_id):
        if self.__err:
            return None  # Handle error state

        # Try to find the user data in the database
        user_data = await self.__db.pm_users[bot_id].find_one({"_id": user_id})

        if not user_data:
            # If user data is not found, insert a new user with the _id
            user_data = {"_id": user_id}  # Initialize with default values
            await self.__db.pm_users[bot_id].insert_one(user_data)
            LOGGER.info(f"New PM User Added From User Settings: {user_id}")

        return user_data

    async def update_user_doc(self, user_id, key, path=""):
        if self.__err:
            return
        if path:
            async with aiopen(path, "rb+") as doc:
                doc_bin = await doc.read()
        else:
            doc_bin = ""
        await self.__db.users[bot_id].update_one(
            {"_id": user_id}, {"$set": {key: doc_bin}}, upsert=True
        )
        self.__conn.close

    async def get_pm_uids(self):
        if self.__err:
            return  # Just exit the generator if there's an error
        async for doc in self.__db.pm_users[bot_id].find({}):
            yield doc["_id"]
    
    async def find_pm_users(self, user_id):
        if self.__err:
            return None
        result = await self.__db.pm_users[bot_id].find_one({"_id": user_id})
        if not result:
            LOGGER.warning(f"User Not Found In PM: {user_id}")
            return False
        else:
            return True

    async def update_pm_users(self, user_id):
        if self.__err:
            return None

        try:
            # Check if the user already exists
            existing_user = await self.__db.pm_users[bot_id].find_one({"_id": user_id})
            if not existing_user:
                # User does not exist, insert the new user
                await self.__db.pm_users[bot_id].insert_one({"_id": user_id})
                LOGGER.info(f"New PM User Added: {user_id}")
                return user_id
            else:
                return False  # User already exists
        except Exception as e:
            LOGGER.error(f"Error updating PM users: {e}")
            return None

    async def rm_pm_user(self, user_id):
        if self.__err:
            return
        await self.__db.pm_users[bot_id].delete_one({"_id": user_id})
        self.__conn.close

    async def update_user_tdata(self, user_id, token, time):
        if self.__err:
            return
        await self.__db.access_token.update_one(
            {"_id": user_id}, {"$set": {"token": token, "time": time}}, upsert=True
        )
        self.__conn.close

    async def update_user_token(self, user_id, token):
        if self.__err:
            return
        await self.__db.access_token.update_one(
            {"_id": user_id}, {"$set": {"token": token}}, upsert=True
        )
        self.__conn.close

    async def get_token_expiry(self, user_id):
        if self.__err:
            return None
        user_data = await self.__db.access_token.find_one({"_id": user_id})
        if user_data:
            return user_data.get("time")
        self.__conn.close
        return None

    async def delete_user_token(self, user_id):
        if self.__err:
            return
        await self.__db.access_token.delete_one({"_id": user_id})

    async def get_user_token(self, user_id):
        if self.__err:
            return None
        user_data = await self.__db.access_token.find_one({"_id": user_id})
        if user_data:
            return user_data.get("token")
        self.__conn.close
        return None

    async def delete_all_access_tokens(self):
        if self.__err:
            return
        await self.__db.access_token.delete_many({})
        self.__conn.close
   
    async def total_users_count(self):
        if self.__err:
            return
        count = await self.__db.pm_users[bot_id].count_documents({})
        return count
    
    async def get_db_size(self, file_db=None):
        if self.__err:
            return
        if file_db:
            return (await fdb.command("dbstats"))['dataSize']
        return (await self.__db.command("dbstats"))['dataSize']
    

    ########### Request Fsub ###########

    async def save_invite_link(self, channel_id, invite_link):
        if self.__err:
            return
        try:
            channel_id = str(channel_id)
            # Fix: Ensure the correct structure for saving the invite link
            await self.__db.fsub[bot_id][channel_id].insert_one({"req_fsub_invite_link": invite_link})
        except Exception as e:
            LOGGER.error(f"Error saving invite link: {e}")
        finally:
            self.__conn.close  # Fixed to call close() as a method

    async def get_invite_link(self, channel_id):
        if self.__err:
            return
        try:
            channel_id = str(channel_id)
            # Assuming __db.fsub is a dictionary-like structure where bot_id is a key
            invite_link_document = await self.__db.fsub[bot_id][channel_id].find_one({"req_fsub_invite_link": {"$exists": True}})

            if invite_link_document:
                return invite_link_document.get("req_fsub_invite_link")
            else:
                LOGGER.info(f"No invite link found for bot_id: {bot_id}, channel_id: {channel_id}")
                return None
        except Exception as e:
            LOGGER.error(f"Error finding invite link: {e}")
            return None

    async def add_requestjoined_fsub_user(self, channel_id, user_id):
        if self.__err:
            return
        try:
            channel_id = str(channel_id)
            await self.__db.fsub[bot_id][channel_id].insert_one({"_id": int(user_id)})
            LOGGER.info(f"User {user_id} added to fsub {channel_id}.")
        except DuplicateKeyError:
            LOGGER.warning(f"User {user_id} already exists in fsub {channel_id}.")
        except Exception as e:
            LOGGER.error(f"Error adding user to fsub {e}")
            pass

    async def check_requestjoined_fsub_user(self, channel_id, user_id):
        if self.__err:
            return
        """Check if the user has joined the channel in MongoDB."""
        channel_id = str(channel_id)
        user = await self.__db.fsub[bot_id][channel_id].find_one({"_id": user_id})
        if user is not None:
            return True, user
        else: 
            return False, None
        
    async def delete_fsub_user(self, chnl_id, user_id):
        if self.__err:
            return
        chnl_id = str(chnl_id)
        user_id = int(user_id)
        result = await self.__db.fsub[bot_id][chnl_id].delete_one({"_id": user_id})
                
        if result.deleted_count > 0:
            LOGGER.info(f"User  with user_id {user_id} deleted successfully from {chnl_id}.")
            return True
        else:
            LOGGER.warning(f"No user found with user_id {user_id} in {chnl_id}.")
            return False
        
    ########### Request Fsub ###########

    #--------Chats-------#
    async def add_chat_id(self, chat_id, chat_title, chat_type, status, promoted_user_id):
        if self.__err:
            return
        try:
            existing_chat = await self.__db.chats[bot_id].find_one({'_id': chat_id})
            if existing_chat:
                data = await self.__db.chats[bot_id].find_one({'_id': chat_id})
                if data['status'] != status or data['promoted_user_id'] != promoted_user_id:
                    result = await self.__db.chats[bot_id].update_one(
                        {"_id": chat_id}, {"$set": {"status": status, 'promoted_user_id': promoted_user_id}}, upsert=False
                    )
                    if result.modified_count > 0:
                        LOGGER.info(f'Chat ID {chat_id} already exist, updateing status to: {status}')
                        return True
                    else:
                        LOGGER.info(f'Chat ID {chat_id} not found or status is already {status}. No action taken.')
                        return False
                LOGGER.info(f'Chat ID {chat_id} already exists. No action taken.')
                return False
            chat = {
                '_id': chat_id,
                'title': chat_title,
                'chat_type': chat_type,
                'status': status,
                'promoted_user_id': promoted_user_id,
            }
            result = await self.__db.chats[bot_id].insert_one(chat)
            if result:
                LOGGER.info(f'Chat ID {chat_id} added with ID: {result.inserted_id}')
                return True
        except Exception as e:
            LOGGER.error('Error adding chat ID: %s', e)

    async def del_chat_id(self, chat_id):
        if self.__err:
            return
        try:
            result = await self.__db.chats[bot_id].delete_one({'_id': chat_id})
            if result.deleted_count > 0:
                LOGGER.info(f'Chat ID {chat_id} has been deleted.')
                return True
            else:
                LOGGER.info(f'Chat ID {chat_id} not found. No action taken.')
                return False
        except Exception as e:
            LOGGER.error('Error deleting chat ID: %s', e)

    async def update_chat_status(self, chat_id, status, promoted_user_id):
        if self.__err:
            return
        try:
            existing_chat = await self.__db.chats[bot_id].find_one({'_id': chat_id})
            if not existing_chat:
                LOGGER.warning(f'Chat ID {chat_id} does not exist. No action taken.')
                return 'Not Found'
            result = await self.__db.chats[bot_id].update_one(
                {"_id": chat_id}, {"$set": {"status": status, 'promoted_user_id': promoted_user_id}}, upsert=False
            )
            if result.modified_count > 0:
                LOGGER.info(f'Chat ID {chat_id} status updated to: {status}')
                return True
            else:
                LOGGER.info(f'Chat ID {chat_id} not found or status is already {status}. No action taken.')
                return False
        except Exception as e:
            LOGGER.error('Error updating chat status: %s', e)

    async def get_chat_data(self, chat_id):
        if self.__err:
            return
        data = await self.__db.chats[bot_id].find_one({'_id': chat_id})
        if data:
            return data
        else:
            return False
        
    async def get_all_chats(self, chnl=False, grp=False):
        query = {}
        if chnl:
            query["chat_type"] = "CHANNEL"
        elif grp:
            query["chat_type"] = {"$in": ["SUPERGROUP", "GROUP"]}

        chats = await self.__db.chats[bot_id].find(query).to_list(length=None)

        return chats
    #--------Chats-------#

if DATABASE_URL:
    bot_loop.run_until_complete(DbManager().db_load())

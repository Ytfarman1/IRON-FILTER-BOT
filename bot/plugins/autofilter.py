import re, math, datetime, pytz, asyncio
from asyncio import sleep
from datetime import datetime, timedelta, date, time
from imdb import Cinemagoer 
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid, MessageIdInvalid, QueryIdInvalid
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.database.db_utils import get_search_results, get_size, get_file_details
from bot.database.db_handler import DbManager
from bot import LOGGER as logger, bot, config_dict, bot_name, handler_dict, user_data, broadcast_handler_dict, deldbfiles_handler_dict
from bot.helper.extra.bot_utils import list_to_str
from bot.helper.telegram_helper.message_utils import forcesub, BotPm_check, send_message, editReplyMarkup, edit_message, delete_message, auto_delete_incoming_user_message, auto_delete_filter_result_message, convert_seconds_to_minutes
from bot.plugins.broadcast import update_broadcast_variable
from bot.plugins.bot_settings import update_variable
from bot.plugins.delete_dbfiles import deldbfiles_update_variable

imdb = Cinemagoer()
SPELL_CHECK = {}



BUTTONS = {}
GETALL = {}
SHORT = {}
FRESH = {}
db = DbManager()

CUDNT_FND = config_dict['CUDNT_FND']
FILE_NOT_FOUND = config_dict['FILE_NOT_FOUND']
SPELL_IMG = config_dict['SPELL_IMG']
NORSLTS = config_dict['NORSLTS']
LOG_CHANNEL = config_dict['LOG_CHANNEL']
LONG_IMDB_DESCRIPTION = config_dict['LONG_IMDB_DESCRIPTION']
NO_RESULTS_MSG = config_dict['NO_RESULTS_MSG']
IMDB_TEMPLATE_TXT = config_dict['IMDB_TEMPLATE_TXT']
ALRT_TXT = config_dict['ALRT_TXT']
OLD_ALRT_TXT = config_dict['OLD_ALRT_TXT']
MAX_LIST_ELM = config_dict['MAX_LIST_ELM']
iron_qualities = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]
iron_languages = ["Hindi", "English", "Gujarati", "Tamil", "Telugu", 'Marathi', "Punjabi", "Bengali", "Kannada","German", "Chinese", "Japanese", 'Spanish']
iron_seasons = ['S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08', 'S09', 'S10']
iron_episodes = [f"E{i:02}" for i in range(1, 41)]
current_year = datetime.now().year
iron_years = [str(year) for year in range(1999, current_year + 1)]

async def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        # https://t.me/GetTGLink/4183
        query = (query.strip()).lower()
        title = query
        year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year:
            year = list_to_str(year[:1])
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1]) 
        else:
            year = None
        movieid = imdb.search_movie(title.lower(), results=10)
        if not movieid:
            return None
        if year:
            filtered=list(filter(lambda k: str(k.get('year')) == str(year), movieid))
            if not filtered:
                filtered = movieid
        else:
            filtered = movieid
        movieid=list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], filtered))
        if not movieid:
            movieid = filtered
        if bulk:
            return movieid
        movieid = movieid[0].movieID
    else:
        movieid = query
    movie = imdb.get_movie(movieid)
    if movie.get("original air date"):
        date = movie["original air date"]
    elif movie.get("year"):
        date = movie.get("year")
    else:
        date = "N/A"
    plot = ""
    if not LONG_IMDB_DESCRIPTION:
        plot = movie.get('plot')
        if plot and len(plot) > 0:
            plot = plot[0]
    else:
        plot = movie.get('plot outline')
    if plot and len(plot) > 800:
        plot = plot[0:800] + "..."

    return {
        'title': movie.get('title'),
        'votes': movie.get('votes'),
        "aka": list_to_str(movie.get("akas")),
        "seasons": movie.get("number of seasons"),
        "box_office": movie.get('box office'),
        'localized_title': movie.get('localized title'),
        'kind': movie.get("kind"),
        "imdb_id": f"tt{movie.get('imdbID')}",
        "cast": list_to_str(movie.get("cast")),
        "runtime": list_to_str(movie.get("runtimes")),
        "countries": list_to_str(movie.get("countries")),
        "certificates": list_to_str(movie.get("certificates")),
        "languages": list_to_str(movie.get("languages")),
        "director": list_to_str(movie.get("director")),
        "writer":list_to_str(movie.get("writer")),
        "producer":list_to_str(movie.get("producer")),
        "composer":list_to_str(movie.get("composer")) ,
        "cinematographer":list_to_str(movie.get("cinematographer")),
        "music_team": list_to_str(movie.get("music department")),
        "distributors": list_to_str(movie.get("distributors")),
        'release_date': date,
        'year': movie.get('year'),
        'genres': list_to_str(movie.get("genres")),
        'poster': movie.get('full-size cover url'),
        'plot': plot,
        'rating': str(movie.get("rating")),
        'url':f'https://www.imdb.com/title/tt{movieid}'
    }
# https://github.com/odysseusmax/animated-lamp/blob/2ef4730eb2b5f0596ed6d03e7b05243d93e3415b/bot/utils/broadcast.py#L37


async def auto_filter(client, msg, spoll=False):
    if not msg.from_user:
        logger.warning(f"Message has no sender: {msg}")
        return
    chat_id = msg.from_user.id
    if chat_id in handler_dict and handler_dict[chat_id]:
        await update_variable(message=msg)
        return 
    if chat_id in broadcast_handler_dict and broadcast_handler_dict[chat_id]:
        await update_broadcast_variable(message=msg)
        return
    if str(chat_id) in deldbfiles_handler_dict and deldbfiles_handler_dict[str(chat_id)]:
        await deldbfiles_update_variable(message=msg)
        return
    
    button_maker = ButtonMaker()
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    if not spoll:
        message = msg
        if message.text.startswith("/"): 
            return  # ignore commands
        if message.text.startswith(("http://", "https://")): 
            return  # ignore link
        if re.findall(r"((^/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        #if msg.chat.type in [ChatType.SUPERGROUP, ChatType.GROUP]:
        #    imsg, btn = await BotPm_check(msg)
        #    if imsg and btn:
        #        await send_message(msg, imsg, buttons=btn)
        #        return
        #pm_user = await db.find_pm_users(msg.from_user.id)
        #if not pm_user:
        #    button_maker.add_button(f"Start {bot.me.first_name}", callback_data=f"iron {msg.from_user.id} private")
        #    button = button_maker.build()
        #    return await send_message(msg, text="🚫 ɪᴛ ꜱᴇᴇᴍꜱ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇꜱꜱ ᴛᴏ ᴜꜱᴇ ᴍᴇ. ᴛᴏ ɢᴀɪɴ ᴀᴄᴄᴇꜱꜱ, ᴘʟᴇᴀꜱᴇ ʀᴇɢɪꜱᴛᴇʀ ʏᴏᴜʀꜱᴇʟꜰ ɪɴ ᴏᴜʀ ᴅᴀᴛᴀʙᴀꜱᴇ ʙʏ ꜱᴇɴᴅɪɴɢ ᴛʜᴇ /ꜱᴛᴀʀᴛ ᴄᴏᴍᴍᴀɴᴅ ᴏʀ ʙʏ ᴄʟɪᴄᴋɪɴɢ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ. ᴛʜᴀɴᴋ ʏᴏᴜ! 🙌", buttons=button)

        if len(message.text) < 100:
            # Check if user_id exists in user_data
            user_id = msg.from_user.id
            if user_id not in user_data:
                user_data[user_id] = {}

            user_language = user_data[user_id]['LANGUAGE'] if 'LANGUAGE' in user_data[user_id] else None
            user_quality = user_data[user_id]['QUALITY'] if 'QUALITY' in user_data[user_id]  else None
            user_imdb = user_data[user_id]['IMDB'] if 'IMDB' in user_data[user_id] else None
            user_file_type = user_data[user_id]['FILE_TYPE'] if 'FILE_TYPE' in user_data[user_id] else None
            if not user_language or not user_quality or not user_imdb or not user_file_type:
                user_dbdata = await db.get_user_data(user_id)
                if user_dbdata:
                    if user_language is None:
                        user_language = user_dbdata['LANGUAGE'] if 'LANGUAGE' in user_dbdata else None
                        user_data[user_id]['LANGUAGE'] = user_language
                    if user_quality is None:
                        user_quality = user_dbdata['QUALITY'] if 'QUALITY' in user_dbdata else None
                        user_data[user_id]['QUALITY'] = user_quality
                    if user_imdb is None:
                        user_imdb = user_dbdata['IMDB'] if 'IMDB' in user_dbdata else None
                        user_data[user_id]['IMDB'] = user_imdb
                    if user_file_type is None:
                        user_file_type = user_dbdata['FILE_TYPE'] if 'FILE_TYPE' in user_dbdata else None
                        user_data[user_id]['FILE_TYPE'] = user_file_type
        
            search = message.text
            m = await send_message(message, f"🔎")
            search = search.lower()
            find = search.split("ᴡᴀɪᴛ ʙʀᴏ..")
            search = ""
            removes = ["in", "upload", "series", "full", "horror", "thriller", "mystery", "print", "file"]
            for x in find:
                if x in removes:
                    continue
                else:
                    search += x + " "
            search = re.sub(r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|bro|bruh|broh|helo|that|find|dubbed|link|venum|iruka|pannunga|pannungga|anuppunga|anupunga|anuppungga|anupungga|film|undo|kitti|kitty|tharu|kittumo|kittum|movie|any(one)|with\ssubtitle(s)?)", "", search, flags=re.IGNORECASE)
            search = re.sub(r"\s+", " ", search).strip()
            search = search.replace("-", " ")
            search = search.replace(":", "")

            # Removed message.chat.id
            try:
                files, offset, total_results = await get_search_results(message.chat.id, search, file_type=user_file_type, file_language=user_language, file_quality=user_quality, offset=0, filter=True)
                if not files:
                    files, offset, total_results = await get_search_results(message.chat.id, search, offset=0, filter=True)
                    if files:
                        if m:
                            await delete_message(m)
                        FRESH[f"{message.chat.id}-{message.id}"] = search
                        text = (
                            "ɴᴏ ꜰɪʟᴇꜱ ꜰᴏᴜɴᴅ ᴡɪᴛʜ ʏᴏᴜʀ ᴅᴇꜰᴜʟᴛ ꜰɪʟᴛᴇʀ\n"
                            "ʙᴜᴛ ɪ ꜰᴏᴜɴᴅ ꜱᴏᴍᴇ ꜰɪʟᴇꜱ ꜰᴏʀ ʏᴏᴜʀ Qᴜᴇʀʏ ᴡɪᴛʜᴏᴜᴛ ᴅᴇꜰᴜʟᴛ ꜰɪʟᴛᴇʀ\n"
                            "ᴛᴏ ᴡᴀᴛᴄʜ ꜰɪʟᴇꜱ ᴘʟᴇᴀꜱᴇ ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ɢᴇᴛ ꜰɪʟᴇꜱ ʙᴜᴛᴛᴏɴ"
                        )
                        buttons = ButtonMaker()
                        buttons.add_button(f"ɢᴇᴛ ꜰɪʟᴇꜱ {total_results}", callback_data=f"getallnondefultfiles#{message.chat.id}-{message.id}#{message.from_user.id if message.from_user else 0}")
                        
                        iron_fmsg = await send_message(msg, text=text, buttons=buttons.build())
                        if iron_fmsg:
                            await auto_delete_filter_result_message(iron_fmsg)
                        return
                    else:
                        if m:
                            await delete_message(m)
                        return await advantage_spell_chok(client, msg)
                    
            except Exception as e:
                logger.error(f"Unknown Error 1 in autofilter: {e}")
                pass
        else:
            return
    else:
        try:
            if msg.message.chat.type in [ChatType.SUPERGROUP, ChatType.GROUP]:
                imsg, btn = await BotPm_check(msg)
                if imsg and btn:
                    await send_message(msg, imsg, buttons=btn)
                    return
            message = msg.message.reply_to_message  # callback query
            search, files, offset, total_results = spoll
            m = await send_message(message, f"🔎")
            await delete_message(msg.message)
        except Exception as e:
            logger.error(f"Unknown Error 2 in auto filter: {e}")
            pass
    
    pre = 'file'
    key = f"{message.chat.id}-{message.id}"
    FRESH[key] = search
    GETALL[key] = files
    req = message.from_user.id if message.from_user else 0
    # Initialize ButtonMaker

    # Adding options at the top (header)
    if config_dict['MAIN_CHNL_USRNM']:
        button_maker.url("💰 ᴘʀᴇᴍɪᴜᴍ", f"https://t.me/{config_dict['MAIN_CHNL_USRNM']}", position="header")
    button_maker.callback("📂 sᴇɴᴅ ᴀʟʟ", f"sendfiles {key} {req}", position="header")

    # Adding the Filtering Data button with current page number
    current_page = 1  # Default to page 1
    button_maker.callback("🕵 ꜰɪʟᴛᴇʀɪɴɢ ᴅᴀᴛᴀ 🕵", f"fd#page#{key}#{current_page}#{req}", position="body")

    # Creating buttons for each file
    for file in files:
        button_maker.callback(
            text=f"[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}",
            callback_data=f'{pre}#{file.file_id}#{req}',
            position="files"
        )

    # Page navigation buttons
    if total_results > 0:
        total_pages = math.ceil(total_results / 10)  # Assuming 10 results per page
        current_page = 1  # Default to page 1, you can adjust this based on your logic

        # Add page navigation buttons
        button_maker.callback("📄 ᴘᴀɢᴇ", "pages", position="footer")
        button_maker.callback(f"📝 {current_page}/{total_pages}", "pages", position="footer")

        # Add Next button if there are more pages
        if total_results > 10:  # If there are more than 10 results
            button_maker.callback(f"ɴᴇxᴛ ⇛", f"next_{req}_{key}_{10}", position="footer")  # Adjust offset for next page
        else:
            button_maker.callback("↭ ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇꜱ ᴀᴠᴀɪʟᴀʙʟᴇ ↭", "pages", position="footer")

    # Build the final menu with the specified column widths
    keyboard = button_maker.build_filter_menu()


    IMDB_RESULT = user_data[req]['IMDB'] if req in user_data and 'IMDB' in user_data[req] else config_dict['IMDB_RESULT']
    
    if IMDB_RESULT and (IMDB_RESULT == 'true' or IMDB_RESULT != 'false'):
        # Fetching additional information (like IMDB data) if needed
        imdb = await get_poster(search, file=(files[0]).file_name) if files else None
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(
            hours=cur_time.hour,
            minutes=cur_time.minute,
            seconds=(cur_time.second + (cur_time.microsecond / 1000000))
        ) - timedelta(
            hours=curr_time.hour,
            minutes=curr_time.minute,
            seconds=(curr_time.second + (cur_time.microsecond / 1000000))
        )
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())

        TEMPLATE = IMDB_TEMPLATE_TXT

        if imdb:
            cap = TEMPLATE.format(
                query=search,
                title=imdb['title'],
                votes=imdb['votes'],
                aka=imdb["aka"],
                seasons=imdb["seasons"],
                box_office=imdb['box_office'],
                localized_title=imdb['localized_title'],
                kind=imdb['kind'],
                imdb_id=imdb["imdb_id"],
                cast=imdb["cast"],
                runtime=imdb["runtime"],
                countries=imdb["countries"],
                certificates=imdb["certificates"],
                languages=imdb["languages"],
                director=imdb["director"],
                writer=imdb["writer"],
                producer=imdb["producer"],
                composer=imdb["composer"],
                cinematographer=imdb["cinematographer"],
                music_team=imdb["music_team"],
                distributors=imdb["distributors"],
                release_date=imdb['release_date'],
                year=imdb['year'],
                genres=imdb['genres'],
                poster=imdb['poster'],
                plot=imdb['plot'],
                rating=imdb['rating'],
                url=imdb['url'],
                **locals()
            )
        else:
            cap = f"<b>• Title: <code>{search}</code>\n• Total Files: <code>{total_results}</code>\n• Requested By: {message.from_user.mention}\n• Result in: <code>{remaining_seconds} Seconds</code>\n</b>"

        if imdb and imdb.get('poster'):
            try:
                iron_msg = await send_message(
                    message,
                    text=cap,
                    buttons=keyboard,
                    photo=imdb.get('poster')
                )
            except Exception:
                iron_msg = await send_message(
                    message,
                    text=cap,
                    buttons=keyboard
                )
        else:
            iron_msg = await send_message(
                message,
                text=cap,
                buttons=keyboard
            )
    else:
        text = config_dict['RESULT_TEXT'].format(
            query = search,
            user_id = message.from_user.id if message else '',
            user_first_name = message.from_user.first_name if message else '',
            user_last_name = message.from_user.last_name if message else '',
            user_mention = f"@{message.from_user.username}" if message else '',
            query_total_results = total_results if total_results else ''
        )
        iron_msg = await send_message(
            message,
            text=text,
            buttons=keyboard
        )
    try:
        if m:
            await delete_message(m)
        await auto_delete_filter_result_message(iron_msg)
        await auto_delete_incoming_user_message(message)
        del BUTTONS[key]
        del GETALL[key]
        del FRESH[key]
    except Exception as e:
        logger.error(f"Error occuer while delete message in auto filter: {e}")
        pass


async def advantage_spell_chok(client, msg):
    mv_id = msg.id
    mv_rqst = msg.text
    reqstr_id = msg.from_user.id if msg.from_user else 0
    reqstr = await client.get_users(reqstr_id)
    key = f"{msg.chat.id}-{msg.id}"
    # Clean up the search query
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", mv_rqst, flags=re.IGNORECASE
    )
    query = query.strip()

    try:
        # Attempt to fetch movies from poster service
        movies = await get_poster(mv_rqst, bulk=True)
    except Exception as e:
        logger.exception(e)
    try:
        # Handle case with no results
        if not movies:
            cleaned = re.sub(r'[^\w\s]', '', mv_rqst)  # Remove symbols
            cleaned = re.sub(r'\s+', ' ', cleaned)     # Replace multiple spaces with a single space
            cleaned = cleaned.strip()                   # Remove leading and trailing spaces

            # Replace spaces with +
            reqst_gle = cleaned.replace(" ", "+")
            button = [[InlineKeyboardButton("ɢᴏᴏɢʟᴇ ᴋᴀʀᴏ ʙʜᴀɪ", url=f"https://www.google.com/search?q={reqst_gle}")]]
            if NO_RESULTS_MSG:
                await client.send_message(chat_id=LOG_CHANNEL, text=NORSLTS.format(reqstr.id, reqstr.mention, mv_rqst))
            k = await msg.reply_photo(
                photo=SPELL_IMG,
                caption=FILE_NOT_FOUND.format(mv_rqst),
                reply_markup=InlineKeyboardMarkup(button),
                quote=True
            )
            await asyncio.sleep(20)
            await delete_message(k)
            return
    except Exception as e:
        logger.error(f"Error Handle case with no results: {e}")
    
    # Compile movie list for spell-check suggestions
    movielist = [movie.get('title') for movie in movies]
    movielist += [f"{movie.get('title')} {movie.get('year')}" for movie in movies]
    SPELL_CHECK[mv_id] = movielist

    # Create buttons for spell-check suggestions
    btn = [
        [
            InlineKeyboardButton(
                text=movie_name.strip(),
                callback_data=f"spol#{reqstr_id}#{k}#{key}",
            )
        ]
        for k, movie_name in enumerate(movielist)
    ]
    btn.append([InlineKeyboardButton(text="❌ ᴄʟᴏꜱᴇ", callback_data=f'spol#{reqstr_id}#close_spellcheck#{key}')])

    # Display the spell-check suggestions
    spell_check_del = await msg.reply_photo(
        photo=SPELL_IMG,
        caption=CUDNT_FND.format(mv_rqst),
        reply_markup=InlineKeyboardMarkup(btn),
        quote=True
    )

    # Handle auto-delete with default logic
    auto_delete = True  # Default auto-delete enabled
    try:
        if auto_delete:
            await asyncio.sleep(600)
            await delete_message(spell_check_del)
    except Exception as e:
        logger.error(f"Error during auto-delete in advantage_spell_chok: {e}")

async def advantage_spoll_choker(bot, query):
    _, user, movie_, key = query.data.split('#')
    k = None

    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("This is Not For You 🚫", show_alert=True)

    if movie_ == "close_spellcheck":
        return await delete_message(query.message)
    else:
        k = movie_

    if query.message.reply_to_message:
        reply_message_id = query.message.reply_to_message.id
        if reply_message_id in SPELL_CHECK:
            movies = SPELL_CHECK[reply_message_id]
        else:
            return await query.answer("No spell check data found for this message.", show_alert=True)
    else:
        return await query.answer("Hey Bro, Please request again.", show_alert=True)

    if not movies:
        return await query.answer(config_dict['OLD_ALRT_TXT'], show_alert=True)

    movie = movies[int(movie_)]
    movie = re.sub(r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|bro|bruh|broh|helo|that|find|dubbed|link|venum|iruka|pannunga|pannungga|anuppunga|anupunga|anuppungga|anupungga|film|undo|kitti|kitty|tharu|kittumo|kittum|movie|any(one)|with\ssubtitle(s)?)", "", movie, flags=re.IGNORECASE)
    movie = re.sub(r"\s+", " ", movie).strip()
    movie = movie.replace("-", " ")
    movie = movie.replace(":", "")
    movie = re.sub(r'\s+', ' ', movie)
    movie = movie.strip()
    await query.answer(config_dict['CHK_MOV_ALRT'])

    if k:  # Ensure k is defined before this check
        user_id = query.from_user.id
        user_language = user_data[user_id]['LANGUAGE'] if 'LANGUAGE' in user_data[user_id] else None
        user_quality = user_data[user_id]['QUALITY'] if 'QUALITY' in user_data[user_id]  else None
        user_file_type = user_data[user_id]['FILE_TYPE'] if 'FILE_TYPE' in user_data[user_id]  else None
        files, offset, total_results = await get_search_results(query=movie, offset=0, file_type=user_file_type, file_language=user_language, file_quality=user_quality, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            files, offset, total_results = await get_search_results(query=movie, offset=0, filter=True)
            if files:
                FRESH[key] = movie
                text = (
                    "ɴᴏ ꜰɪʟᴇꜱ ꜰᴏᴜɴᴅ ᴡɪᴛʜ ʏᴏᴜʀ ᴅᴇꜰᴜʟᴛ ꜰɪʟᴛᴇʀ\n"
                    "ʙᴜᴛ ɪ ꜰᴏᴜɴᴅ ꜱᴏᴍᴇ ꜰɪʟᴇꜱ ꜰᴏʀ ʏᴏᴜʀ Qᴜᴇʀʏ ᴡɪᴛʜᴏᴜᴛ ᴅᴇꜰᴜʟᴛ ꜰɪʟᴛᴇʀ\n"
                    "ᴛᴏ ᴡᴀᴛᴄʜ ꜰɪʟᴇꜱ ᴘʟᴇᴀꜱᴇ ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ɢᴇᴛ ꜰɪʟᴇꜱ ʙᴜᴛᴛᴏɴ"
                )
                buttons = ButtonMaker()
                buttons.add_button(f"ɢᴇᴛ ꜰɪʟᴇꜱ {total_results}", callback_data=f"getallnondefultfiles#{key}#{user_id}")
                button = buttons.build()
                iron_msg = await edit_message(query.message, text, button)
                await auto_delete_filter_result_message(iron_msg)
                await auto_delete_incoming_user_message(query.message.reply_to_message)
            else:
                # Check if the current message content is the same as the new one
                new_content = config_dict['MOV_NT_FND']
                if query.message.text != new_content:
                    k = await edit_message(query.message, text=new_content)
                    await asyncio.sleep(10)
                    await delete_message(k)
                else:
                    await query.answer("No change in message content.", show_alert=True)


async def next_page(bot, query: CallbackQuery):
    data_parts = query.data.split("_")

    if len(data_parts) < 4:
        return await query.answer("Invalid callback data format.", show_alert=True)
    
    iden, req, key, offset = data_parts[0], data_parts[1], data_parts[2], "_".join(data_parts[3:])
    
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    
    try:
        offset_parts = offset.split("-")
        if len(offset_parts) == 2:
            offset = int(offset_parts[0])
        else:
            offset = int(offset)
    except:
        offset = 0
    
    if BUTTONS.get(key) is not None:
        search = BUTTONS.get(key)
    else:
        search = FRESH.get(key)
    
    if not search:
        await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        return
    user_id = query.from_user.id
    user_language = user_data[user_id]['LANGUAGE'] if 'LANGUAGE' in user_data[user_id] else None
    user_quality = user_data[user_id]['QUALITY'] if 'QUALITY' in user_data[user_id]  else None
    user_file_type = user_data[user_id]['FILE_TYPE'] if 'FILE_TYPE' in user_data[user_id]  else None

    files, n_offset, total = await get_search_results(query.message.chat.id, search, file_type=user_file_type, file_language=user_language, file_quality=user_quality, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    pre = 'file'
    GETALL[key] = files

    button_maker = ButtonMaker()

    # Header section with Premium and Send All buttons
    if config_dict['MAIN_CHNL_USRNM']:
        button_maker.url("💰 ᴘʀᴇᴍɪᴜᴍ", f"https://t.me/{config_dict['MAIN_CHNL_USRNM']}", position="header")
    button_maker.callback("📂 sᴇɴᴅ ᴀʟʟ", f"sendfiles {key} {req}", position="header")

    # New "Filtering Data" button with current page number
    button_maker.callback("🕵 ꜰɪʟᴛᴇʀɪɴɢ ᴅᴀᴛᴀ 🕵", f"fd#page#{key}#{math.ceil(int(offset)/10)+1}#{req}", position="body")

    # Dynamically adding file-related buttons
    for file in files:
        button_maker.callback(
            text=f"[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}",
            callback_data=f'{pre}#{file.file_id}#{req}',
            position="files"
        )

    # Page navigation buttons
    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10

    if n_offset == 0:
        if total > 10:
            button_maker.callback("⋞ ʙᴀᴄᴋ", f"next_{req}_{key}_{off_set}", position="footer")
            button_maker.callback(f"{math.ceil(int(offset)/10)+1} / {math.ceil(total/10)}", "pages", position="footer")
        else:
            button_maker.callback("📄 ᴘᴀɢᴇ", "pages", position="footer")
            button_maker.callback(f"📝 {math.ceil(int(offset)/10)+1} / {math.ceil(total/10)}", "pages", position="footer")
            button_maker.callback("↭ ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇꜱ ᴀᴠᴀɪʟᴀʙʟᴇ ↭", "pages", position="footer")
    elif off_set is None:
        button_maker.callback("📄 ᴘᴀɢᴇ", "pages", position="footer")
        button_maker.callback(f"📝 {math.ceil(int(offset)/10)+1} / {math.ceil(total/10)}", "pages", position="footer")
        button_maker.callback(f"ɴᴇxᴛ ⇛", f"next_{req}_{key}_{n_offset}", position="footer")
    else:
        button_maker.callback("⋞ ʙᴀᴄᴋ", f"next_{req}_{key}_{off_set}", position="footer")
        button_maker.callback(f"📝 {math.ceil(int(offset)/10)+1} / {math.ceil(total/10)}", "pages", position="footer")
        button_maker.callback(f"ɴᴇxᴛ ⇛", f"next_{req}_{key}_{n_offset}", position="footer")

    try:
        await editReplyMarkup(
            query.message,
            reply_markup=button_maker.build_filter_menu()
        )
    

    except MessageNotModified:
        pass
    except FloodWait as f:
        logger.warning(str(f))
        await asyncio.sleep(f.value * 1.2)
        await next_page(bot, query)
    except MessageIdInvalid as m:
        logger.error(f"error to update message cause MessageIdInvalid: {m}")
        return
 


async def auto_filter_file_sender(client, query: CallbackQuery):
    try:
        clicked = query.from_user.id
        data = query.data.split("#")

        if len(data) != 3:
            return await query.answer("This invalid data.Please request new.", show_alert=True)
        
        ident, file_id, req = query.data.split("#")
        if req not in ['file', 'sendfiles']:
            if int(req) not in [query.from_user.id, 0]:
                return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('Nᴏ sᴜᴄʜ ғɪʟᴇ ᴇxɪsᴛ.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if config_dict['CUSTOM_FILE_CAPTION']:
            try:
                f_caption = config_dict['CUSTOM_FILE_CAPTION'].format(file_name='' if title is None else title,
                                                        file_size='' if size is None else size,
                                                        file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if clicked == query.from_user.id:
                SHORT[clicked] = query.message.chat.id
                await query.answer(url=f"https://telegram.me/{bot_name}?start={ident}_{file_id}")
                return
            else:
                await query.answer(f"Hᴇʏ {query.from_user.first_name},\nTʜɪs Is Nᴏᴛ Yᴏᴜʀ Mᴏᴠɪᴇ Rᴇǫᴜᴇsᴛ.\nRᴇǫᴜᴇsᴛ Yᴏᴜʀ's !", show_alert=True)
        except UserIsBlocked:
            await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://telegram.me/{bot_name}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://telegram.me/{bot_name}?start={ident}_{file_id}")
    except QueryIdInvalid as q:
        logger.error(f"Error auto_filter_file_sender: {q}")

async def filtering_data(client, query: CallbackQuery):
    data_parts = query.data.split('#')
    if len(data_parts) < 4:
        return await query.answer("Invalid callback data format.", show_alert=True)
    
    if len(data_parts) == 4:
        current_page = 1  # Default to page 1 if not specified
    elif any(x in data_parts for x in ['qs', 'ls', 'es', 'ys', 'ss']):
        current_page = data_parts[4]
    elif len(data_parts) == 5 or len(data_parts) == 6:
        current_page = int(data_parts[3])  # Get the current page number from the callback data
    req = data_parts[-1]
    key = data_parts[2]
    all_page = 'all' in data_parts
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    # Initialize ButtonMaker
    user_lang = user_data[int(req)]['LANGUAGE'] if int(req) in user_data and 'LANGUAGE' in user_data[int(req)] else None
    user_qual = user_data[int(req)]['QUALITY'] if int(req) in user_data and 'QUALITY' in user_data[int(req)] else None
    user_imdb = user_data[int(req)]['IMDB'] if int(req) in user_data and 'IMDB' in user_data[int(req)] else None
    user_file_type = user_data[int(req)]['FILE_TYPE'] if int(req) in user_data and 'FILE_TYPE' in user_data[int(req)] else None

    button_maker = ButtonMaker()

    if data_parts[1] == 'page':
        button_maker.add_button(text="ꜰᴏʀ ᴀᴄᴛɪᴠᴇ ᴘᴀɢᴇ", callback_data=f"fd#bt#{key}#{current_page}#{req}")
        button_maker.add_button(text="ꜰᴏʀ ᴀʟʟ ᴘᴀɢᴇꜱ", callback_data=f"fd#bt#{key}#{current_page}#all#{req}")
        button_maker.add_row([("⋞ ʙᴀᴄᴋ", f"next_{query.from_user.id}_{key}_{(current_page - 1) * 10}"), ("❌ ᴄʟᴏꜱᴇ", f"fd#close#{key}#{req}")])

        keyboard = button_maker.build()

    elif data_parts[1] == 'bt':
        if all_page:
            # Add the Quality, Language, Season, Year, and Episode buttons
            if user_qual is None:
                button_maker.callback("Quality", f"fd#qf#{key}#{current_page}#all#{req}")
            if user_lang is None:
                button_maker.callback("Language", f"fd#lf#{key}#{current_page}#all#{req}")
            button_maker.callback("Season", f"fd#sf#{key}#{current_page}#all#{req}")
            button_maker.callback("Year", f"fd#yf#{key}#{current_page}#all#{req}")
            button_maker.callback("Episode", f"fd#ef#{key}#{current_page}#all#{req}")
            
        else:
            # Add the Quality, Language, Season, Year, and Episode buttons
            if user_qual is None:
                button_maker.callback("Quality", f"fd#qf#{key}#{current_page}#{req}")
            if user_lang is None:
                button_maker.callback("Language", f"fd#lf#{key}#{current_page}#{req}")
            button_maker.callback("Season", f"fd#sf#{key}#{current_page}#{req}")
            button_maker.callback("Year", f"fd#yf{key}#{current_page}#{req}")
            button_maker.callback("Episode", f"fd#ef#{key}#{current_page}#{req}")

        # Add Back and Close buttons in footer
        button_maker.callback("⋞ ʙᴀᴄᴋ", f"fd#page#{key}#{current_page}#{req}", position="footer")
        button_maker.callback("❌ ᴄʟᴏꜱᴇ", f"fd#close#{key}#{req}", position="footer")

        # Build the final menu
        keyboard = button_maker.column(2)

    elif data_parts[1] == 'home':
        movie = FRESH.get(key)
        pre = 'file'
        if not movie:
            await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
            return
        # Initialize ButtonMaker
        files, offset, total_results = await get_search_results(query=movie, offset=0, file_type=user_file_type, file_language=user_lang, file_quality=user_qual, filter=True)
        button_maker = ButtonMaker()

        # Adding options at the top (header)
        if config_dict['MAIN_CHNL_USRNM']:
            button_maker.url("💰 ᴘʀᴇᴍɪᴜᴍ", f"https://t.me/{config_dict['MAIN_CHNL_USRNM']}", position="header")
        button_maker.callback("📂 sᴇɴᴅ ᴀʟʟ", f"sendfiles {key} {req}", position="header")

        # Adding the Filtering Data button with current page number
        current_page = 1  # Default to page 1
        button_maker.callback("🕵 ꜰɪʟᴛᴇʀɪɴɢ ᴅᴀᴛᴀ 🕵", f"fd#page#{key}#{current_page}#{req}", position="body")

        # Creating buttons for each file
        for file in files:
            button_maker.callback(
                text=f"[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}",
                callback_data=f'{pre}#{file.file_id}#{req}',
                position="files"
            )

        # Page navigation buttons
        if total_results > 0:
            total_pages = math.ceil(total_results / 10)  # Assuming 10 results per page
            current_page = 1  # Default to page 1, you can adjust this based on your logic

            # Add page navigation buttons
            button_maker.callback("📄 ᴘᴀɢᴇ", "pages", position="footer")
            button_maker.callback(f"📝 {current_page}/{total_pages}", "pages", position="footer")

            # Add Next button if there are more pages
            if total_results > 10:  # If there are more than 10 results
                button_maker.callback(f"ɴᴇxᴛ ⇛", f"next_{req}_{key}_{10}", position="footer")  # Adjust offset for next page
            else:
                button_maker.callback("↭ ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇꜱ ᴀᴠᴀɪʟᴀʙʟᴇ ↭", "pages", position="footer")

        # Build the final menu with the specified column widths
        keyboard = button_maker.build_filter_menu()
        
    elif data_parts[1] in ['qf', 'lf', 'sf', 'yf', 'ef']:
        keyboard = await general_filtering(client, query)
        
    elif data_parts[1] in ['qs', 'ls', 'ss', 'ys', 'es']:
        keyboard = await general_selected(client, query)

    elif data_parts[1] == 'close':
        await delete_message(query.message)
        return
    elif data_parts[1] in ['sls', 'sqs', 'sss', 'sys', 'ses']:
        # Handle the start case
        await query.answer()
        new_start = int(data_parts[-2])  # Get the new start value from the callback data
        keyboard = await general_filtering(client, query, start=new_start)
    else:
        keyboard = None

    # Edit the message with updated buttons
    try:
        if keyboard:
            await editReplyMarkup(query.message, reply_markup=keyboard)
            await asyncio.sleep(0.5)
        else:
            return
    except MessageNotModified:
        await query.answer("Error! Buttons Can't Modify")
    except MessageIdInvalid:
        pass
    except FloodWait as e:
        logger.info(f"FloodWait: Waiting for {e.value} seconds")
        await query.answer(f'Oops! You are doing too fast. Please wait for {e.value}  before trying again.', show_alert=True)
        await asyncio.sleep(16)
        # Retry after the wait
        await editReplyMarkup(
            query.message,
            reply_markup=keyboard
        )
    
    await query.answer()

async def filter_next_page(client, query):
    data = query.data.split('_')
    data_list = ['qn', 'sn', 'yn', 'en', 'ln']
    iron_filter = None
    if len(data) != 7:
        return await query.answer("Invalid callback data format.", show_alert=True)
    user_id = query.from_user.id
    
    if data[-1] in data_list and data[-1] == 'qn':
        quality, current_page, iden, req, key, offset = data[-3], data[-2], data[0], data[1], data[2], data[3]
        offset = int(offset)
        user_lang = user_data[user_id]['LANGUAGE'] if req in user_data and 'LANGUAGE' in user_data[user_id] else None
        user_qual = user_data[user_id]['QUALITY'] if req in user_data and 'QUALITY' in user_data[user_id] else None
        user_file_type = user_data[user_id]['FILE_TYPE'] if req in user_data and 'FILE_TYPE' in user_data[user_id] else None

        curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        iron_filter = quality
        if int(req) not in [query.from_user.id, 0]:
            return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        
        if BUTTONS.get(key) is not None:
            search = BUTTONS.get(key)
        else:
            search = FRESH.get(key)
        
        if not search:
            await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
            return
   
        files, n_offset, total = await get_search_results(query.message.chat.id, search, file_type=user_file_type, file_language=user_lang, file_quality=quality, offset=offset, filter=True)
        
        try:
            n_offset = int(n_offset)
        except:
            n_offset = 0

        if not files:
            return
        pre = 'file'
        GETALL[key] = files
        filtered_files = [file for file in files if file.file_quality == quality]
    elif data[-1] in data_list and data[-1] == 'ln':
        language, current_page, iden, req, key, offset = data[-3], data[-2], data[0], data[1], data[2], data[3]
        offset = int(offset)
        user_lang = user_data[user_id]['LANGUAGE'] if req in user_data and 'LANGUAGE' in user_data[user_id] else None
        user_qual = user_data[user_id]['QUALITY'] if req in user_data and 'QUALITY' in user_data[user_id] else None
        user_file_type = user_data[user_id]['FILE_TYPE'] if req in user_data and 'FILE_TYPE' in user_data[user_id] else None

        curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        iron_filter = language
        if int(req) not in [query.from_user.id, 0]:
            return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        
        if BUTTONS.get(key) is not None:
            search = BUTTONS.get(key)
        else:
            search = FRESH.get(key)
        
        if not search:
            await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
            return
   
        files, n_offset, total = await get_search_results(query.message.chat.id, search, file_type=user_file_type, file_language=language, file_quality=user_qual, offset=offset, filter=True)
        
        try:
            n_offset = int(n_offset)
        except:
            n_offset = 0

        if not files:
            return
        pre = 'file'
        GETALL[key] = files
        filtered_files = [file for file in files if language.lower() in [lang.lower() for lang in file.file_languages]]
    elif data[-1] in data_list and data[-1] == 'sn':
        season, current_page, iden, req, key, offset = data[-3], data[-2], data[0], data[1], data[2], data[3]
        offset = int(offset)
        user_lang = user_data[user_id]['LANGUAGE'] if req in user_data and 'LANGUAGE' in user_data[user_id] else None
        user_qual = user_data[user_id]['QUALITY'] if req in user_data and 'QUALITY' in user_data[user_id] else None
        user_file_type = user_data[user_id]['FILE_TYPE'] if req in user_data and 'FILE_TYPE' in user_data[user_id] else None

        curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        iron_filter = season
        if int(req) not in [query.from_user.id, 0]:
            return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        
        if BUTTONS.get(key) is not None:
            search = BUTTONS.get(key)
        else:
            search = FRESH.get(key)
        
        if not search:
            await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
            return
   
        files, n_offset, total = await get_search_results(query.message.chat.id, search, file_type=user_file_type, file_language=user_lang, file_quality=user_qual, file_season=season, offset=offset, filter=True)
        
        try:
            n_offset = int(n_offset)
        except:
            n_offset = 0

        if not files:
            return
        pre = 'file'
        GETALL[key] = files
        filtered_files = [file for file in files if file.file_season == season]
    elif data[-1] in data_list and data[-1] == 'en':
        episode, current_page, iden, req, key, offset = data[-3], data[-2], data[0], data[1], data[2], data[3]
        offset = int(offset)
        user_lang = user_data[user_id]['LANGUAGE'] if req in user_data and 'LANGUAGE' in user_data[user_id] else None
        user_qual = user_data[user_id]['QUALITY'] if req in user_data and 'QUALITY' in user_data[user_id] else None
        user_file_type = user_data[user_id]['FILE_TYPE'] if req in user_data and 'FILE_TYPE' in user_data[user_id] else None

        curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        iron_filter = episode
        if int(req) not in [query.from_user.id, 0]:
            return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        
        if BUTTONS.get(key) is not None:
            search = BUTTONS.get(key)
        else:
            search = FRESH.get(key)
        
        if not search:
            await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
            return
   
        files, n_offset, total = await get_search_results(query.message.chat.id, search, file_type=user_file_type, file_language=user_lang, file_quality=user_qual, file_episode=episode, offset=offset, filter=True)
        
        try:
            n_offset = int(n_offset)
        except:
            n_offset = 0

        if not files:
            return
        pre = 'file'
        GETALL[key] = files
        filtered_files = [file for file in files if file.file_episode == episode]
    elif data[-1] in data_list and data[-1] == 'yn':
        year, current_page, iden, req, key, offset = data[-3], data[-2], data[0], data[1], data[2], data[3]
        offset = int(offset)
        user_lang = user_data[user_id]['LANGUAGE'] if req in user_data and 'LANGUAGE' in user_data[user_id] else None
        user_qual = user_data[user_id]['QUALITY'] if req in user_data and 'QUALITY' in user_data[user_id] else None
        user_file_type = user_data[user_id]['FILE_TYPE'] if req in user_data and 'FILE_TYPE' in user_data[user_id] else None

        curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        iron_filter = year
        if int(req) not in [query.from_user.id, 0]:
            return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        
        if BUTTONS.get(key) is not None:
            search = BUTTONS.get(key)
        else:
            search = FRESH.get(key)
        
        if not search:
            await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
            return
   
        files, n_offset, total = await get_search_results(query.message.chat.id, search, file_type=user_file_type, file_language=user_lang, file_quality=user_qual, file_year=year, offset=offset, filter=True)
        
        try:
            n_offset = int(n_offset)
        except:
            n_offset = 0

        if not files:
            return
        pre = 'file'
        GETALL[key] = files
        filtered_files = [file for file in files if file.file_year == year]
    ##############################################################################
    button_maker = ButtonMaker()

    # Header section with Premium and Send All buttons
    if config_dict['MAIN_CHNL_USRNM']:
            button_maker.url("💰 ᴘʀᴇᴍɪᴜᴍ", f"https://t.me/{config_dict['MAIN_CHNL_USRNM']}", position="header")
    button_maker.callback("📂 sᴇɴᴅ ᴀʟʟ", f"sendfiles {key} {req}", position="header")

    if data[-1] == 'qn':
        button_maker.callback("QUALITY FILTERS FILES", "quality_filters", position="body")
    elif data[-1] == 'ln':
        button_maker.callback("LANGUAGE FILTERS FILES", "language_filters", position="body")
    elif data[-1] == 'sn':
        button_maker.callback("SEASON FILTERS FILES", "season_filters", position="body")
    elif data[-1] == 'en':
        button_maker.callback("EPISODE FILTERS FILES", "episode_filters", position="body")
    elif data[-1] == 'yn':
        button_maker.callback("YEAR FILTERS FILES", "year_filters", position="body")

    # Add filtered file buttons
    for file in filtered_files:
        # Check if file_size is a dictionary or an integer
        button_maker.callback(
            text=f"[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}",
            callback_data=f'{pre}#{file.file_id}#{req}',
            position="files"
        )

    # Page navigation buttons
    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    
    if n_offset == 0:
        button_maker.callback("⋞ ᴘʀᴇᴠɪᴏᴜꜱ", f"fnext_{req}_{key}_{off_set}_{iron_filter}_{current_page}_{data[-1]}", position="extra")
        button_maker.callback(f"{math.ceil(int(offset)/10)+1} / {math.ceil(total/10)}", "pages", position="extra")
    elif off_set is None:
        button_maker.callback("📄 ᴘᴀɢᴇ", "pages", position="extra")
        button_maker.callback(f"📝 {math.ceil(int(offset)/10)+1} / {math.ceil(total/10)}", "pages", position="extra")
        button_maker.callback(f"ɴᴇxᴛ ⇛", f"fnext_{req}_{key}_{n_offset}_{iron_filter}_{current_page}_{data[-1]}", position="extra")
    else:
        button_maker.callback("⋞ ᴘʀᴇᴠɪᴏᴜꜱ", f"fnext_{req}_{key}_{off_set}_{iron_filter}_{current_page}_{data[-1]}", position="extra")
        button_maker.callback(f"📝 {math.ceil(int(offset)/10)+1} / {math.ceil(total/10)}", "pages", position="extra")
        button_maker.callback(f"ɴᴇxᴛ ⇛", f"fnext_{req}_{key}_{n_offset}_{iron_filter}_{current_page}_{data[-1]}", position="extra")
    button_maker.callback("⋞ ʙᴀᴄᴋ", f"fd#bt#{key}#{current_page}#all#{req}", position="footer")
    button_maker.callback("🏠 ʜᴏᴍᴇ", f"fd#home#{key}#{req}", position="footer")
    button_maker.callback("❌ ᴄʟᴏꜱᴇ", f"fd#close#{key}#{req}", position="footer")
    try:
        await editReplyMarkup(
            query.message,
            reply_markup=button_maker.build_filter_menu()
        )
        await asyncio.sleep(0.5)
    except MessageNotModified:
        pass
    except FloodWait as e:
        logger.info(f"FloodWait: Waiting for {e.value} seconds")
        await query.answer('OOps, You are doing to fast. Telegram says its floodwait.\n\nNow wait for 16 sec, Before try again.')
        await asyncio.sleep(16)
        # Retry after the wait
        await editReplyMarkup(
            query.message,
            reply_markup=button_maker.build_filter_menu()
        )

    await query.answer()


async def general_filtering(client, query: CallbackQuery, start=0):
    data_parts = query.data.split('#')

    if len(data_parts) < 5:
        return await query.answer("Invalid callback data format.", show_alert=True)
    
    key = data_parts[2]  # Get the key from the callback data
    current_page = int(data_parts[3])  # Get the current page number
    req = data_parts[-1]
    all_page = 'all' in data_parts
    filter_options = []
    filter_select = ''
    #fd#{filter_select}#{key}#{page * 10}#s10#{req}
    #"fd#lf#{key}#{current_page}#all#{req}"
    #----------------------------------------------------#
    if data_parts[1] == 'qf' or data_parts[1] == 'sqs':  
        # Create a list of available qualities
        filter_options = iron_qualities
        filter_select = 'qs'
    elif data_parts[1] == 'lf' or data_parts[1] == 'sls':
        # Create a list of available languages
        filter_options = iron_languages
        filter_select = 'ls'
    elif data_parts[1] == 'sf' or data_parts[1] == 'sss':  # Season filter
        filter_options = iron_seasons
        filter_select = 'ss'
    elif data_parts[1] == 'yf' or data_parts[1] == 'sys':  # Year filter
        filter_options = iron_years
        filter_select = 'ys'
    elif data_parts[1] == 'ef' or data_parts[1] == 'ses':  # Episode filter
        filter_options = iron_episodes
        filter_select = 'es'
    else:
        await query.answer(f"This is unknown filtering", show_alert=True)
    #----------------------------------------------------#
    # Initialize ButtonMaker
    button_maker = ButtonMaker()


    if all_page:
        # Add quality buttons
        for filter_option in filter_options[start : start + 10]:
            button_maker.callback(filter_option, f"fd#{filter_select}#{key}#{filter_option}#{current_page}#all#{req}", position="header")    
    else: 
        for filter_option in filter_options[start : start + 10]:
            button_maker.callback(filter_option, f"fd#{filter_select}#{key}#{filter_option}#{current_page}#{req}", position="header")
    if all_page:
        button_maker.callback("⋞ ʙᴀᴄᴋ", f"fd#bt#{key}#{current_page}#all#{req}")
    else:
        button_maker.callback("⋞ ʙᴀᴄᴋ", f"fd#bt#{key}#{current_page}#{req}")
    button_maker.callback("❌ ᴄʟᴏꜱᴇ", f"fd#close#{key}#{req}")
    check = 'all' if all_page else '#'
    if len(filter_options) > 10:
        # Pagination buttons
        total_pages = (len(filter_options) + 9) // 10  # Calculate total pages
        for page in range(total_pages):
            button_maker.callback(
                f"{page + 1}", f"fd#s{filter_select}#{key}#{current_page}#{check}#{page * 10}#{req}", position="footer"
            )
    # Build the final menu
    keyboard = button_maker.column(main_columns=2, header_columns=2, footer_columns=8)
    return keyboard

async def general_selected(client, query: CallbackQuery):
    data_parts = query.data.split('#')

    # Ensure there are enough parts in the data
    if len(data_parts) < 5:
        await query.answer("Invalid selection. Please try again.", show_alert=True)
        return
    
    key = data_parts[2]  # Get the key from the callback data
    general_filter = data_parts[3]  # Get the selected quality
    current_page = int(data_parts[4])  # Get the current page number
    req = data_parts[-1]
    all_page = 'all' in data_parts
    pre='file'
    # Calculate the offset for the current page
    offset = (current_page - 1) * 10  # Assuming 10 results per page
    iron_search = FRESH.get(key)
    try:
        if not iron_search:
            await query.answer(config_dict['OLD_ALRT_TXT'].format(query.from_user.first_name), show_alert=True)
            return
    except Exception as e:
        await query.answer(config_dict['OLD_ALRT_TXT'].format(query.from_user.first_name), show_alert=True)
        return
    
    user_lang = user_data[req]['LANGUAGE'] if req in user_data and 'LANGUAGE' in user_data[req] else None
    user_qual = user_data[req]['QUALITY'] if req in user_data and 'QUALITY' in user_data[req] else None
    user_file_type = user_data[req]['FILE_TYPE'] if req in user_data and 'FILE_TYPE' in user_data[req] else None

    # Fetch the current page's files
    if all_page:
        if data_parts[1] == 'qs':
            files, offset, total_results = await get_search_results(query.message.chat.id, iron_search, file_type=user_file_type, file_language=user_lang, file_quality=general_filter, offset=0, filter=True)
        elif data_parts[1] == 'ls':
            files, offset, total_results = await get_search_results(query.message.chat.id, iron_search, file_type=user_file_type, file_language=general_filter, file_quality=user_qual, offset=0, filter=True)
        elif data_parts[1] == 'ss':
            general_filter = str(general_filter[1:])
            files, offset, total_results = await get_search_results(query.message.chat.id, iron_search, file_type=user_file_type, file_language=user_lang, file_quality=user_qual, file_season=general_filter, offset=0, filter=True)
        elif data_parts[1] == 'ys':
            files, offset, total_results = await get_search_results(query.message.chat.id, iron_search, file_type=user_file_type, file_language=user_lang, file_quality=user_qual, file_year=general_filter, offset=0, filter=True)
        elif data_parts[1] == 'es':
            general_filter = general_filter[1:]
            files, offset, total_results = await get_search_results(query.message.chat.id, iron_search, file_type=user_file_type, file_language=user_lang, file_quality=user_qual, file_episode=general_filter, offset=0, filter=True)
    else:
        files, _, total_results = await get_search_results(query.message.chat.id, iron_search, file_type=user_file_type, max_results=10, offset=offset, file_language=user_lang, file_quality=user_qual, filter=True)

    if data_parts[1] == 'qs':
        # Filter files based on the selected quality
        filtered_files = [file for file in files if file.file_quality == general_filter]
        filter_next = 'qn'
    elif data_parts[1] == 'ls':
        # Filter files based on the selected language
        filtered_files = [file for file in files if general_filter.lower() in [lang.lower() for lang in file.file_languages]]
        filter_next = 'ln'
    elif data_parts[1] == 'ss':
        if not all_page:
            general_filter = general_filter[1:]
        filtered_files = [file for file in files if file.file_season == general_filter]
        filter_next = 'sn'
    elif data_parts[1] == 'ys':
        filtered_files = [file for file in files if file.file_year == general_filter]
        filter_next = 'yn'
    elif data_parts[1] == 'es':
        if not all_page:
            general_filter = general_filter[1:]
        filtered_files = [file for file in files if file.file_episode == general_filter]
        filter_next = 'en'
    total_count_filtered_files = len(filtered_files)

    GETALL[key] = files
    # Initialize ButtonMaker for the filtered results
    button_maker = ButtonMaker()

    # Header section with Premium and Send All buttons
    if config_dict['MAIN_CHNL_USRNM']:
            button_maker.url("💰 ᴘʀᴇᴍɪᴜᴍ", f"https://t.me/{config_dict['MAIN_CHNL_USRNM']}", position="header")
    button_maker.callback("📂 sᴇɴᴅ ᴀʟʟ", f"sendfiles {key} {req}", position="header")

    if data_parts[1] == 'qs':
        button_maker.callback("QUALITY FILTERS FILES", "quality_filters", position="body")
    elif data_parts[1] == 'ls':
        button_maker.callback("LANGUAGE FILTERS FILES", "language_filters", position="body")
    elif data_parts[1] == 'ss':
        button_maker.callback("SEASON FILTERS FILES", "season_filters", position="body")
    elif data_parts[1] == 'ys':
        button_maker.callback("YEAR FILTERS FILES", "year_filters", position="body")
    elif data_parts[1] == 'es':
        button_maker.callback("EPISODE FILTERS FILES", "episode_filters", position="body")

    if total_count_filtered_files != 0:
        # Add filtered file buttons
        for file in filtered_files:
            # Check if file_size is a dictionary or an integer
            button_maker.callback(
                text=f"[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}",
                callback_data=f'{pre}#{file.file_id}#{req}',
                position="files"
            )

        # Page navigation buttons
        if total_count_filtered_files > 0:
            if all_page:
                total_pages = math.ceil(total_results / 10)  # Assuming 10 results per page
                iron_current_page = 1  # Default to page 1, you can adjust this based on your logic
                # Add page navigation buttons
                button_maker.callback("📄 ᴘᴀɢᴇ", "pages", position="extra")
                button_maker.callback(f"📝 {iron_current_page}/{total_pages}", "pages", position="extra")
            else:
                button_maker.callback("📄 ᴄᴜʀʀᴇɴᴛ ᴘᴀɢᴇ", "pages", position="extra")
                button_maker.callback(f"{current_page}", "pages", position="extra")
            # Add Next button if there are more pages
            if all_page == True and total_results > 10:  # If there are more than 10 results
                button_maker.callback(f"ɴᴇxᴛ ⇛", f"fnext_{req}_{key}_{10}_{general_filter}_{current_page}_{filter_next}", position="extra")  # Adjust offset for next page
    else:
        button_maker.callback("↭ ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇꜱ ᴀᴠᴀɪʟᴀʙʟᴇ ↭", "pages", position="footer")
    # Add Back and Home buttons in footer
    if all_page:
        button_maker.callback("⋞ ʙᴀᴄᴋ", f"fd#bt#{key}#{current_page}#all#{req}", position="footer")
    else:
        button_maker.callback("⋞ ʙᴀᴄᴋ", f"fd#bt#{key}#{current_page}#{req}", position="footer")
    button_maker.callback("🏠 ʜᴏᴍᴇ", f"fd#home#{key}#{req}", position="footer")
    button_maker.callback("❌ ᴄʟᴏꜱᴇ", f"fd#close#{key}#{req}", position="footer")
    # Initialize keyboard variable
    keyboard = None

    # Build the final menu with the filtered results
    keyboard = button_maker.build_filter_menu()

    # Prepare the caption for the message
    if filtered_files:
        if data_parts[1] == 'qs':
            cap = f"<b>Filtered Files for Quality: {general_filter}</b>\n\n"
        elif data_parts[1] == 'ls':
            cap = f"<b>Filtered Files for Language: {general_filter}</b>\n\n"
        elif data_parts[1] == 'ss':
            cap = f"<b>Filtered Files for Season: {general_filter}</b>\n\n"
        elif data_parts[1] == 'ys':
            cap = f"<b>Filtered Files for Year: {general_filter}</b>\n\n"
        elif data_parts[1] == 'es':
            cap = f"<b>Filtered Files for Episode: {general_filter}</b>\n\n"
        for file in filtered_files:
            cap += f"<code>{file['file_name']}</code> - Size: {get_size(file.file_size)}\n"
    else:
        cap = "<b>No files found for the selected quality on active page.</b>"
        await query.answer(cap, show_alert=True)
        return
    return keyboard

async def get_all_none_defult_files(client, query):
    try:
        ident, key, req = query.data.split('#')

        if int(req) not in [query.from_user.id, 0]:
            return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)

        if BUTTONS.get(key) is not None:
            search = BUTTONS.get(key)
        else:
            search = FRESH.get(key)
        
        if not search:
            await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
            return

        files, offset, total_results = await get_search_results(query=search, offset=0, filter=True)
        if files:
            k = (search, files, offset, total_results)
            await auto_filter(bot, query, k)
    except Exception as e:
        logger.error(f"Error while handling get_all_none_defult_files: {e}")

async def send_files_handler(client, query):
    data = query.data.split()
    user_id = query.from_user.id

    ident, key, req = data

    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    
    if BUTTONS.get(key) is not None:
        search = BUTTONS.get(key)
    else:
        search = FRESH.get(key)
        
    if not search:
        await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        return
    
    return await query.answer(url=f"https://telegram.me/{bot_name}?start={ident}_{key}")

async def on_start_cmd_senfiles_handler(client, message):
    button_maker = ButtonMaker()
    cmd = message.command[1]

    key = cmd.split('_')[1]
    pre = cmd.split('_')[0]
    files = GETALL.get(key, None)

    if not files:
        return await send_message(message, "Invalid or old data.\n\nPlease send your query again")
    
    if ids := config_dict['FSUB_IDS']:
        mode = config_dict['REQ_JOIN_FSUB']
        msg, button = await forcesub(message=message, ids=ids, pre=pre, ikey=key, request_join=mode)
        if msg:
            await message.reply(msg, reply_markup=button.build())
            return
    if len(config_dict['UPDT_BTN_URL']) != 0:
        button_maker.add_button(text="📰 ᴜᴘᴅᴀᴛᴇꜱ 📰", url=config_dict['UPDT_BTN_URL'])
    iron_button = button_maker.build()
    iron_msg = []
    for file in files:
        title = file.file_name
        size=get_size(file.file_size)
        f_caption=file.caption
        if config_dict['CUSTOM_FILE_CAPTION']:
            try:
                f_caption=config_dict['CUSTOM_FILE_CAPTION'].format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption=f_caption
        if f_caption is None:
            f_caption = f"{file.file_name}"

        if len(iron_msg) != 0:
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file.file_id,
                caption=f_caption,
                protect_content=config_dict['FILE_SECURE_MODE'],
                reply_markup=iron_button if iron_button.inline_keyboard else None
            )
        else:
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file.file_id,
                caption=f_caption,
                protect_content=config_dict['FILE_SECURE_MODE'],
                reply_markup=iron_button if iron_button.inline_keyboard else None
            )
        iron_msg.append(msg)
        await asyncio.sleep(1)

    if len(iron_msg) != 0:
        if config_dict['AUTO_FILE_DELETE_MODE'] == True and not config_dict['FILE_SECURE_MODE']:
            btn = [[
                InlineKeyboardButton("❗ ɢᴇᴛ ꜰɪʟᴇ ᴀɢᴀɪɴ ❗", callback_data=f'resendfile#{key}#{pre}')
            ]]
            if config_dict['AUTO_FILE_DELETE_MODE_TIMEOUT'] > 60:
                MINUTE = await convert_seconds_to_minutes(config_dict['AUTO_FILE_DELETE_MODE_TIMEOUT'])
                k = await send_message(msg, text=f"<b>❗️ <u>ɪᴍᴘᴏʀᴛᴀɴᴛ</u> ❗️</b>\n\n<b>ᴛʜɪꜱ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ</b> <b><u>{MINUTE} ᴍɪɴᴜᴛᴇꜱ</u> </b><b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪꜱꜱᴜᴇꜱ).</b>\n\n<b><i>📌 ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴛᴏ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ.</i></b>", buttons = None)
            else:
                k = await send_message(msg, text=f"<b>❗️ <u>ɪᴍᴘᴏʀᴛᴀɴᴛ</u> ❗️</b>\n\n<b>ᴛʜɪꜱ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ</b> <b><u>{config_dict['AUTO_FILE_DELETE_MODE_TIMEOUT']} ꜱᴇᴄᴏɴᴅꜱ</u> </b><b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪꜱꜱᴜᴇꜱ).</b>\n\n<b><i>📌 ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴛᴏ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ.</i></b>", buttons = None)
            await asyncio.sleep(config_dict['AUTO_FILE_DELETE_MODE_TIMEOUT'])
            for i_msg in iron_msg:
                await delete_message(i_msg)
            await delete_message(k)
                




bot.add_handler(MessageHandler(auto_filter, filters=(filters.group|filters.private) & filters.incoming & filters.text), group=1)

bot.add_handler(
    CallbackQueryHandler(next_page, filters=filters.regex("^next_"))
)
bot.add_handler(
    CallbackQueryHandler(send_files_handler, filters=filters.regex("^sendfiles"))
)
bot.add_handler(
    CallbackQueryHandler(filter_next_page, filters=filters.regex("^fnext"))
)

bot.add_handler(
    CallbackQueryHandler(auto_filter_file_sender, filters=filters.regex("^(file|resendfile)"))
)
bot.add_handler(
    CallbackQueryHandler(filtering_data, filters=filters.regex("^fd"))
)
bot.add_handler(
    CallbackQueryHandler(advantage_spoll_choker, filters=filters.regex("^spol"))
)
bot.add_handler(
    CallbackQueryHandler(get_all_none_defult_files, filters=filters.regex("^getallnondefultfiles"))
)

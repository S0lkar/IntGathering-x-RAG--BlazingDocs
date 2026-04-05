import requests, os
from typing import Dict
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

#region CONFIG
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("TELEGRAM_API_URL")

# whitelist telegram usernames
WHITELIST = set(os.getenv("TELEGRAM_WHITELIST", "").split(","))

# sessions
USER_TOKENS: Dict[int, str] = {}
USER_PROJECT: Dict[int, str] = {}
USER_COLLECTION: Dict[int, str] = {}
USER_STATE: Dict[int, str] = {}

#endregion

#region AUTH
def is_authorized(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False

    username = user.username
    if username not in WHITELIST:
        return False

    return True
#endregion

#region API WRAPPER
def api_get(endpoint, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{API_URL}{endpoint}", headers=headers, params=params)


def api_post(endpoint, token, data=None, files=None):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{API_URL}{endpoint}", headers=headers, data=data, files=files)


def api_delete(endpoint, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.delete(f"{API_URL}{endpoint}", headers=headers, params=params)

#endregion

#region LOGIN
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_authorized(update):
        return

    await update.message.reply_text(
        "Bot RAG\n\n"
        "Usa:\n"
        "/login usuario password"
    )


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_authorized(update):
        return

    try:
        username = context.args[0]
        password = context.args[1]
    except:
        await update.message.reply_text("Uso: /login username password")
        return

    r = requests.post(
        f"{API_URL}/token",
        data={
            "username": username,
            "password": password
        }
    )

    if r.status_code != 200:
        await update.message.reply_text("Login incorrecto")
        return

    token = r.json()["access_token"]

    USER_TOKENS[update.effective_user.id] = token

    await update.message.reply_text(
        "Login OK",
        reply_markup=main_menu()
    )

#endregion

#region MENUS
def main_menu():

    kb = [
        [InlineKeyboardButton("Project", callback_data="project")],
        [InlineKeyboardButton("Collection", callback_data="collection")]
    ]

    return InlineKeyboardMarkup(kb)


def project_menu():

    kb = [
        [InlineKeyboardButton("Watch", callback_data="project_watch")],
        [InlineKeyboardButton("Add", callback_data="project_add")],
        [InlineKeyboardButton("Del", callback_data="project_del")],
    ]

    return InlineKeyboardMarkup(kb)


def collection_menu():

    kb = [
        [InlineKeyboardButton("Watch", callback_data="collection_watch")],
        [InlineKeyboardButton("Add", callback_data="collection_add")],
        [InlineKeyboardButton("Del", callback_data="collection_del")],
    ]

    return InlineKeyboardMarkup(kb)

#endregion

#region CALLBACK ROUTER

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_authorized(update):
        return

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    token = USER_TOKENS.get(user_id)

    if token is None:
        await query.message.reply_text("Debes hacer login")
        return

    data = query.data

    if data == "project":
        await query.message.edit_text(
            "Project menu",
            reply_markup=project_menu()
        )

    elif data == "collection":
        await query.message.edit_text(
            "Collection menu",
            reply_markup=collection_menu()
        )

    elif data == "project_watch":

        r = api_get("/projects", token)

        projects = r.json()

        kb = []

        for p in projects:
            kb.append([
                InlineKeyboardButton(
                    p["name"],
                    callback_data=f"select_project:{p['name']}"
                )
            ])

        await query.message.edit_text(
            "Projects",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("select_project"):

        name = data.split(":")[1]

        USER_PROJECT[user_id] = name

        kb = [
            [InlineKeyboardButton("UploadDoc", callback_data="upload_doc")],
            [InlineKeyboardButton("Execute", callback_data="execute_project")],
            [InlineKeyboardButton("RAG", callback_data="rag_project")],
        ]

        await query.message.edit_text(
            f"Project: {name}",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "upload_doc":

        USER_STATE[user_id] = "upload_doc"

        await query.message.reply_text(
            "Envía el archivo (pdf/txt/md/xlsx)"
        )

    elif data == "execute_project":

        project = USER_PROJECT[user_id]

        r = api_get("/project/excecute", token, {"name": project})

        await query.message.reply_text(str(r.json()))

    elif data == "rag_project":

        project = USER_PROJECT[user_id]

        r = api_get("/project/compile", token, {"name": project})

        await query.message.reply_text(str(r.json()))

    elif data == "collection_watch":

        project = USER_PROJECT.get(user_id)

        r = api_get("/project/collections", token, {"project": project})

        cols = r.json()

        kb = []

        for c in cols:
            kb.append([
                InlineKeyboardButton(
                    c,
                    callback_data=f"select_collection:{c}"
                )
            ])

        await query.message.edit_text(
            "Collections",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("select_collection"):

        name = data.split(":")[1]

        USER_COLLECTION[user_id] = name

        kb = [
            [InlineKeyboardButton("AddQ", callback_data="add_q")],
            [InlineKeyboardButton("DelQ", callback_data="del_q")],
        ]

        await query.message.edit_text(
            f"Collection {name}",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "add_q":

        USER_STATE[user_id] = "add_question"

        await query.message.reply_text(
            "Escribe la pregunta"
        )

#endregion

#region TEXT HANDLER

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_authorized(update):
        return

    user_id = update.effective_user.id
    token = USER_TOKENS.get(user_id)

    state = USER_STATE.get(user_id)

    if state == "add_question":

        question = update.message.text
        collection = USER_COLLECTION[user_id]

        r = api_post(
            f"/collections/{collection}/add-question",
            token,
            data={"question": question}
        )

        await update.message.reply_text(str(r.json()))

        USER_STATE[user_id] = None

#endregion

#region FILE UPLOAD

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_authorized(update):
        return

    user_id = update.effective_user.id
    state = USER_STATE.get(user_id)

    if state != "upload_doc":
        return

    token = USER_TOKENS[user_id]
    project = USER_PROJECT[user_id]

    file = await update.message.document.get_file()

    path = f"/tmp/{update.message.document.file_name}"

    await file.download_to_drive(path)

    ext = path.split(".")[-1]

    files = {"file": open(path, "rb")}

    data = {
        "name": project,
        "file_type": ext
    }

    r = api_post("/upload-doc", token, data=data, files=files)

    await update.message.reply_text(str(r.json()))

    USER_STATE[user_id] = None

#endregion

#region BOT (MAIN)
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, file_handler))
    app.run_polling()

#endregion

if __name__ == "__main__":
    main()
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#  Copyright (C) 2023. HCAT-Project-Team
#  _
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#  _
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  _
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
@File       : handler.py

@Author     : hsn

@Date       : 2024/8/9 下午12:08
"""
from pathlib import Path
from uuid import uuid4

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
from ..db import db



async def start(update: Update, context):
    m = await update.message.reply_text(update.message.chat.username)


async def set_group_permissions(update: Update, context):
    if update.message.chat.type != "group" and update.message.chat.type != "supergroup":
        await update.message.reply_text("This command can only be used in groups.")
        return
    await update.message.reply_text("Please select the permission you want to set.",
                                    reply_markup=gen_permission_options(update.message.chat.id))


def gen_permission_options(chat_id: int):
    default_perm = {"review": False, "post": False, "auto_post":False}
    try:
        perm = db.get_group_permissions(chat_id)
        for k, v in default_perm.items():
            if k not in perm:
                print(perm)
                perm[k] = v
    except KeyError:
        perm = default_perm
        db.set_group_permissions(chat_id, default_perm)

    return InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(f"{k}: {v}", callback_data=f"perm-{k}") for k, v in perm.items()] + [
            InlineKeyboardButton("Done", callback_data="perm-done")
        ]
    )


post_review_dict = {}


async def callback_handler(update: Update, context):
    print(update.callback_query.data)
    if update.callback_query.data.startswith("perm-"):
        from ..main import config

        if update.callback_query.from_user.username not in config.get("telegram").get("admin"):
            await update.callback_query.answer("You are not an admin.")
            return
        query = update.callback_query
        if query.data == "perm-done":
            await query.edit_message_text("Done.")
            return
        perm = db.get_group_permissions(query.message.chat.id)
        perm[query.data.split("-")[-1]] = not perm.get(query.data.split("-")[-1], False)
        db.set_group_permissions(query.message.chat.id, perm)

        await query.edit_message_reply_markup(reply_markup=gen_permission_options(query.message.chat.id))
        await query.answer()
    elif update.callback_query.data.startswith("post-"):
        query = update.callback_query
        if query.data == "post-done":
            await query.edit_message_text("Done.")
            medias = post_dict[f"{query.from_user.id}/{query.message.chat_id}"]["media"]
            text = post_dict[f"{query.from_user.id}/{query.message.chat_id}"]["text"]
            if f"{query.from_user.id}/{query.message.chat_id}" not in post_review_dict:
                post_review_dict[f"{query.from_user.id}/{query.message.chat_id}"] = []
            for group_id, permission in db.fetch_group_permissions():
                if permission.get("review", False):
                    if text:
                        m = await update.get_bot().send_message(group_id, text)
                        post_review_dict[f"{query.from_user.id}/{query.message.chat_id}"].append(
                            (m.chat_id, m.message_id))
                    for media in medias:
                        file_id = media["file_id"]
                        alt = media["alt"]
                        m = await update.get_bot().send_photo(group_id, file_id, caption=alt)
                        post_review_dict[f"{query.from_user.id}/{query.message.chat_id}"].append(
                            (m.chat_id, m.message_id))
                    m = await update.get_bot().send_message(
                        group_id, "Approve or reject?",
                        reply_markup=InlineKeyboardMarkup.from_column([
                            InlineKeyboardButton(
                                "Approve",
                                callback_data=f"post_review-approve_{query.from_user.id}/{query.message.chat_id}"),
                            InlineKeyboardButton(
                                "Reject",
                                callback_data=f"post_review-reject_{query.from_user.id}/{query.message.chat_id}")
                        ]))
                    post_review_dict[f"{query.from_user.id}/{query.message.chat_id}"].append((m.chat_id, m.message_id))
            return
        if query.data == "post-cancel":
            await query.edit_message_text("Cancelled.")
            post_dict.pop(f"{query.from_user.id}/{query.message.chat_id}")
            return
        await query.answer()
    elif update.callback_query.data.startswith("post_review-"):
        query = update.callback_query
        if query.data.startswith("post_review-approve"):

            uid, chat_id = query.data.split("_")[-1].split("/")
            post_id = f"{uid}/{chat_id}"
            await update.get_bot().send_message(chat_id, "Your post has been approved.")

            if not (temp := Path("temp")).exists():
                temp.mkdir()
            text = post_dict[post_id]["text"]
            paths=[]
            for media in post_dict[post_id]["media"]:
                file_id = media["file_id"]
                file = await update.get_bot().get_file(file_id)
                await file.download_to_drive(temp / f"{file_id}")
                img=Image.open(temp / f"{file_id}")
                img.save(temp / f"{file_id}.{img.format.lower()}")
                paths.append((temp / f"{file_id}.{img.format.lower()}").as_posix())
            from ..twi import account
            medias=[{"media": path} for path in paths]
            account.tweet(text, media=medias)
            post_dict.pop(post_id)
            for chat_id, msg_id in post_review_dict[post_id]:
                await update.get_bot().delete_message(chat_id, msg_id)
            post_review_dict.pop(post_id)
        elif query.data.startswith("post_review-reject"):
            post_id = query.data.split("_")[1]
            post_dict.pop(post_id)
        # await query.edit_message_text("Done.")
        await query.answer()


post_dict = {}


async def post(update: Update, context):
    if update.message.chat.type != "private":
        await update.message.reply_text("This command can only be used in private chat.")
        return
    # start post
    m = await update.message.reply_text("Please send the media you want to post.", quote=True,
                                        reply_markup=InlineKeyboardMarkup.from_column([
                                            InlineKeyboardButton("Cancel", callback_data="post-cancel")
                                        ]))
    uid = update.message.from_user.id
    post_id = f"{uid}/{update.message.chat_id}"
    post_dict[post_id] = {"text": None, "media": [], "last_msg": m.message_id}

    # for group_id, permission in db.fetch_group_permissions():
    #     if permission.get("review", False):
    #         # if medias_id in post_dict:
    #         #     post_dict[medias_id].append((group_id, text,update.message.me))
    #         # else:
    #         #     post_dict[medias_id] = [(group_id, text)]
    #


async def post_upload_photo(update: Update, context):
    bot = update.get_bot()
    if update.message.chat.type in ["group", "supergroup"]:
        if db.get_group_permissions(update.message.chat.id).get("auto_post", False):

            if not (temp := Path("temp")).exists():
                temp.mkdir()

            pid = uuid4().hex
            file = await update.message.photo[-1].get_file()
            text = update.message.caption if update.message.caption else ""
            print(update.message.photo)

            await file.download_to_drive(temp / f"{pid}")
            img=Image.open(temp / f"{pid}")
            img.save(temp / f"{pid}.{img.format.lower()}")
            from ..twi import account
            account.tweet(text, media=[{"media": (temp / f"{pid}.{img.format.lower()}").as_posix()}])
    uid = update.message.from_user.id
    post_id = f"{uid}/{update.message.chat_id}"
    if post_id not in post_dict:
        return
    m = post_dict[post_id]["last_msg"]
    await bot.delete_message(update.message.chat_id, post_dict[post_id]["last_msg"])
    if len(post_dict[post_id]["media"]) >= 4:
        m = await update.message.reply_text("Please send less than 4 photos at a time.", quote=True,
                                            reply_markup=InlineKeyboardMarkup.from_column([
                                                InlineKeyboardButton("Done", callback_data="post-done"),
                                                InlineKeyboardButton("Cancel", callback_data="post-cancel")
                                            ]))
        post_dict[post_id]["last_msg"] = m.message_id
        return
    post_dict[post_id]["media"].append(
        {"file_id": update.message.photo[-1].file_id, "alt": update.message.caption})

    count = len(post_dict[post_id]["media"])
    m = await update.message.reply_text(f"Got it. Count:{count}", quote=True,
                                        reply_markup=InlineKeyboardMarkup.from_column([
                                            InlineKeyboardButton("Done", callback_data="post-done"),
                                            InlineKeyboardButton("Cancel", callback_data="post-cancel")
                                        ]))
    post_dict[post_id]["last_msg"] = m.message_id


async def post_add_text(update: Update, context):
    uid = update.message.from_user.id
    post_id = f"{uid}/{update.message.chat_id}"
    if post_id not in post_dict:
        return
    m = post_dict[post_id]["last_msg"]
    await update.get_bot().delete_message(update.message.chat_id,
                                          post_dict[post_id]["last_msg"])
    post_dict[post_id]["text"] = update.message.text
    m = await update.message.reply_text("Got it.", quote=True,
                                        reply_markup=InlineKeyboardMarkup.from_column([
                                            InlineKeyboardButton("Done", callback_data="post-done"),
                                            InlineKeyboardButton("Cancel", callback_data="post-cancel")
                                        ]))
    post_dict[post_id]["last_msg"] = m.message_id

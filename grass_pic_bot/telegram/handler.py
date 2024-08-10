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
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

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
    default_perm = {"review": False, "post": False, "bypass_review": False}
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
        query = update.callback_query
        if query.data == "done":
            await query.edit_message_text("Done.")
            return
        perm = db.get_group_permissions(query.message.chat.id)
        perm[query.data] = not perm.get(query.data, False)
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
                            (m.chat_id,m.message_id))
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
            post_id=f"{uid}/{chat_id}"
            await update.get_bot().send_message(chat_id, "Your post has been approved.")
            post_dict.pop(post_id)
            for chat_id,msg_id in post_review_dict[post_id]:
                await update.get_bot().delete_message(chat_id, msg_id)
            post_review_dict.pop(post_id)
        elif query.data.startswith("post_review-reject"):
            post_id = query.data.split("_")[1]
            post_dict.pop(post_id)
        #await query.edit_message_text("Done.")
        await query.answer()


post_dict = {}


async def post(update: Update, context):
    # start post
    m = await update.message.reply_text("Please send the media you want to post.", quote=True,
                                        reply_markup=InlineKeyboardMarkup.from_column([
                                            InlineKeyboardButton("Cancel", callback_data="post-cancel")
                                        ]))
    uid = update.message.from_user.id
    post_id=f"{uid}/{update.message.chat_id}"
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
    uid = update.message.from_user.id
    post_id=f"{uid}/{update.message.chat_id}"
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

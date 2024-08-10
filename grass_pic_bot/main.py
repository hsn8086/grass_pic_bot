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
@File       : main.py

@Author     : hsn

@Date       : 2024/8/7 上午11:59
"""
import tomllib
from argparse import ArgumentParser
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from .db import db
from .telegram.handler import start, set_group_permissions, callback_handler, post, post_upload_photo, post_add_text
import shutil
config = {}


def main():
    global config
    parser = ArgumentParser(prog="Grass Pic Bot",
                            description="A bot that posts grass pictures to Twitter.",
                            epilog="Made by hsn8086.")
    parser.add_argument("-c", "--config", help="The path to the config file.", type=str, default="config.toml")
    if (p := Path("temp")).exists():
        shutil.rmtree(p)
    config_path = Path(parser.parse_args().config)
    if config_path.exists():

        with config_path.open('rb') as f:
            config = tomllib.load(f)
    else:
        raise FileNotFoundError(f"Config file {config_path} not found.")
    cookies = config.get("twitter").get("cookies")
    # account=Account(cookies=cookies)
    #
    # account.tweet('随便发张图',media=[
    #     {"media":"photo_2023-05-26_21-13-12.jpg","alt":"随便发张图"}
    # ])
    # persistence =PicklePersistence(filepath="")
    app = Application.builder().token("7235232629:AAEU95wBKshphzJKHB5H_AkirY6tI3HFpXg").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_group_permission", set_group_permissions))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CommandHandler("post", post, filters=filters.USER))
    app.add_handler(MessageHandler(filters.PHOTO, post_upload_photo))
    app.add_handler(MessageHandler(filters.TEXT, post_add_text))
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        db.conn.commit()
        db.conn.close()

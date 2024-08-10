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
@File       : db.py

@Author     : hsn

@Date       : 2024/8/9 下午1:53
"""
import json
from sqlite3 import connect


class DB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.collections = {}
        self.conn = connect(self.db_path)
        self.cursor = self.conn.cursor()
        # group permissions
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS group_permissions "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT ,chat_id INTEGER,permission STRING)")
        # index
        self.cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS group_permissions_chat_id_index ON group_permissions(chat_id)")
        # user permissions
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS user_permissions "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT ,user_id STRING,permission STRING)")
        # index
        self.cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS user_permissions_user_id_index ON user_permissions(user_id)")

    def get_group_permissions(self, chat_id: int):
        self.cursor.execute(f"SELECT * FROM group_permissions WHERE chat_id={chat_id}")
        if p := self.cursor.fetchall():
            data = p[0]
            j = json.loads(data[2])
            return j
        raise KeyError("Chat id not found.")

    def get_user_permissions(self, user_id: str):
        self.cursor.execute(f"SELECT * FROM user_permissions WHERE user_id={user_id}")
        if p := self.cursor.fetchall():
            data = p[0]
            j = json.loads(data[2])
            return j
        raise KeyError("User id not found.")

    def set_group_permissions(self, chat_id: int, permission: dict):
        s = json.dumps(permission, ensure_ascii=False)
        try:
            self.get_group_permissions(chat_id)
            self.cursor.execute(f"UPDATE group_permissions SET permission='{s}' WHERE chat_id={chat_id}")
        except KeyError:
            self.cursor.execute(f"INSERT INTO group_permissions (chat_id,permission) VALUES ({chat_id},'{s}')")
        self.conn.commit()

    def set_user_permissions(self, user_id: str, permission: str):
        try:
            self.get_user_permissions(user_id)
            self.cursor.execute(f"UPDATE user_permissions SET permission='{permission}' WHERE user_id={user_id}")
        except KeyError:
            self.cursor.execute(f"INSERT INTO user_permissions (user_id,permission) VALUES ({user_id},'{permission}')")
        self.conn.commit()

    def fetch_group_permissions(self):
        self.cursor.execute("SELECT * FROM group_permissions")
        for _, chat_id, permission in self.cursor.fetchall():
            yield chat_id, json.loads(permission)

db = DB("data.sqlite")

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

@Date       : 2024/8/9 下午12:47
"""
from sqlite3 import connect, Cursor

from .jelly import jelly_dump, Jelly


class Collection:
    def __init__(self, collection_name: str, cursor: Cursor):
        self.collection_name = collection_name
        self.cursor = cursor
        self.inited = False

    def init(self, obj_type: Jelly):
        d = jelly_dump(obj_type)
        self.cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {self.collection_name} "
            f"(id INTEGER PRIMARY KEY AUTOINCREMENT ,{','.join([f'{k} {type(v).__name__}' for k, v in d.items()])})")
        self.inited = True

    def insert(self, obj: Jelly):
        if not self.inited:
            self.init(obj)
        d = jelly_dump(obj)
        self.cursor.execute(
            f"INSERT INTO {self.collection_name} ({','.join(d.keys())}) VALUES ({','.join(v.__repr__() for v in d.values())})")


class DB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.collections = {}
        self.conn = connect(self.db_path)
        self.cursor = self.conn.cursor()

    def get_collection(self, collection_name: str):
        if collection_name not in self.collections:
            self.collections[collection_name] = Collection(collection_name, self.cursor)
        return self.collections[collection_name]

    def insert(self, data: Jelly):
        type_name = type(data).__name__
        collection = self.get_collection(type_name)
        collection.insert(data)

    def select(self, obj, selectors:str):
        type_name = obj.__name__
        self.cursor.execute(f"SELECT * FROM {type_name} WHERE {selectors}")
        return self.cursor.fetchall()
    def update(self, obj, selectors:str, new_data:Jelly):
        type_name = obj.__name__
        d = jelly_dump(new_data)
        self.cursor.execute(f"UPDATE {type_name} SET {','.join([f'{k}={v.__repr__()}' for k, v in d.items()])} WHERE {selectors}")

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

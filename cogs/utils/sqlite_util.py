# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os

import aiosqlite


class aio_sqlite():
    def __init__(self):
        self.currentpath = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__))))
        self.db_path = f'{self.currentpath}/data/example.sqlite3'

    async def create_db_reaction(self):
        db = await aiosqlite.connect(f'{self.db_path}')
        aiosqlite.register_adapter(
            list, lambda l: ';'.join([str(i) for i in l]))
        aiosqlite.register_converter(
            'List', lambda s: [item.decode('utf-8') for item in s.split(bytes(b';'))])
        await db.execute('create table if not exists reactions(id INTEGER PRIMARY KEY, guild INTEGER, channel INTEGER,cnt INTEGER, reaction_sum INTEGER, matte INTEGER, author TEXT, timestamp TEXT,role LIST)')

    async def db_connect(self):
        conn = await aiosqlite.connect(f'{self.db_path}')
        conn.row_factory = aiosqlite.Row
        return conn


if __name__ == "__main__":
    aiodb = aio_sqlite()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(aiodb.create_db_reaction())
    loop.close()

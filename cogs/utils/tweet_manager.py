import asyncio
import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import List, Union

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import Boolean, DATETIME
from sqlalchemy.types import VARCHAR, BigInteger

from .db import engine

Base = declarative_base()


@dataclass
class TweetParameter:
    message_id: int
    channel_id: int
    author_id: int
    created_at: datetime = dataclasses.field(
        default_factory=datetime.now, init=False)
    content: str


class TweetObj(Base):
    __tablename__ = 'tweetqueue'

    message_id = Column(BigInteger, primary_key=True)  # メッセージID
    channel_id = Column(BigInteger, nullable=False)  # チャンネルID
    author_id = Column(BigInteger, nullable=False)  # 集めてる人のID
    created_at = Column(DATETIME, nullable=False)  # 集計開始時間
    content = Column(VARCHAR, default='')  # 内容


class TweetManager():

    @staticmethod
    def return_dataclass(db_data: TweetObj) -> TweetParameter:
        """DBからの情報をデータクラスに変換する関数、もうちょっとなんとかならんか？？？

        Args:
            db_data (sqlalchemyの): DBから取り出したデータ

        Returns:
            TweetParameter: データクラス
        """

        db_data_raw = TweetParameter(
            message_id=db_data[0].message_id,
            author_id=db_data[0].author_id,
            channel_id=db_data[0].channel_id,
            content=db_data[0].content)
        return db_data_raw

    async def create_table(self):
        async with engine.begin() as conn:
            await conn.run_sync(TweetObj.metadata.create_all)

    async def register_tweetdata(self, data: TweetParameter) -> None:
        """ツイートのキューを登録するコマンド

        Args:
            data (TweetParameter): ツイートのデータ
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                new_queue = TweetObj(
                    message_id=data.message_id,
                    author_id=data.author_id,
                    channel_id=data.channel_id,
                    created_at=data.created_at,
                    content=data.content)

                session.add(new_queue)

    async def get_tweetdata(self, message_id: int) -> Union[None, TweetParameter]:
        """メッセージIDからキューの情報を返す関数

        Args:
            message_id (int): 対象のメッセージID

        Returns:
            Union[None, TweetParameter]: あれば情報、なければNone
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(TweetObj).where(
                    TweetObj.message_id == message_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is None:
                    return None
                else:
                    return self.return_dataclass(result)

    async def remove_tweetdata(self, message_id: int) -> None:
        """キューを削除するコマンド

        Args:
            message_id (int): メッセージID
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = delete(TweetObj).where(
                    TweetObj.message_id == message_id)
                await session.execute(stmt)

    async def get_all_tweetdata(self) -> Union[None, List[TweetParameter]]:
        """すべてのキューを取得する関数

        Returns:
            Union[None, List[TweetParameter]]: なければNone、あったらリスト
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(TweetObj)
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [self.return_dataclass(poll)
                          for poll in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def is_exist(self, message_id: int) -> bool:
        """引数のメッセージIDが待機中かを判定する関数

        Args:
            guild_id (int): サーバーID

        Returns:
            bool: あったらTrue、なかったらFalse
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(TweetObj).where(
                    TweetObj.message_id == message_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is not None:
                    return True
                else:
                    return False


if __name__ == "__main__":
    polling_mng = TweetManager()
    result = asyncio.run(polling_mng.create_table())

    now = datetime.now()

    test = TweetParameter(
        message_id=12334,
        channel_id=123,
        author_id=123,
        content='hoge')
    print(asyncio.run(polling_mng.register_tweetdata(test)))

    # for i in result:
    #    print(i)

    # asyncio.run(guild_mng.register_setting())

    # asyncio.run(reaction_mng.all_guild_id())

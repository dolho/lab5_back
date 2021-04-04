from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, UniqueConstraint, TIMESTAMP
from sqlalchemy.orm import relationship
from .session_maker import Base


class User(Base):
    __tablename__ = "Users"

    login = Column(String, primary_key=True, index=True)
    telegram_login = Column(String)
    current_chat = Column(String, ForeignKey("ChatRooms.name"), nullable=True,)
    telegram_chat_id = Column(BigInteger, nullable=True)
    __table_args__ = (UniqueConstraint('login', 'telegram_login'),)

    def __init__(self, login, telegram_login):
        self.login = login
        self.telegram_login = telegram_login

class ChatRoom(Base):
    __tablename__ = "ChatRooms"

    name = Column(String, primary_key=True, index=True, onupdate='cascade')
    owner_login = Column(BigInteger, ForeignKey("Users.login"))

    def __init__(self, name, owner_login):
        self.name = name
        self.owner_login = owner_login


class Messages(Base):
    __tablename__ = "Messages"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP, nullable=False)
    author = Column(BigInteger, ForeignKey("Users.login"))
    text = Column(String, nullable=False)
    chat_room = Column(String, ForeignKey("ChatRooms.name"))

    def __init__(self, timestamp, author, text, chat_room):
        self.timestamp = timestamp
        self.author = author
        self.text = text
        self.chat_room = chat_room

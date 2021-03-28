from .models import *
from sqlalchemy import exc
from datetime import datetime
from sqlalchemy.dialects import postgresql


class DataBaseHandler:

    def __init__(self, session):
        self._session = session
        # Clear db from old users chats and messages
        users = self._session.query(User).all()
        for i in users:
            i.current_chat = None
        # self._session.query(Messages).delete()
        self._session.commit()

    def add_user(self, login, telegram_login):
        """
        Tries to add user. If user already exists nothing happens.
        :param login:
        :param telegram_login:
        :return:
        """
        try:
            user = self._session.query(User).filter(User.login == login).all()
            if user:
                return True
            user = User(login, telegram_login)
            self._session.add(user)
            self._session.commit()
            return True
        except exc.IntegrityError or exc.PendingRollbackError:
            return True

    def add_or_update_user(self, login, telegram_login):
        """
        Tries to add user. If user already exists nothing happens.
        :param login:
        :param telegram_login:
        :return:
        """
        try:
            user = self._session.query(User).filter(User.login == login).first()
            if user:
                #print('telegram_login  inside db: ', telegram_login)
                user.telegram_login = telegram_login
                self._session.commit()
                return True
            user = User(login, telegram_login)
            self._session.add(user)
            self._session.commit()
            return True
        except exc.IntegrityError or exc.PendingRollbackError:
            return True

    def get_chat_rooms(self):
        chat_rooms = self._session.query(ChatRoom).all()
        return list(chat_rooms)

    def get_chat_room(self, room_name):
        chat_room = self._session.query(ChatRoom).filter(ChatRoom.name == room_name).first()
        return chat_room

    def join_chatroom(self, login, room_name):
        # q = self._session.query(ChatRoom).filter(ChatRoom.name == room_name)
        # str(q.statement.compile(dialect=postgresql.dialect()))
        # print(f'"{room_name}"')
        chat = self._session.query(ChatRoom).filter(ChatRoom.name == room_name).first()
        user = self._session.query(User).filter(User.login == login).first()
        # print(f'Inside db, {user}, {chat},')
        if chat:
            user.current_chat = room_name
            self._session.commit()
            return True
        else:
            return False

    def get_all_users_in_chatroom(self, room_name):
        users = self._session.query(User).filter(User.current_chat == room_name).all()
        return users

    def get_user(self, login):
        user = self._session.query(User).filter(User.login == login).first()
        return user

    def leave_room(self, login):
        user = self.get_user(login)
        user.current_chat = None
        self._session.commit()
        return True

    def post_message(self, login, message, chat_room):
        timestamp = datetime.now().isoformat()
        message = Messages(timestamp, login, message, chat_room)
        self._session.add(message)
        self._session.commit()
        return message

    def get_all_users_in_chatroom_except_one(self, room_name, login):
        users = self._session.query(User).filter(User.current_chat == room_name).\
                                          filter(User.login != login).all()
        return users

    def get_last_10_messages(self, room_name):
        messages = self._session.query(Messages).\
            filter(Messages.chat_room == room_name).\
            order_by(Messages.timestamp.desc()).limit(10)
        return messages

    def post_room(self, room_name, owner):
        try:
            room = self._session.query(ChatRoom).filter(ChatRoom.name == room_name).first()
            if room:
                return False
            new_room = ChatRoom(room_name, owner)
            self._session.add(new_room)
            self._session.commit()
            return new_room
        except exc.IntegrityError or exc.PendingRollbackError:
            return new_room

    def get_all_users(self):
        return self._session.query(User).all()

    def update_chat_room(self, old_name, new_name) -> bool:
        try:
            is_renaming_acceptable = self._session.query(ChatRoom).filter(ChatRoom.name == new_name).first()
            if is_renaming_acceptable:
                return False
            old_room = self._session.query(ChatRoom).filter(ChatRoom.name == old_name).first()
            old_room.name = new_name
            self._session.commit()
            return True
        except exc.IntegrityError or exc.PendingRollbackError:
            return True

    def delete_chat_room_if_owner(self, room_name, login):
        room = self._session.query(ChatRoom).filter(ChatRoom.name == room_name).first()
        if room.owner_login == login:
            self._session.delete(room)
            self._session.commit()
            return room
        return None

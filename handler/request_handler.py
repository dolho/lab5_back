import json
from fastapi import WebSocket
from .session_maker import SessionLocal
from .database_handler import DataBaseHandler
import jwt
from .config import Config
from .models import ChatRoom, Messages


SALT = Config.SALT


db = DataBaseHandler(SessionLocal())


class RequestHandler:

    def __init__(self, database: DataBaseHandler = db):
        self.ALLOWED_TYPE = {'get-token': self.get_token, 'get-rooms-list': self.get_rooms_list,
                             'join-room': self.join_room, 'leave-room': self.leave_room,
                             'get-members-list': self.get_chatroom_members, 'post-message': self.post_message,
                             'get-last-messages-list': self.get_last_messages_list, 'create-room': self.create_room,
                             'rename-room': self.rename_room, 'remove-room': self.delete_room}
        self.OUTPUT_TYPE_MAP = {'get-token': 'token', 'get-rooms-list': 'rooms-list',
                                'join-room': 'current-room-changed', 'leave-room':'current-room-changed',
                                'get-members-list': 'members-list', 'post-message': 'message-posted',
                                'get-last-messages-list': 'last-messages-list', 'create-room': 'room-created',
                                'rename-room': 'room-renamed', 'remove-room': 'room-removed'}
        self.BROADCAST_ROOM_MEMBERS = {'join-room': self.construct_member_joined, 'leave-room': self.construct_member_left,
                                       'post-message': '', 'create-room': '', 'update-room': '', 'rename-room': '',
                                       'remove-room': ''}
        self._db = database
        self.socket_token_pairs = []

    @staticmethod
    def construct_app_message(message_type: str, payload):
        """
        Constructs AppMessage with structure:
        {
          token: string,
          type: string,
          payload: any
        }
        :param message_type: string
        :param payload: Any
        :return:
        """
        return {'token': '', 'type': message_type, 'payload': payload}

    @staticmethod
    def construct_chat_room(chat_room: ChatRoom):
        """
        Constructs ChatRoom with structure:
        {
          name: string
          owner: string
        }
        :param chat_room:
        :return:
        """
        chat_room_dict = {'name': chat_room.name, 'owner': chat_room.owner_login}
        return chat_room_dict

    @staticmethod
    def construct_message(message: Messages):
        message_dict = {'timestamp': message.timestamp, 'author': message.author, 'text': message.text}
        return message_dict

    def router(self, data: str):
        """
        returns list of dicts with structure:
        [{'message_type': 'broad' or 'single', 'app_message': app_message}]
        :param data:
        :return:
        """
        resulting_messages = []
        try:
            app_message = json.loads(data)
            #print(app_message)
        except json.JSONDecodeError:
            return resulting_messages
        message_token = app_message.get('token')
        message_type = app_message.get('type')
        message_payload = app_message.get('payload')
        login_telegram = {'login': '', 'telegramLogin': ''}
        #We do this if, to work correctly, when user just asks for a token
        chatroom_before = ''
        if message_type != 'get-token':
            login_telegram = self.check_token(message_token)
            if not login_telegram:
                return resulting_messages
            usr = self.get_user(login_telegram['login'])
            chatroom_before = usr['current_chat']
        try:
            # print(self.ALLOWED_TYPE[message_type])
            payload = self.ALLOWED_TYPE[message_type](app_message, login_telegram['login'],
                                                      login_telegram['telegramLogin'])

        except KeyError:
            return resulting_messages
        if not payload:
            return None
        answer_to_user_who_asked = self.construct_app_message(self.OUTPUT_TYPE_MAP[message_type], payload)
       # print('Answer to user who asked: ', answer_to_user_who_asked)
        if message_type not in ['create-room', 'rename-room', 'remove-room']:
            resulting_messages.append({'message_type': 'broad', 'users': [login_telegram['login']], 'app_message': answer_to_user_who_asked})
        # Here we decide, should we broadcast message to users in the chatroom, or not

        if message_type in self.BROADCAST_ROOM_MEMBERS:
            broad = self.broad_message_router(login_telegram, chatroom_before, message_type, answer_to_user_who_asked)
           # print('broad:   ', broad)
            if broad is not None:
                resulting_messages.append(broad)
        # print(resulting_messages)
        return resulting_messages

    def broad_message_router(self, login_telegram, chatroom_before, message_type, message=''):
        initial_user = self.get_user(login_telegram['login'])
        chatroom_after = initial_user['current_chat']
        chat = ''
        broad_message = ''
        #print('Message type: ',message_type)
        if chatroom_after is not None:
            chat = chatroom_after
        else:
            chat = chatroom_before
        if message_type == 'post-message':
            users = self.get_all_users_in_chatroom_except_one(chat, login_telegram['login'])
            broad_message = message
        elif message_type == 'create-room':
            users = 'ALL'
            broad_message = message
        elif message_type == 'rename-room':
            users = 'ALL'
            broad_message = message
        elif message_type == 'remove-room':
            users = 'ALL'
            broad_message = message
        elif message_type in self.BROADCAST_ROOM_MEMBERS:
            # If we should notify other users about initial user actions
            users = self.get_all_users_in_chatroom(chat)
            broad_message = self.BROADCAST_ROOM_MEMBERS[message_type](login_telegram['login'])
        else:
            return None
        return {'message_type': 'broad', 'users': users,  'app_message': broad_message}

    def get_token(self, app_message, *args): #login, telegram_login
        """
        Creates token and save data about user in db
        :param app_message:
        :return:
        """
        # print('Inside get-token: ',app_message)
        payload = app_message.get('payload')
        if not payload:
            return None
        login = payload.get('login')
        telegram_login = payload.get('telegramLogin')
        # print('nes_login teleg', telegram_login)
        if not login:
            return None
        self._db.add_or_update_user(login, telegram_login)  # We have to ensure that user exists, change his telegram login if he have a new one or register him
        encoded = jwt.encode({'login': login, 'telegramLogin': telegram_login}, SALT, algorithm="HS256")
        return encoded

    def get_rooms_list(self, *args):
        # token_payload = self.check_token(app_message['token'])
        # if not token_payload:
        #     return None
        res = self._db.get_chat_rooms()
        chat_rooms = []
        for i in res:
            chat_rooms.append(RequestHandler.construct_chat_room(i))
        return chat_rooms

    @staticmethod
    def check_token(token):
        try:
            decoded_token = jwt.decode(token, Config.SALT, algorithms=["HS256"])
            return decoded_token
        except jwt.exceptions.InvalidTokenError as e:
            return None

    def join_room(self, app_message, login, telegram_login):
        # token_payload = self.check_token(app_message['token'])
        # if not token_payload:
        #     return None
        room_name = app_message['payload']
        res = self._db.join_chatroom(login, room_name)
        if res:
            room = self._db.get_chat_room(room_name)
            return self.construct_chat_room(room)

    def get_all_users_in_chatroom(self, chatroom_name):
        users = self._db.get_all_users_in_chatroom(chatroom_name)
        res = []
        for i in users:
            res.append(i.login)
        return res

    def get_all_users_in_chatroom_except_one(self, chatroom_name, login):
        users = self._db.get_all_users_in_chatroom_except_one(chatroom_name, login)
        res = []
        for i in users:
            res.append(i.login)
        return res

    def get_user(self, login):
        user = self._db.get_user(login)
        return {'login': user.login, 'telegram_login': user.telegram_login, 'current_chat': user.current_chat}

    # def leave_room(self, login):
    #

    def leave_room(self, app_message, login, telegram_login):
        is_left = self._db.leave_room(login)
        if is_left:
            return {'name': ' ', 'owner': ' '}

    def get_chatroom_members(self, app_message, *args):
        room_name = app_message['payload']
        users = self._db.get_all_users_in_chatroom(room_name)
        login_list = []
        for i in users:
            login_list.append(i.login)
        return login_list

    def post_message(self, app_message, login, telegram_login):
        user = self.get_user(login)
        message = self._db.post_message(login, app_message['payload'], user['current_chat'])
        message_dict = self.construct_message(message)
        return message_dict

    def get_last_messages_list(self, app_message, login='', telegram_login=''):
        room_name = app_message['payload']
        messages = self._db.get_last_10_messages(room_name)
        result = []
        for i in messages:
            result.append(self.construct_message(i))
        return result

    def create_room(self, app_message, login='', telegram_login=''):
        created_room = self._db.post_room(app_message['payload'].strip(), login)
        if created_room:
            return self.construct_chat_room(created_room)
        else:
            return None

    def rename_room(self, app_message, login='', telegram_login=''):
        payload = app_message['payload']
        old_name = payload['oldRoomName']
        new_name = payload['newRoomName']
        is_renamed = self._db.update_chat_room(old_name, new_name)
        if is_renamed:
            return payload
        else:
            return None

    def delete_room(self, app_message, login, telegram_login=''):
        room_name = app_message['payload']
        room = self._db.delete_chat_room_if_owner(room_name, login)
        if room:
            return self.construct_chat_room(room)
        return ''

    def is_telegram_login_registered(self, telegram_login, chat_id = 0) -> {}:
        user = self._db.is_telegram_login_registered(telegram_login, chat_id)
        if not user:
            return None
        return {'login': user.login, 'telegram_login': user.telegram_login,
                'current_chat': user.current_chat, 'telegram_chat_id': user.telegram_chat_id}

    def is_user_in_room(self, login='', telegram_login=''):
        return self._db.is_in_room(login, telegram_login)

    def is_user_in_given_room(self, login='', telegram_login='', room=''):
        return self._db.is_user_in_given_room(login, telegram_login, room)

    @staticmethod
    def construct_member_joined(login, *args, **kwargs):
        return {'token': '','type': 'member-joined', 'payload': login}

    @staticmethod
    def construct_member_left(login, *args, **kwargs):
        return {'token': '', 'type': 'member-left', 'payload': login}

    # def disconnect(self, websocket:  WebSocket):
    #     for i in enumerate(self.socket_token_pairs):
    #         # i == [index, (websocket, token)]
    #         if i[1][0] == websocket:
    #             self.socket_token_pairs.pop(i[0])
    #
    #     self.socket_token_pairs.remove((websocket,))
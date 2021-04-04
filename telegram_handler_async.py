import asyncio
from aiogram import Bot, Dispatcher, types
from handler.request_handler import RequestHandler
import concurrent.futures
from messages import MessageTypes, create_app_message
import datetime
import json

ADRESS = 'https://still-mesa-73593.herokuapp.com/'

class TelegramHandlerAsync:

    def __init__(self, token, request_handler: RequestHandler, websocket_manager, rpc_manager):
        self._token = token
        self.request_handler = request_handler
        self._users = {}  # [{user_login: chat_id}]
        self._telegram_login_token = {}  # user_telegram_login: token
        self._teleg_login_chat_room = {}
        self._rooms = []
        self.websocket_manager = websocket_manager
        self.rpc_manager = rpc_manager
        self._bot = Bot(token=self._token)
        self._login_telegram_login = {}

    async def start_handler(self, event: types.Message):
        loop = asyncio.get_running_loop()
        # await self.websocket_manager.broadcast('{"token": "", "type": "member-joined", "payload": "axel"}', ['somebody1'])
        telegram_login = event.from_user.username
        chat_id = event.chat.id
        user = self.request_handler.is_telegram_login_registered(telegram_login, chat_id)
        if user:
            self._login_telegram_login[user['login']] = user['telegram_login']
            self._teleg_login_chat_room[telegram_login] = {}
            # print('If worked')
            await self._bot.send_message(chat_id=chat_id, text="You are registered")
            msg_to_server = json.dumps(create_app_message('', MessageTypes.CLIENT_GET_TOKEN,
                                                        {'login': user['login'],
                                                        'telegramLogin': user['telegram_login']}))
            with concurrent.futures.ThreadPoolExecutor() as pool:
                server_response = await loop.run_in_executor(
                    pool, self.request_handler.router, msg_to_server)
            self._telegram_login_token[telegram_login] = server_response[0]['app_message']['payload']
            self._users[user['login']] = chat_id
            await self.get_rooms(event)
        else:
            await self._bot.send_message(chat_id=chat_id,
                                         text=f'You are not registered. Visit <a href="{ADRESS}" > {ADRESS} </a> to register. \n'
                                          f'Use /start again when you register ', parse_mode=types.ParseMode.HTML)

    async def get_rooms(self, event: types.Message):
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            rooms = await loop.run_in_executor(
                pool, self.request_handler.get_rooms_list)
        if not self._rooms:
            self._rooms = rooms
        rooms_names = []
        answer = ''
        i = 1
        for room in rooms:
            rooms_names.append(f'{i}) {room["name"]} \n')
            i += 1
        await self._bot.send_message(chat_id=event.chat.id, text=''.join(rooms_names))


    async def join_room(self, event: types.Message):
        loop = asyncio.get_running_loop()
        if not (event.from_user.username in self._telegram_login_token):
            await self._bot.send_message(event.chat.id, text="You are not logged in. Use /start command")
            return
        try:
            room_number = int(event.get_full_command()[1]) # returns (command, args)
            if room_number <= 0 or room_number > len(self._rooms):
                res = self._bot.send_message(chat_id=event.chat.id, text="Incorrect room number")
        except IndexError:
            await self._bot.send_message(chat_id=event.chat.id, text="No room number given")
            return
        except ValueError:
            await self._bot.send_message(chat_id=event.chat.id, text="Incorrect value for room number")
            return
        msg_to_server = json.dumps(create_app_message(self._telegram_login_token[event.from_user.username],
                                                       MessageTypes.CLIENT_JOIN_ROOM, self._rooms[room_number - 1]['name']))
        self._teleg_login_chat_room[event.from_user.username] = self._rooms[room_number - 1]
        with concurrent.futures.ThreadPoolExecutor() as pool:
            server_response = await loop.run_in_executor(
                pool, self.request_handler.router, msg_to_server)
        #loop = asyncio.get_running_loop()
        await self.notify_other_clients(server_response)
        await self.get_members(event, self._rooms[room_number - 1]['name'])
            # print('after websocket')

    async def notify_other_clients(self, server_response):
        if not server_response:
            return None
        for i in server_response:
            json_answer = json.dumps(i['app_message'], default=str)
            await self.websocket_manager.broadcast(json_answer, i['users'])
            self.rpc_manager.broadcat_to(json_answer, i['users'])
            await self.broadcast_to(i['app_message'], i['users'])

    async def get_members(self, event: types.Message, room_name = ''):
        loop = asyncio.get_running_loop()
        msg_to_server = json.dumps(create_app_message(self._telegram_login_token[event.from_user.username],
                                                      MessageTypes.CLIENT_GET_MEMBERS_LIST,
                                                      room_name))
        with concurrent.futures.ThreadPoolExecutor() as pool:
            server_response = await loop.run_in_executor(
                pool, self.request_handler.router, msg_to_server)
        res = self.view_router_response(server_response[0]['app_message'])
        await self._bot.send_message(chat_id=event.chat.id, text=res)


    async def broadcast_to(self, app_message, users):
        loop = asyncio.get_running_loop()
        if users == 'ALL':
            msg = self.view_router_response(app_message)
            for i in self._users:
                    if app_message['type'] == MessageTypes.SERVER_ROOM_REMOVED:
                        if i in self._login_telegram_login:
                            if self._teleg_login_chat_room[self._login_telegram_login[i]]['name'] == app_message['payload']['name']:
                                await self._bot.send_message(chat_id=self._users[i], text=msg)
                                self._teleg_login_chat_room[self._login_telegram_login[i]] = ''
                            elif self._teleg_login_chat_room[self._login_telegram_login[i]]['name'] == '':
                                await self._bot.send_message(chat_id=self._users[i], text=msg)
                                self._teleg_login_chat_room[self._login_telegram_login[i]] = ''
                        try:
                            self._rooms.remove(app_message['payload'])
                        except ValueError as e:
                            print(e)
                        # with concurrent.futures.ThreadPoolExecutor() as pool:
                        #     server_response = await loop.run_in_executor(
                        #         pool, self.request_handler.is_user_in_given_room, i, '', app_message['payload']['name'])
                        # if server_response:
                        #     msg = self.view_router_response(app_message)
                        #     await self._bot.send_message(chat_id=self._users[i], text=msg)
                        #     continue
                    elif app_message['type'] == MessageTypes.SERVER_ROOM_RENAMED:
                        try:
                            index = self._rooms.index(app_message['payload']['oldRoomName'])
                            self._rooms[index] = app_message['payload']['newRoomName']
                        except ValueError as e:
                            print(e)

                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            server_response = await loop.run_in_executor(
                                pool, self.request_handler.is_user_in_given_room, i, '', app_message['payload']['newRoomName'])
                        if server_response:
                            msg = self.view_router_response(app_message)
                            await self._bot.send_message(chat_id=self._users[i], text=msg)
                            continue
                    elif app_message['type'] == MessageTypes.SERVER_ROOM_CREATED:
                        self._rooms.append(app_message['payload'])
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            server_response = await loop.run_in_executor(
                                pool, self.request_handler.is_user_in_room, i, '')
                        if not server_response:
                            msg = self.view_router_response(app_message)
                            await self._bot.send_message(chat_id=self._users[i], text=msg)
                            continue
        else:
            for i in users:
                if i in self._users:
                    msg = self.view_router_response(app_message)
                    if not msg:
                        continue
                    await self._bot.send_message(chat_id=self._users[i], text=msg)

    async def send_message(self, event: types.Message):
        loop = asyncio.get_running_loop()
        telegram_login = event.from_user.username
        is_in_room = self.request_handler.is_user_in_room(telegram_login=telegram_login)
        print(event.get_full_command())
        msg_text = event.text
        if is_in_room:
            msg_to_server = json.dumps(create_app_message(self._telegram_login_token[telegram_login],
                                               MessageTypes.CLIENT_POST_MESSAGE, msg_text))
            with concurrent.futures.ThreadPoolExecutor() as pool:
                server_response = await loop.run_in_executor(
                    pool, self.request_handler.router, msg_to_server)
            await self.notify_other_clients(server_response)


    @staticmethod
    def view_router_response(app_message):
        if app_message['type'] == MessageTypes.SERVER_CURRENT_ROOM_CHANGED:
            if app_message["payload"] == '':
                return None
            return f'You joined the room {app_message["payload"]["name"]}'
        elif app_message['type'] == MessageTypes.SERVER_MEMBER_JOINED:
            return f'Member {app_message["payload"]} joined'
        elif app_message['type'] == MessageTypes.SERVER_MESSAGE_POSTED:
            message = app_message['payload']
            date_time_obj = datetime.datetime.fromisoformat(str(message['timestamp']))
            return f'[{message["author"]}][{date_time_obj.time()}]: {message["text"]}'
        elif app_message['type'] == MessageTypes.SERVER_MEMBERS_LIST:
            i = 1
            res = ['Members in this room: \n']
            for member in app_message['payload']:
                res.append(f'[{i}) {member}] \n')
            return ''.join(res)
        elif app_message['type'] == MessageTypes.SERVER_MEMBER_LEFT:
            return f'{app_message["payload"]} left the chat'
        elif app_message['type'] == MessageTypes.SERVER_ROOM_CREATED:
            return f'Room {app_message["payload"]["name"]} was created'
        elif app_message['type'] == MessageTypes.SERVER_ROOM_REMOVED:
            return f'Room {app_message["payload"]["name"]} was removed'
        elif app_message['type'] == MessageTypes.SERVER_ROOM_RENAMED:
            return f'Room {app_message["payload"]["oldRoomName"]} was renamed to {app_message["payload"]["newRoomName"]}'
        else:
            return None

    async def run_bot(self):
        try:
            disp = Dispatcher(bot=self._bot)
            disp.register_message_handler(self.start_handler, commands={"start", "restart"})
            disp.register_message_handler(self.get_rooms, commands={"rooms"})
            disp.register_message_handler(self.join_room, commands={"join"})
            disp.register_message_handler(self.send_message)
            await disp.start_polling()
        finally:
            await self._bot.close()


from typing import List
from fastapi import WebSocket
import asyncio

class ConnectionManagerWebsockets:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.socket_login_pairs = []
        self._user_message = {}
        self._queue_from_telegram = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def make_pair(self, websocket: WebSocket, token: str):
        self.socket_login_pairs.append([websocket, token])

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        for i in enumerate(self.socket_login_pairs):
            # i == [index, (websocket, token)]
            if i[1][0] == websocket:
                self.socket_login_pairs.pop(i[0])

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, to_whom: list):
        # print(message)
        # print(to_who)
        # print(self.socket_login_pairs)
        print(f'Websocket broadcast worked. Message: {message}. To whom: {to_whom}. ')
        # print()
        if to_whom == 'ALL':
            await self.broadcast_all(message)
        else:
            for socket_login in self.socket_login_pairs:
                if socket_login[1] in to_whom:
                    await socket_login[0].send_text(message)

    def add_message_to_user(self, login, message):
        usr = self._user_message.get(login)
        if usr:
            usr.append(message)
        else:
            self._user_message[login] = [message]

    async def send_messages_from_queue(self):
        while True:
            await asyncio.sleep(0.5)
            for i in self._queue_from_telegram:
                await self.broadcast(i['app_message'], i['users'])
            self._queue_from_telegram.clear()

    async def broadcast_all(self, message: str):
        # socket_login == [index, (websocket, token)]
        for socket_login in self.socket_login_pairs:
            await socket_login[0].send_text(message)

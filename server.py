from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
import asyncio
import concurrent.futures

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from os.path import dirname, join
from handler.request_handler import RequestHandler

import json

request_handler = RequestHandler()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

current_dir = dirname(__file__)  # this will be the location of the current .py file
templates = Jinja2Templates(directory=join(current_dir, 'templates'))


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.socket_login_pairs = []

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
        if to_whom == 'ALL':
            await self.broadcast_all(message)
        else:
            for socket_login in self.socket_login_pairs:
                if socket_login[1] in to_whom:
                    await socket_login[0].send_text(message)

    async def broadcast_all(self, message: str):
        # socket_login == [index, (websocket, token)]
        for socket_login in self.socket_login_pairs:
                await socket_login[0].send_text(message)

manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print(f'New conection. Connections overall {len(manager.active_connections)}')
    try:
        loop = asyncio.get_running_loop()
        while True:
            data = await websocket.receive_text()
            print(f'Data: {data}')
            with concurrent.futures.ThreadPoolExecutor() as pool:
                server_answers = await loop.run_in_executor(
                    pool, request_handler.router, data)
            if server_answers is None:
                continue
            for server_answer in server_answers:
                if not server_answer:
                    server_answer = ''
                    continue
                elif server_answer['app_message']['type'] == 'token':
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        login_telegram = await loop.run_in_executor(
                            pool, request_handler.check_token, server_answer['app_message']['payload'])
                    manager.make_pair(websocket, login_telegram['login'])
                print(f'Result: {server_answer}')
                json_answer = json.dumps(server_answer['app_message'], default=str)
                print('my answer:  ', json_answer)
                if server_answer['message_type'] == 'broad':
                    await manager.broadcast(json_answer, server_answer['users'])
                else:
                    await manager.send_personal_message(json_answer, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # await manager.broadcast(f"Client #1 left the chat")


#TODO Реализовать все методы, которые требуются протоколом
#TODO Реализовать телеграм клиент
#TODO (???) RPC
#TODO Установить асинхронный драйвер для базы данных
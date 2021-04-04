from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse


from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from os.path import dirname, join

from pydantic import BaseModel
from typing import Any

import asyncio
import concurrent.futures
import json

from handler.request_handler import RequestHandler
from connection_managers.connection_manager_rpc import ConnectionManagerRPC
from connection_managers.connection_manager_websockets import ConnectionManagerWebsockets
# from telegram.ext.dispatcher import run_async
# from telegram_handler import TelegramBotHandler
from telegram_handler_async import TelegramHandlerAsync

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')


class AppMessage(BaseModel):
    token: str
    type: str
    payload: Any

request_handler = RequestHandler()





app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")

current_dir = dirname(__file__)  # this will be the location of the current .py file
templates = Jinja2Templates(directory=join(current_dir, 'templates'))




manager = ConnectionManagerWebsockets()
manager_rpc = ConnectionManagerRPC()
manager_telegram = TelegramHandlerAsync(BOT_TOKEN, request_handler, manager, manager_rpc)
# telegram_handler = TelegramBotHandler(request_handler, BOT_TOKEN, manager, manager_rpc)





def convert_app_messages_to_json(app_message: AppMessage):
    res = {}
    res['token'] = app_message.token
    res['type'] = app_message.type
    res['payload'] = app_message.payload
    return json.dumps(res)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(manager_telegram.run_bot())




@app.post('/rpc', response_class=JSONResponse)
async def rpc_endpoint(req: Request, response: JSONResponse):
    loop = asyncio.get_running_loop()
    app_message = await req.json()
    # print(f'RPC request: {app_message} {type(app_message)}')
    # for key in app_message:
    #     print(key)

    if app_message['type'] == 'get-updates':
        messages = []
        i = 0
        with concurrent.futures.ThreadPoolExecutor() as pool:
            login_telegram = await loop.run_in_executor(
                pool, request_handler.check_token, app_message['token'])
        if not login_telegram:
            response.status_code = 403
            print('not login and telegram')
            return response
        while i < 30:
            messages = manager_rpc.get_user_messages(login_telegram['login'])
            # print('User have such messages: ', messages)
            if not messages:
                await asyncio.sleep(1)
                i += 1
            else:
                break
        return messages

    if app_message['type'] != 'get-token':
        with concurrent.futures.ThreadPoolExecutor() as pool:
            login_telegram = await loop.run_in_executor(
                pool, request_handler.check_token, app_message['token'])
            manager_rpc.add_user(login_telegram['login'])
    with concurrent.futures.ThreadPoolExecutor() as pool:
        server_answers = await loop.run_in_executor(
            pool, request_handler.router, json.dumps(app_message))

    for server_answer in server_answers:
        if not server_answer:
            server_answer = ''
            continue
        elif server_answer['app_message']['type'] == 'token':
            # with concurrent.futures.ThreadPoolExecutor() as pool:
            #     login_telegram = await loop.run_in_executor(
            #         pool, request_handler.check_token, server_answer['app_message']['payload'])
            # manager_rpc.add_message_to_user(login_telegram['login'], server_answer['app_message'])
            return server_answer['app_message']
        print(f'Result: {server_answer}')
        json_answer = json.dumps(server_answer['app_message'], default=str)
        if server_answer['message_type'] == 'broad':
            await manager.broadcast(json_answer, server_answer['users'])
            await manager_telegram.broadcast_to(server_answer['app_message'], server_answer['users'])
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool, manager_rpc.broadcat_to, json_answer, server_answer['users'])
        else:
            print('my answer:  ', json_answer)
            manager_rpc.add_message_to_user(login_telegram['login'], server_answer['app_message'])



@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    #loop = asyncio.get_running_loop()
    await manager.connect(websocket)
    # asyncio.create_task(manager.send_messages_from_queue())# ???
    loop = asyncio.get_running_loop()
    # telegram_handler.loop = loop
    print(f'New conection. Connections overall {len(manager.active_connections)}')
    try:

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
                if server_answer['app_message']['type'] == 'token':
                    await manager.send_personal_message(json_answer, websocket)
                    break
                print('my answer:  ', json_answer)
                if server_answer['message_type'] == 'broad':
                    await manager.broadcast(json_answer, server_answer['users'])
                    await manager_telegram.broadcast_to(server_answer['app_message'], server_answer['users'])
                    # Send message to rpc users
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        loop.run_in_executor(
                            pool, manager_rpc.broadcat_to, json_answer, server_answer['users'])

                else:
                    await manager.send_personal_message(json_answer, websocket)
    except WebSocketDisconnect as e:
        manager.disconnect(websocket)
        # await manager.broadcast(f"Client #1 left the chat")


#TODO Реализовать все методы, которые требуются протоколом (сделано)
#TODO Реализовать телеграм клиент
#TODO (???) RPC (сделано все, кроме добавления-удаления-переименования комнат)

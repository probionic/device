from typing import List
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import random
import asyncio
import serial

app = FastAPI()
BAUDRATE = 38400
NUM_OF_USB_PORTS = 4
NUM_OF_DATA_POINTS = 150


def get_serial():
    for port in range(NUM_OF_USB_PORTS):
        try:
            ser = serial.Serial('/dev/ttyUSB{}'.format(port), BAUDRATE)
        except serial.serialutil.SerialException:
            continue
        return ser
    return False


SERIAL = get_serial()


async def get_serial_data(data):
    if not data:
        data =[0 for idx in range(NUM_OF_DATA_POINTS)]
        try:
            SERIAL.flushInput()
            data[-1] = [float(SERIAL.readline()[:-2])]
        except ValueError:
            data[-1] = [0]
        return data
    try:
        data.append(float(SERIAL.readline()[:-2]))
    except ValueError:
        data.append(0)
    return data[1:]


def get_rand(data, labels):
    if not data:
        labels = ['{} s'.format(nbr/10) for nbr in range(150)]
        data =[random.randint(0, 60) for idx in range(150)]
        return data, labels
    data.append(random.randint(0, 60))
    last = float(labels[-1][:-2])
    labels.append('{:.1f} s'.format(last + 0.1))
    return data[1:], labels[1:]

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    data = []
    labels = []
    try:
        while True:
            data = await get_serial_data(data)
            await manager.send_personal_message(data, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} socket was disconnected.")


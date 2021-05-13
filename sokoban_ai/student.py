import asyncio
import json
import os
import sys
import websockets
from mapa import Map
from AISokobanSolver import *

async def solver(map_queue, solver_queue):
    while True:
        game_properties = await map_queue.get()
        mapa = Map(game_properties["map"])

        t = TreeSearch(mapa, game_properties['map'])

        while True:
            await asyncio.sleep(0)
            break
        
        keys = await t.search()
        
        await solver_queue.put(keys)


async def agent_loop(map_queue, solver_queue, server_address="localhost:8000", agent_name="student"):
    async with websockets.connect(f"ws://{server_address}/player") as websocket:

        # Receive information about static game properties
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))
        
        while True:
            try:
                update = json.loads(
                    await websocket.recv()
                )

                if "map" in update:
                    # new level
                    game_properties = update
                    keys = ""
                    await map_queue.put(game_properties)

                if not solver_queue.empty():
                    keys = await solver_queue.get()

                key = ""

                if len(keys):
                    key = keys[0]
                    keys = keys[1:]

                await websocket.send(
                    json.dumps({"cmd": "key", "key": key})
                )

            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                sys.exit()


# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = "daniel_mario"

map_queue = asyncio.Queue(loop=loop)
solver_queue = asyncio.Queue(loop=loop)

net_task = loop.create_task(agent_loop(map_queue, solver_queue, f"{SERVER}:{PORT}", NAME))
solver_task = loop.create_task(solver(map_queue, solver_queue))

loop.run_until_complete(asyncio.gather(net_task, solver_task))
loop.close()
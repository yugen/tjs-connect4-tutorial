import os
import signal
import asyncio
import websockets
import json
import logging
import secrets

from connect4 import PLAYER1, PLAYER2, Connect4

logging.basicConfig(format="%(message)s", level=logging.DEBUG)

JOIN = {}
WATCH = {}

async def error(websocket, message):
    event = {"type": "error", "message": message}
    await websocket.send(json.dumps(event))

async def replay(websocket, game):
    for player, column, row in game.moves.copy():
        logging.debug(f"play back {len(game.moves)} moves: {json.dumps({'type': 'play', 'player': player, 'column': column, 'row': row})} to {id(game)}")
        event = {
            "type": "play",
            "player": player,
            "column": column,
            "row": row,
        }
        await websocket.send(json.dumps(event))
    

async def join(websocket, join_key):
    try:
        game, connected = JOIN[join_key]
    except KeyError:
        await error(websocket, "Game not found")
        return
    
    connected.add(websocket)
    try:
        logging.debug(f"Player joined game {id(game)}")
        await replay(websocket, game)
        await play(websocket, game, PLAYER2, connected)
    finally:
        connected.remove(websocket)
        logging.debug(f"Player 2 left game {id(game)}")

async def start(websocket):
    game = Connect4()
    connected = {websocket}

    join_key = secrets.token_urlsafe(12)
    watch_key = secrets.token_urlsafe(12)
    logging.debug(f"Game {id(game)} started with join key {join_key} and watch key {watch_key}")
    JOIN[join_key] = game, connected
    WATCH[watch_key] = game, connected

    try:
        event = {"type": "init", "join": join_key, "watch": watch_key}
        await websocket.send(json.dumps(event))
        logging.debug(f"first player started game {id(game)}")
        await play(websocket, game, PLAYER1, connected)
    finally:
        del JOIN[join_key]
        logging.debug(f"first player left game {id(game)}")

async def play(websocket, game, player, connected):
    async for message in websocket:
        data = json.loads(message)

        assert data['type'] == "play"
        
        try:
            row = game.play(player, data['column'])


        except RuntimeError as e:
            await websocket.send(json.dumps({"type": "error", "message": str(e)}))
            continue

        event = {
            "type": "play", 
            "player": player,
            "column": data['column'],
            "row": row,
        }
        for connection in connected:
            logging.debug(f"Sending {event} to {id(game)} for {connection} (player {player})")
            await connection.send(json.dumps(event))

        if game.winner is not None:
            event = {"type": "win", "player": game.winner}
            for connection in connected:
                await connection.send(json.dumps(event))

async def watch(websocket, watch_key):
    try:
        game, connected = WATCH[watch_key]
        logging.debug(f"watcher joining game {id(game)}, with {len(connected)} connected")
    except KeyError:
        await error(websocket, "Game not found")
        return
    
    connected.add(websocket)
    logging.debug(f"Added watcher to game {id(game)} with watch key {watch_key}")

    await replay(websocket, game)
    await play(websocket, game, PLAYER1, connected)
        
async def handler(websocket):
    message = await websocket.recv()
    event = json.loads(message)
    logging.debug(f"event_type: {event['type']} received")
    if "join" in event:
        await join(websocket, event["join"])
    if "watch" in event:
        await watch(websocket, event["watch"])
    else: 
        # Can I get rid of the else clause or does that kill the connection?
        await start(websocket)


async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    
    port = int(os.environ.get("PORT", "8001"))
    async with websockets.serve(handler, "", port):
        await stop

if __name__ == "__main__":
    asyncio.run(main())


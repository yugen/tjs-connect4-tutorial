import {createBoard, playMove} from './connect4.js';

function isWatcher() {
    const params = new URLSearchParams(window.location.search);
    return params.has("watch");
}

function sendEvent(websocket, type, data = {}) {
    const event = {type, ...data};
    websocket.send(JSON.stringify(event));
}

function startNewGame(websocket) {
    console.log("starting a new game");
    sendEvent(websocket, "init");
}

function joinGame(websocket, join) {
    console.log(`joining game ${join}`);
    sendEvent(websocket, "join", {join});
}

function watchGame(websocket, watch) {
    console.log(`watching game ${watch}`);
    sendEvent(websocket, "watch", {watch});
}

function initGame(websocket) {
    console.log("initializing game")
    websocket.addEventListener("open", () => {
        console.log("Connected to server")
        const params = new URLSearchParams(window.location.search);
        console.log("params", Array.from(params));
        
        if (params.has("join")) {
            console.log("--> join")
            joinGame(websocket, params.get("join"));
            return;
        }

        if (params.has("watch")) {
            console.log("--> watch")
            watchGame(websocket, params.get("watch"))
            return;
        }

        console.log("--> start")
        startNewGame(websocket);
    });
}

function sendMoves(board, websocket) {
    console.log("sending moves")
    board.addEventListener("click", ({target}) => {
        const column = target.dataset.column;

        if (column === undefined) {
            return;
        }

        const move = {column: parseInt(column, 10)}
        console.log(`playing move: ${move.column}`)

        sendEvent(websocket, "play", move);
    })
}

function showMessage(message) {
    window.setTimeout(() => window.alert(message), 50);
}

function receiveMoves(board, websocket) {
    websocket.addEventListener("message", ({data}) => {
        const event = JSON.parse(data);
        console.log("received message", event)
        switch (event.type) {
            case "init":
                document.querySelector(".join").href = `?join=${event.join}`
                document.querySelector(".watch").href = `?watch=${event.watch}`
                break;
            case "play":
                playMove(board, event.player, event.column, event.row);
                break;
            case "win":
                showMessage(`Player ${event.player} wins!`);
                break;
            case "error":
                showMessage(event.message);
                break;
            default:
                throw new Error(`Unknown event type: ${event.type}`);
        }
    })
}

function setupForWatcher() {
    console.log("setting up for watcher")
    document.querySelector(".board").classList.add("watcher");
}

window.addEventListener("DOMContentLoaded", () => {
    const board = document.querySelector(".board");
    createBoard(board);

    const websocket = new WebSocket("ws://localhost:8001");
    initGame(websocket);
    receiveMoves(board, websocket);
    
    if (isWatcher()) {
        setupForWatcher();
        return;
    }
    
    sendMoves(board, websocket);
});
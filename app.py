import string
import random
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from socketio import ASGIApp, AsyncServer
from starlette.middleware.sessions import SessionMiddleware

from models import Game, Room, Player
from threading import Lock

# Socket.IOサーバーの初期化
sio = AsyncServer(async_mode='asgi')
app = FastAPI()

# セッションミドルウェアの追加（必要に応じて）
app.add_middleware(SessionMiddleware, secret_key='secret!')

# Socket.IOアプリをASGIアプリとして統合
sio_app = ASGIApp(sio, other_asgi_app=app)

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="static"), name="static")

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

# グローバルに部屋を管理する辞書
rooms_dict = {}
lock = Lock()

def generate_room_code(length=6):
    """ランダムな部屋コードを生成"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Socket.IOイベントハンドラー

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('game_state', {'message': 'Connected'}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    # プレイヤーの削除や他のクリーンアップ処理をここに追加可能

@sio.event
async def create_room(sid, data):
    player_name = data.get('player_name')
    if not player_name:
        await sio.emit('error', {'message': 'Player name is required'}, room=sid)
        return

    room_code = generate_room_code()
    with lock:
        new_room = Room(room_code)
        rooms_dict[room_code] = new_room

    player = Player(sid, player_name)
    await sio.emit('room_created', {'room_code': room_code}, room=sid)

    # プレイヤーを部屋に追加
    async with sio.session(sid):
        new_room.add_player(player)
        sio.enter_room(sid, room_code)
        await sio.emit('room_joined', {'room_code': room_code}, room=room_code)

        # 4人揃ったらゲーム開始
        if new_room.is_full():
            new_room.start_game()
            await sio.emit('game_started', room=room_code)
            current_player = new_room.game.get_current_player()
            await sio.emit('turn', {'player_id': current_player.sid}, room=room_code)
            await start_turn_timer(room_code, current_player.sid)

@sio.event
async def join_room_event(sid, data):
    room_code = data.get('room_code')
    player_name = data.get('player_name')
    if not player_name or not room_code:
        await sio.emit('error', {'message': 'Player name and room code are required'}, room=sid)
        return

    room = rooms_dict.get(room_code)
    if not room:
        await sio.emit('error', {'message': 'Invalid room code'}, room=sid)
        return

    if room.is_full():
        await sio.emit('error', {'message': 'Room is full'}, room=sid)
        return

    player = Player(sid, player_name)
    room.add_player(player)
    sio.enter_room(sid, room_code)
    await sio.emit('room_joined', {'room_code': room_code}, room=sid)

    if room.is_full():
        room.start_game()
        await sio.emit('game_started', room=room_code)
        current_player = room.game.get_current_player()
        await sio.emit('turn', {'player_id': current_player.sid}, room=room_code)
        await start_turn_timer(room_code, current_player.sid)

@sio.event
async def join_random(sid, data):
    player_name = data.get('player_name')
    if not player_name:
        await sio.emit('error', {'message': 'Player name is required'}, room=sid)
        return

    # 空いている部屋を探す
    for room_code, room in rooms_dict.items():
        if not room.is_full() and not room.game.started:
            player = Player(sid, player_name)
            room.add_player(player)
            sio.enter_room(sid, room_code)
            await sio.emit('room_joined', {'room_code': room_code}, room=sid)

            if room.is_full():
                room.start_game()
                await sio.emit('game_started', room=room_code)
                current_player = room.game.get_current_player()
                await sio.emit('turn', {'player_id': current_player.sid}, room=room_code)
                await start_turn_timer(room_code, current_player.sid)
            return

    # 空いている部屋がなければ新しい部屋を作成
    room_code = generate_room_code()
    with lock:
        new_room = Room(room_code)
        rooms_dict[room_code] = new_room

    player = Player(sid, player_name)
    new_room.add_player(player)
    sio.enter_room(sid, room_code)
    await sio.emit('room_created', {'room_code': room_code}, room=sid)
    await sio.emit('room_joined', {'room_code': room_code}, room=sid)

@sio.event
async def action(sid, data):
    room_code = data.get('room_code')
    action = data.get('action')
    if not room_code or not action:
        await sio.emit('error', {'message': 'Room code and action are required'}, room=sid)
        return

    room = rooms_dict.get(room_code)
    if not room or not room.game.started:
        await sio.emit('error', {'message': 'Game not started or invalid room'}, room=sid)
        return

    game = room.game
    player = room.get_player(sid)
    if not player:
        await sio.emit('error', {'message': 'Player not found in room'}, room=sid)
        return

    if game.current_player != player:
        await sio.emit('error', {'message': 'Not your turn'}, room=sid)
        return

    if action not in ['ron', 'tsumo', 'reach', 'naki']:
        await sio.emit('error', {'message': 'Invalid action'}, room=sid)
        return

    game.process_action(action, player)
    await sio.emit('game_state', game.get_state(), room=room_code)

    # 次のプレイヤーにターンを移動
    next_player = game.next_turn()
    await sio.emit('turn', {'player_id': next_player.sid}, room=room_code)
    await start_turn_timer(room_code, next_player.sid)

@sio.event
async def player_left(sid):
    # プレイヤーが退出した場合の処理
    for room_code, room in list(rooms_dict.items()):
        player = room.get_player(sid)
        if player:
            room.remove_player(player)
            sio.leave_room(sid, room_code)
            await sio.emit('player_left', {'player_id': sid}, room=room_code)
            if len(room.players) < 2 and room.game.started:
                await sio.emit('game_ended', {'message': 'Not enough players'}, room=room_code)
                room.end_game()
            if room.is_empty():
                del rooms_dict[room_code]
            break

# タイマー管理の開始
async def start_turn_timer(room_code, player_sid):
    room = rooms_dict.get(room_code)
    if not room:
        return
    game = room.game
    player = room.get_player(player_sid)
    if not player:
        return

    while game.started and game.current_player.sid == player_sid:
        await sio.sleep(1)
        game.decrement_time(player)
        await sio.emit('game_state', game.get_state(), room=room_code)
        if player.remaining_time <= 0:
            # タイムオーバー、ツモ切り
            game.process_action('tsumo', player)
            await sio.emit('game_state', game.get_state(), room=room_code)
            # 次のプレイヤーへ
            next_player = game.next_turn()
            await sio.emit('turn', {'player_id': next_player.sid}, room=room_code)
            await start_turn_timer(room_code, next_player.sid)
            break

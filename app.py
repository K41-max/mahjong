import string
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import eventlet
from models import Game, Room, Player
from threading import Lock

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')
thread = None
thread_lock = Lock()

# グローバルに部屋を管理する辞書
rooms_dict = {}

def generate_room_code(length=6):
    """ランダムな部屋コードを生成"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_room')
def handle_create_room(data):
    player_name = data.get('player_name')
    room_code = generate_room_code()
    new_room = Room(room_code)
    rooms_dict[room_code] = new_room
    player = Player(request.sid, player_name)
    new_room.add_player(player)
    join_room(room_code)
    emit('room_created', {'room_code': room_code}, room=request.sid)

@socketio.on('join_room')
def handle_join_room(data):
    room_code = data.get('room_code')
    player_name = data.get('player_name')
    room = rooms_dict.get(room_code)
    if room and not room.is_full():
        player = Player(request.sid, player_name)
        room.add_player(player)
        join_room(room_code)
        emit('room_joined', {'room_code': room_code}, room=request.sid)
        # 全員が揃ったらゲームを開始
        if room.is_full():
            room.start_game()
            socketio.emit('game_started', room=room_code)
            # 開始時に最初のプレイヤーのターンを設定
            current_player = room.game.get_current_player()
            socketio.emit('turn', {'player_id': current_player.sid}, room=room_code)
            # タイマー開始
            start_turn_timer(room_code, current_player.sid)
    else:
        emit('error', {'message': 'Invalid room code or room is full'}, room=request.sid)

@socketio.on('join_random')
def handle_join_random(data):
    player_name = data.get('player_name')
    # 空いている部屋を探す
    for room_code, room in rooms_dict.items():
        if not room.is_full() and not room.game.started:
            player = Player(request.sid, player_name)
            room.add_player(player)
            join_room(room_code)
            emit('room_joined', {'room_code': room_code}, room=request.sid)
            # 全員が揃ったらゲームを開始
            if room.is_full():
                room.start_game()
                socketio.emit('game_started', room=room_code)
                # 開始時に最初のプレイヤーのターンを設定
                current_player = room.game.get_current_player()
                socketio.emit('turn', {'player_id': current_player.sid}, room=room_code)
                # タイマー開始
                start_turn_timer(room_code, current_player.sid)
            return
    # 空いている部屋がなければ新しい部屋を作成
    room_code = generate_room_code()
    new_room = Room(room_code)
    rooms_dict[room_code] = new_room
    player = Player(request.sid, player_name)
    new_room.add_player(player)
    join_room(room_code)
    emit('room_created', {'room_code': room_code}, room=request.sid)

@socketio.on('action')
def handle_action(data):
    room_code = data.get('room_code')
    action = data.get('action')
    room = rooms_dict.get(room_code)
    if not room or not room.game.started:
        emit('error', {'message': 'Game not started or invalid room'}, room=request.sid)
        return
    game = room.game
    player = room.get_player(request.sid)
    if game.current_player != player:
        emit('error', {'message': 'Not your turn'}, room=request.sid)
        return
    # 假设处理动作的逻辑
    if action in ['ron', 'tsumo', 'reach', 'naki']:
        game.process_action(action, player)
        socketio.emit('game_state', game.get_state(), room=room_code)
        # 移到下一个玩家
        next_player = game.next_turn()
        socketio.emit('turn', {'player_id': next_player.sid}, room=room_code)
        # 重置タイマー
        start_turn_timer(room_code, next_player.sid)
    else:
        emit('error', {'message': 'Invalid action'}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    # プレイヤーが切断した場合の処理
    for room_code, room in list(rooms_dict.items()):
        player = room.get_player(request.sid)
        if player:
            room.remove_player(player)
            leave_room(room_code)
            socketio.emit('player_left', {'player_id': request.sid}, room=room_code)
            # ゲームを終了するか、他のプレイヤーに通知
            if len(room.players) < 2 and room.game.started:
                socketio.emit('game_ended', {'message': 'Not enough players'}, room=room_code)
                room.end_game()
            if room.is_empty():
                del rooms_dict[room_code]
            break

def start_turn_timer(room_code, player_sid):
    room = rooms_dict.get(room_code)
    if not room:
        return
    game = room.game
    player = room.get_player(player_sid)
    if not player:
        return

    def timer():
        if game.timer_thread_active:
            return  # 既にタイマーが動作中
        game.timer_thread_active = True
        while game.started and game.current_player.sid == player_sid:
            remaining = game.get_remaining_time()
            if remaining <= 0:
                # タイムオーバー、ツモ切り
                game.process_action('tsumo', player)
                socketio.emit('game_state', game.get_state(), room=room_code)
                # 次のプレイヤーへ
                next_player = game.next_turn()
                socketio.emit('turn', {'player_id': next_player.sid}, room=room_code)
                start_turn_timer(room_code, next_player.sid)
                break
            else:
                # 毎秒更新
                socketio.sleep(1)
                game.decrement_time()
        game.timer_thread_active = False

    socketio.start_background_task(timer)

if __name__ == '__main__':
    socketio.run(app, debug=True)

import time

class Player:
    def __init__(self, sid, name):
        self.sid = sid  # SocketIOセッションID
        self.name = name
        self.remaining_time = 25  # 初期持ち時間（20秒 + 5秒）

    def reset_time(self):
        self.remaining_time = 25  # 基本ルールに基づく

class Game:
    def __init__(self):
        self.players = []  # Playerオブジェクトのリスト
        self.current_player_index = 0
        self.started = False

    def add_player(self, player):
        if len(self.players) < 4:
            self.players.append(player)

    def remove_player(self, player):
        self.players = [p for p in self.players if p.sid != player.sid]

    def is_full(self):
        return len(self.players) == 4

    def start_game(self):
        self.started = True
        self.current_player_index = 0
        for player in self.players:
            player.reset_time()  # 各プレイヤーの持ち時間をリセット

    def get_current_player(self):
        if self.players:
            return self.players[self.current_player_index]
        return None

    def next_turn(self):
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        return self.get_current_player()

    def process_action(self, action, player):
        # アクションに基づいてゲーム状態を更新
        if action in ['tsumo', 'ron', 'reach', 'naki']:
            print(f'Player {player.name} performed {action}')
            # タイマーをリセットまたは更新
            self.update_timer(player, action)

    def update_timer(self, player, action):
        if action in ['tsumo', 'ron']:
            # ツモやロンの場合、次のプレイヤーに移動
            pass
        elif action == 'reach':
            # リーチの場合、追加のロジック
            pass
        elif action == 'naki':
            # 鳴きの場合、追加のロジック
            pass
        # タイマーをリセット
        player.reset_time()

    def get_state(self):
        return {
            'players': [{'sid': p.sid, 'name': p.name, 'remaining_time': p.remaining_time} for p in self.players],
            'current_player': self.get_current_player().sid if self.get_current_player() else None,
            'started': self.started
        }

    def decrement_time(self, player):
        player.remaining_time -= 1
        if player.remaining_time < 20:
            player.remaining_time += 5  # 残り時間が20秒を切ったら+5秒
        if player.remaining_time <= 0:
            # タイムオーバーの処理（自動ツモ切り）
            self.process_action('tsumo', player)

class Room:
    def __init__(self, code):
        self.code = code
        self.players = []  # Playerオブジェクトのリスト
        self.game = Game()

    def add_player(self, player):
        if len(self.players) < 4:
            self.players.append(player)
            self.game.add_player(player)

    def remove_player(self, player):
        self.players = [p for p in self.players if p.sid != player.sid]
        self.game.remove_player(player)

    def is_full(self):
        return len(self.players) == 4

    def is_empty(self):
        return len(self.players) == 0

    def start_game(self):
        self.game.start_game()

    def end_game(self):
        self.game.started = False

    def get_player(self, sid):
        for player in self.players:
            if player.sid == sid:
                return player
        return None

document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // ラビング要素
    const lobbyDiv = document.querySelector('.lobby');
    const createRoomBtn = document.getElementById('create-room-btn');
    const joinRoomBtn = document.getElementById('join-room-btn');
    const joinRandomBtn = document.getElementById('join-random-btn');

    // ゲーム要素
    const gameDiv = document.querySelector('.game');
    const roomCodeSpan = document.getElementById('room-code');
    const statusDiv = document.getElementById('status');
    const playersDiv = document.getElementById('players');
    const buttonsDiv = document.getElementById('buttons');
    const remainingTimeSpan = document.getElementById('remaining-time');

    let currentRoom = null;
    let currentPlayerId = null;
    let timerInterval = null;

    // 部屋の作成
    createRoomBtn.addEventListener('click', () => {
        const playerName = document.getElementById('create-player-name').value.trim();
        if (!playerName) {
            alert('名前を入力してください');
            return;
        }
        socket.emit('create_room', { player_name: playerName });
    });

    // 部屋への参加
    joinRoomBtn.addEventListener('click', () => {
        const playerName = document.getElementById('join-player-name').value.trim();
        const roomCode = document.getElementById('join-room-code').value.trim().toUpperCase();
        if (!playerName || !roomCode) {
            alert('名前と部屋コードを入力してください');
            return;
        }
        socket.emit('join_room_event', { player_name: playerName, room_code: roomCode });
    });

    // ランダム参加
    joinRandomBtn.addEventListener('click', () => {
        const playerName = document.getElementById('random-player-name').value.trim();
        if (!playerName) {
            alert('名前を入力してください');
            return;
        }
        socket.emit('join_random', { player_name: playerName });
    });

    // 部屋が作成されたとき
    socket.on('room_created', (data) => {
        currentRoom = data.room_code;
        roomCodeSpan.innerText = currentRoom;
        lobbyDiv.style.display = 'none';
        gameDiv.style.display = 'block';
        statusDiv.innerText = '他のプレイヤーを待っています...';
    });

    // 部屋に参加したとき
    socket.on('room_joined', (data) => {
        currentRoom = data.room_code;
        roomCodeSpan.innerText = currentRoom;
        lobbyDiv.style.display = 'none';
        gameDiv.style.display = 'block';
        statusDiv.innerText = '他のプレイヤーを待っています...';
    });

    // ゲームが開始されたとき
    socket.on('game_started', () => {
        statusDiv.innerText = 'ゲームが開始されました！';
        updatePlayersUI();
    });

    // ターンが渡されたとき
    socket.on('turn', (data) => {
        const playerId = data.player_id;
        currentPlayerId = playerId;
        if (playerId === socket.id) {
            statusDiv.innerText = 'あなたのターンです';
        } else {
            statusDiv.innerText = '他のプレイヤーのターンです';
        }
        updateButtons();
    });

    // ゲーム状態が更新されたとき
    socket.on('game_state', (data) => {
        updatePlayersUI(data.players);
    });

    // プレイヤーが退出したとき
    socket.on('player_left', (data) => {
        updatePlayersUI();
    });

    // ゲームが終了したとき
    socket.on('game_ended', (data) => {
        alert(data.message);
        resetUI();
    });

    // エラーが発生したとき
    socket.on('error', (data) => {
        alert(data.message);
    });

    // ゲームがリセットされたとき
    function resetUI() {
        gameDiv.style.display = 'none';
        lobbyDiv.style.display = 'block';
        roomCodeSpan.innerText = '';
        statusDiv.innerText = 'ゲーム開始待機中...';
        playersDiv.innerHTML = '';
        buttonsDiv.innerHTML = '';
        remainingTimeSpan.innerText = '--';
        clearInterval(timerInterval);
    }

    // プレイヤー情報を更新
    function updatePlayersUI(players = []) {
        if (!players.length) {
            // ゲーム状態からプレイヤー情報を取得するロジックを追加可能
            return;
        }
        playersDiv.innerHTML = '<h3>プレイヤー一覧:</h3>';
        players.forEach(player => {
            const playerDiv = document.createElement('div');
            playerDiv.classList.add('player');
            playerDiv.innerText = `${player.name} - 残り時間: ${player.remaining_time}秒`;
            playersDiv.appendChild(playerDiv);
            // 自分の残り時間を表示
            if (player.sid === socket.id) {
                remainingTimeSpan.innerText = player.remaining_time;
                clearInterval(timerInterval);
                timerInterval = setInterval(() => {
                    if (player.remaining_time > 0) {
                        remainingTimeSpan.innerText = player.remaining_time;
                    } else {
                        remainingTimeSpan.innerText = '0';
                        clearInterval(timerInterval);
                    }
                }, 1000);
            }
        });
    }

    // アクションボタンを更新
    function updateButtons() {
        buttonsDiv.innerHTML = '';
        if (currentPlayerId === socket.id) {
            const actions = ['ron', 'tsumo', 'reach', 'naki'];
            actions.forEach(action => {
                const button = document.createElement('button');
                button.innerText = actionToJapanese(action);
                button.addEventListener('click', () => {
                    socket.emit('action', { room_code: currentRoom, action: action });
                });
                buttonsDiv.appendChild(button);
            });
        } else {
            buttonsDiv.innerHTML = '<p>相手のターンです...</p>';
        }
    }

    // アクション名を日本語に変換
    function actionToJapanese(action) {
        switch(action) {
            case 'ron':
                return 'ロン';
            case 'tsumo':
                return 'ツモ';
            case 'reach':
                return 'リーチ';
            case 'naki':
                return '鳴き';
            default:
                return action;
        }
    }
});

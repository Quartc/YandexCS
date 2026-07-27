from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import SubmitField
from data import db_session
from data.user import User
from data.queue import Queue
from config import Config
from steam_auth import SteamAuth
import datetime
import threading
import time

app = Flask(__name__)
app.config.from_object(Config)

db_session.global_init('cs2_tournament.db')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.get(User, user_id)


class LogoutForm(FlaskForm):
    submit = SubmitField('Выйти')


class QueueForm(FlaskForm):
    join_queue = SubmitField('Встать в очередь')


class LeaveQueueForm(FlaskForm):
    leave_queue = SubmitField('Выйти из очереди')


queue_state = {
    'players': [],
    'match_players': [],
    'last_updated': None,
    'match_started': False
}


def get_queue_info():
    session = db_session.create_session()
    queue_entries = session.query(Queue).order_by(Queue.joined_at).all()
    players = []
    for entry in queue_entries:
        user = session.get(User, entry.user_id)
        if user:
            players.append({
                'id': entry.id,
                'user_id': user.id,
                'username': user.username,
                'steam_id_64': user.steam_id_64,
                'avatar_url': user.avatar_url,
                'joined_at': entry.joined_at,
                'is_in_match': entry.is_in_match
            })
    return players


def get_next_match_players(players):
    available = []
    for player in players:
        if not player['is_in_match']:
            available.append(player)
    return available[:Config.MATCH_PLAYERS]


@app.route('/')
@app.route('/index')
def index():
    players = get_queue_info()
    match_players = get_next_match_players(players)
    
    match_player_ids = []
    for player in match_players:
        match_player_ids.append(player['user_id'])
    
    for player in players:
        if player['user_id'] in match_player_ids:
            player['will_play'] = True
        else:
            player['will_play'] = False
    
    queue_form = QueueForm()
    leave_queue_form = LeaveQueueForm()
    logout_form = LogoutForm()
    
    is_in_queue = False
    if current_user.is_authenticated:
        for player in players:
            if player['user_id'] == current_user.id:
                is_in_queue = True
                break
    
    return render_template(
        'index.html',
        title='Чай?',
        players=players,
        max_queue=Config.MAX_QUEUE_SIZE,
        match_players=Config.MATCH_PLAYERS,
        queue_form=queue_form,
        leave_queue_form=leave_queue_form,
        logout_form=logout_form,
        is_in_queue=is_in_queue,
        match_started=queue_state.get('match_started', False)
    )


@app.route('/auth/steam')
def steam_login():
    redirect_uri = Config.STEAM_REDIRECT_URI
    login_url = SteamAuth.get_steam_login_url(redirect_uri)
    return redirect(login_url)


@app.route('/auth/steam/callback')
def steam_callback():
    steam_id_64 = SteamAuth.validate_steam_response()
    if not steam_id_64:
        flash('Ошибка авторизации через Steam', 'danger')
        return redirect(url_for('index'))
    
    player_info = SteamAuth.get_player_info(steam_id_64, Config.STEAM_API_KEY)
    if not player_info:
        flash('Не удалось получить информацию о пользователе', 'danger')
        return redirect(url_for('index'))
    
    session = db_session.create_session()
    user = session.query(User).filter(User.steam_id_64 == steam_id_64).first()
    
    if not user:
        user = User(
            steam_id=player_info['steam_id'],
            steam_id_64=player_info['steam_id_64'],
            username=player_info['username'],
            avatar_url=player_info['avatar_url'],
            profile_url=player_info['profile_url']
        )
        session.add(user)
        session.commit()
    
    login_user(user, remember=True)
    flash(f'Добро пожаловать, {user.username}!', 'success')
    return redirect(url_for('index'))


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/queue/join', methods=['POST'])
@login_required
def join_queue():
    session = db_session.create_session()
    
    existing = session.query(Queue).filter(Queue.user_id == current_user.id).first()
    if existing:
        flash('Вы уже в очереди', 'warning')
        return redirect(url_for('index'))
    
    count = session.query(Queue).count()
    if count >= Config.MAX_QUEUE_SIZE:
        flash('Очередь полностью заполнена', 'danger')
        return redirect(url_for('index'))
    
    queue_entry = Queue(user_id=current_user.id)
    session.add(queue_entry)
    session.commit()
    
    all_players = get_queue_info()
    available_players = []
    for player in all_players:
        if not player['is_in_match']:
            available_players.append(player)
    
    if len(available_players) >= Config.MATCH_PLAYERS:
        start_match()
    
    flash('Вы встали в очередь!', 'success')
    return redirect(url_for('index'))


@app.route('/queue/leave', methods=['POST'])
@login_required
def leave_queue():
    session = db_session.create_session()
    queue_entry = session.query(Queue).filter(Queue.user_id == current_user.id).first()
    
    if queue_entry:
        session.delete(queue_entry)
        session.commit()
        flash('Вы вышли из очереди', 'info')
    else:
        flash('Вас нет в очереди', 'warning')
    
    return redirect(url_for('index'))


def start_match():
    session = db_session.create_session()
    all_players = get_queue_info()
    
    available_players = []
    for player in all_players:
        if not player['is_in_match']:
            available_players.append(player)
    
    match_players = available_players[:Config.MATCH_PLAYERS]
    
    if len(match_players) < Config.MATCH_PLAYERS:
        return
    
    print("\n" + "=" * 60)
    print("🔥 НОВЫЙ МАТЧ НАЧИНАЕТСЯ! 🔥")
    print("=" * 60)
    print(f"Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Количество игроков: {len(match_players)}")
    print("-" * 60)
    print("Steam ID 64 игроков:")
    print("-" * 60)
    
    match_ids = []
    player_number = 1
    for player in match_players:
        print(f"{player_number}. {player['username']} (SteamID64: {player['steam_id_64']})")
        match_ids.append(player['user_id'])
        
        queue_entry = session.query(Queue).filter(
            Queue.user_id == player['user_id']
        ).first()
        if queue_entry:
            queue_entry.is_in_match = True
        
        player_number += 1
    
    print("-" * 60)
    steam_ids_str = ""
    for player in match_players:
        if steam_ids_str:
            steam_ids_str += ", "
        steam_ids_str += str(player['steam_id_64'])
    print(f"Всего Steam ID 64: {steam_ids_str}")
    print("=" * 60)
    print()
    
    session.commit()
    
    queue_state['match_started'] = True
    queue_state['match_players'] = match_players
    queue_state['last_updated'] = datetime.datetime.now()
    
    def clear_after_match():
        time.sleep(5)
        clear_match_players(match_ids)
    
    thread = threading.Thread(target=clear_after_match)
    thread.start()


def clear_match_players(match_ids):
    session = db_session.create_session()
    
    for user_id in match_ids:
        queue_entry = session.query(Queue).filter(Queue.user_id == user_id).first()
        if queue_entry:
            session.delete(queue_entry)
    
    session.commit()
    queue_state['match_started'] = False
    queue_state['match_players'] = []
    queue_state['last_updated'] = datetime.datetime.now()
    print("Матч завершен. Игроки удалены из очереди.")


@app.route('/api/queue_status')
def queue_status():
    players = get_queue_info()
    match_players = get_next_match_players(players)
    
    match_player_ids = []
    for player in match_players:
        match_player_ids.append(player['user_id'])
    
    players_data = []
    for player in players:
        joined_time = None
        if player['joined_at']:
            joined_time = player['joined_at'].strftime('%H:%M:%S')
        
        will_play = False
        if player['user_id'] in match_player_ids:
            will_play = True
        
        players_data.append({
            'username': player['username'],
            'avatar_url': player['avatar_url'],
            'joined_at': joined_time,
            'will_play': will_play,
            'is_in_match': player['is_in_match']
        })
    
    data = {
        'total': len(players),
        'max': Config.MAX_QUEUE_SIZE,
        'match_players': Config.MATCH_PLAYERS,
        'players': players_data,
        'match_started': queue_state['match_started']
    }
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
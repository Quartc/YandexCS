import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'yandexlyceum_secret_key_2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cs2_tournament.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STEAM_API_KEY = os.environ.get('STEAM_API_KEY') or '3C7EF4F9FA70FBA8A1A74F2E0EFC390B'
    STEAM_OPENID_URL = 'https://steamcommunity.com/openid/login'
    STEAM_REDIRECT_URI = 'http://localhost:5000/auth/steam/callback'
    MAX_QUEUE_SIZE = 20
    MATCH_PLAYERS = 10
import requests
from flask import request
from urllib.parse import urlencode
import re


class SteamAuth:
    OPENID_URL = 'https://steamcommunity.com/openid/login'

    @staticmethod
    def get_steam_login_url(redirect_uri):
        params = {
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.mode': 'checkid_setup',
            'openid.return_to': redirect_uri,
            'openid.realm': 'http://localhost:5000/',
            'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
        }
        return f"{SteamAuth.OPENID_URL}?{urlencode(params)}"

    @staticmethod
    def validate_steam_response():
        if 'openid.identity' not in request.args:
            return None
        identity_url = request.args.get('openid.identity', '')
        match = re.search(r'/id/(\d+)', identity_url)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def get_player_info(steam_id_64, api_key):
        url = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
        params = {'key': api_key, 'steamids': steam_id_64}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['response']['players']:
                    player = data['response']['players'][0]
                    return {
                        'steam_id': player['steamid'],
                        'username': player.get('personaname', 'Unknown'),
                        'avatar_url': player.get('avatar', ''),
                        'profile_url': player.get('profileurl', ''),
                        'steam_id_64': steam_id_64
                    }
        except Exception:
            pass
        return None
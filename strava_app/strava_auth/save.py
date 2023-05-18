import json

from social_django.models import UserSocialAuth

from config import DATABASE
from bot.utilities import db_execute


def save_strava_token(request, backend, user, *args, **kwargs):
    if backend.name == 'strava':
        user_social_auth = UserSocialAuth.objects.get(
            provider='strava', user=user
        )
        tokens = json.dumps(user_social_auth.extra_data)
        chat_id = request.session.get('chat_id')
        db_execute(
            DATABASE,
            (
                'UPDATE Students SET tokens = ? WHERE chat_id = ?',
                (tokens, chat_id),
            ),
        )

        del request.session['chat_id']

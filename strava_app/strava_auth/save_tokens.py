import json

import psycopg2
from social_django.models import UserSocialAuth

from strava_app.settings import DATABASE


def save_strava_token(request, backend, user, *args, **kwargs):
    if backend.name == 'strava':
        user_social_auth = UserSocialAuth.objects.get(
            provider='strava', user=user
        )
        tokens = json.dumps(user_social_auth.extra_data)
        chat_id = request.session.get('chat_id')
        execution = (
            'UPDATE students SET tokens = %s WHERE chat_id = %s',
            (tokens, chat_id),
        )

        with psycopg2.connect(**DATABASE) as conn:
            with conn.cursor() as cur:
                cur.execute(*execution)

        del request.session['chat_id']

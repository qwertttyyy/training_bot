from django.shortcuts import redirect


class StravaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path == '/login/strava/'
            and not request.GET.get('chat_id')
            and 'strava' in request.path
        ):
            return redirect('strava:forbidden')

        error = request.GET.get('error')

        if request.path == '/complete/strava/' and error == 'access_denied':
            return redirect('strava:canceled')

        response = self.get_response(request)
        request.session['chat_id'] = request.GET.get('chat_id')

        return response

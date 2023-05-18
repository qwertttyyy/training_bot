from django.shortcuts import redirect

url = 'http://127.0.0.1:8000/login/strava/?chat_id=123456'


class StravaLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path == '/login/strava/'
            and not request.GET.get('chat_id')
            and 'strava' in request.path
        ):
            return redirect('strava:forbidden')
        response = self.get_response(request)
        request.session['chat_id'] = request.GET.get('chat_id')
        return response


class StravaCompleteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        error = request.GET.get('error')
        if request.path == '/complete/strava/' and error == 'access_denied':
            return redirect('strava:canceled')
        response = self.get_response(request)
        return response

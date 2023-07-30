from django.shortcuts import redirect, render


def strava_login(request):
    chat_id = request.GET.get('chat_id')

    if not chat_id:
        return redirect('strava:forbidden')

    request.session['chat_id'] = chat_id
    return redirect('social:begin', 'strava')


def success_auth(request):
    return render(request, 'strava_auth/success.html')


def auth_forbidden(request):
    return render(request, 'strava_auth/forbidden.html')


def auth_canceled(request):
    return render(request, 'strava_auth/canceled.html')

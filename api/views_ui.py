from django.shortcuts import render


def swagger_ui(request):
    return render(request, 'api/swagger.html')

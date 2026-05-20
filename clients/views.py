from django.shortcuts import render

def client_list(request):
    return render(request, 'clients/list.html')
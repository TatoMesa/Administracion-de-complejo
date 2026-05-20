from django.shortcuts import render

def resource_list(request):
    return render(request, 'resources/list.html')
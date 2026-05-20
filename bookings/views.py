from django.shortcuts import render

def booking_list(request):
    return render(request, 'bookings/list.html')
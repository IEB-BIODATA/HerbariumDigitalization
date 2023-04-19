from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST


@require_POST
@login_required
def set_back_page(request):
    prev_page = request.POST.get('prev_page')
    request.session['prev_page'] = prev_page
    return HttpResponse('OK')

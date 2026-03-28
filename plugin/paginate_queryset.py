from django.core.paginator import Paginator


def paginate_queryset(request, queryset, per_page):
    paginator = Paginator(queryset, per_page)
    raw = request.GET.get("page")
    try:
        n = int(str(raw).strip()) if raw not in (None, "") else 1
    except (TypeError, ValueError):
        n = 1
    # Верхняя граница номера страницы (защита от огромных значений в URL)
    n = max(1, min(n, 10_000))
    return paginator.get_page(n)

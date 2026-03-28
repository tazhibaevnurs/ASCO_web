from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.html import strip_tags

from blog import models as blog_models
from plugin.input_validation import clamp_text, MAX_COMMENT_LEN
from plugin.paginate_queryset import paginate_queryset

def blog_list(request):
    blogs_list = blog_models.Blog.objects.all().order_by('-date') 
    blogs = paginate_queryset(request, blogs_list, 10)

    context = {
        'blogs': blogs,
        'blogs_list': blogs_list,
    }
    return render(request, 'blog/blog_list.html', context)

def blog_detail(request, slug):
    blog = get_object_or_404(blog_models.Blog, slug=slug) 
    comments = blog.comments.filter(approved=True)  

    liked = False
    if request.user.is_authenticated and blog.likes.filter(id=request.user.pk).exists():
        liked = True

    context = {
        'blog': blog,
        'comments': comments,
        'liked': liked,
        'total_likes': blog.total_likes(),
    }
    return render(request, 'blog/blog_detail.html', context)

def create_comment(request, slug):
    blog = get_object_or_404(blog_models.Blog, slug=slug)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    full_name = clamp_text(request.POST.get("full_name"), 200)
    email = clamp_text(request.POST.get("email"), 254)
    content_raw = request.POST.get("content") or ""
    content = strip_tags(content_raw)[:MAX_COMMENT_LEN]

    if not full_name or not email or not content.strip():
        messages.error(request, "Заполните имя, email и текст комментария.")
        return redirect("blog:blog_detail", slug=blog.slug)
    try:
        EmailValidator()(email)
    except ValidationError:
        messages.error(request, "Укажите корректный email.")
        return redirect("blog:blog_detail", slug=blog.slug)

    blog_models.Comment.objects.create(
        blog=blog,
        full_name=full_name,
        email=email,
        content=content.strip(),
    )
    messages.success(request, "Комментарий создан, ожидает модерации!")
    return redirect("blog:blog_detail", slug=blog.slug)

@login_required
def like_blog(request):
    if request.method != "POST":
        return redirect("blog:blog_list")

    raw = request.POST.get("blog_id")
    try:
        blog_pk = int(raw)
    except (TypeError, ValueError):
        messages.error(request, "Некорректный запрос.")
        return redirect("blog:blog_list")

    blog = get_object_or_404(blog_models.Blog, id=blog_pk)
    if blog.likes.filter(id=request.user.pk).exists():
        blog.likes.remove(request.user)
        liked = False
    else:
        blog.likes.add(request.user)
        liked = True

    context = {
        "total_likes": blog.total_likes(),
        "liked": liked,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(context)

    return redirect("blog:blog_detail", slug=blog.slug)
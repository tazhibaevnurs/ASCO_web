from django.db import models
from userauths import models as userauths_models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field
from django.utils import timezone
import re


def transliterate_cyrillic(text):
    """Простая транслитерация кириллицы в латиницу"""
    cyrillic_to_latin = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    }
    result = ''
    for char in text:
        result += cyrillic_to_latin.get(char, char)
    return result

STATUS_CHOICES = [
    ('Draft', 'Draft'),
    ('Published', 'Published'),
]


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)

    class Meta:
        ordering = ['-id']
        verbose_name_plural = "Категории блога"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Blog(models.Model):
    image = models.ImageField(upload_to='blog_images', blank=True, null=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=350, unique=True, blank=True)
    author = models.ForeignKey(userauths_models.User, on_delete=models.CASCADE)
    content = CKEditor5Field(config_name='extends', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    tags = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Published")
    likes = models.ManyToManyField(userauths_models.User, blank=True, related_name="likes")
    views = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']
        verbose_name_plural = "Блоги"

    def save(self, *args, **kwargs):
        if not self.slug or self.slug == '':
            # Генерируем slug из title, если title пустой, используем id
            if self.title:
                # Сначала транслитерируем кириллицу, затем создаем slug
                transliterated = transliterate_cyrillic(self.title)
                base_slug = slugify(transliterated)
                if not base_slug:  # Если все еще пусто, используем id
                    base_slug = f"blog-{self.id}" if self.id else "blog"
            else:
                base_slug = f"blog-{self.id}" if self.id else "blog"
            
            # Проверяем уникальность slug
            slug = base_slug
            counter = 1
            while Blog.objects.filter(slug=slug).exclude(pk=self.pk if self.pk else None).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.likes.all().count()


class Comment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="comments")
    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-id']
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f"Comment by {self.full_name} on {self.blog.title}"

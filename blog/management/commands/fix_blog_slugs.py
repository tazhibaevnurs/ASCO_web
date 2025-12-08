from django.core.management.base import BaseCommand
from blog.models import Blog, transliterate_cyrillic
from django.utils.text import slugify


class Command(BaseCommand):
    help = "Исправляет пустые slug у блогов"

    def handle(self, *args, **options):
        blogs_without_slug = Blog.objects.filter(slug__isnull=True) | Blog.objects.filter(slug='')
        
        fixed_count = 0
        for blog in blogs_without_slug:
            if blog.title:
                # Сначала транслитерируем кириллицу, затем создаем slug
                transliterated = transliterate_cyrillic(blog.title)
                base_slug = slugify(transliterated)
                
                # Если slugify вернул пустую строку
                if not base_slug:
                    # Используем id для создания slug
                    base_slug = f"blog-{blog.id}"
            else:
                # Если title тоже пустой, используем id
                base_slug = f"blog-{blog.id}"
            
            # Проверяем уникальность
            slug = base_slug
            counter = 1
            while Blog.objects.filter(slug=slug).exclude(pk=blog.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            blog.slug = slug
            blog.save(update_fields=['slug'])
            fixed_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Исправлен slug для блога "{blog.title}": {slug}')
            )
        
        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS('Все блоги уже имеют slug.'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nУспешно исправлено {fixed_count} блогов!')
            )


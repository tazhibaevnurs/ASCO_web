from django.core.management.base import BaseCommand
from blog.models import Blog, transliterate_cyrillic
from django.utils.text import slugify


class Command(BaseCommand):
    help = "Обновляет slug для всех блогов с использованием транслитерации"

    def handle(self, *args, **options):
        all_blogs = Blog.objects.all()
        
        updated_count = 0
        for blog in all_blogs:
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
            
            # Обновляем slug только если он изменился
            if blog.slug != slug:
                blog.slug = slug
                blog.save(update_fields=['slug'])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Обновлен slug для блога "{blog.title}": {slug}')
                )
        
        if updated_count == 0:
            self.stdout.write(self.style.SUCCESS('Все блоги уже имеют правильные slug.'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nУспешно обновлено {updated_count} блогов!')
            )



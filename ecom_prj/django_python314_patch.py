"""
Патч для совместимости Django 4.2 с Python 3.14
Исправляет ошибку 'super' object has no attribute 'dicts' в django/template/context.py
"""
import sys

# Проверяем версию Python
if sys.version_info >= (3, 14):
    try:
        from django.template.context import BaseContext, Context
        
        from copy import copy as copy_func
        from django.template.context import RenderContext
        
        # Сохраняем оригинальный метод __copy__ BaseContext
        original_base_copy = BaseContext.__copy__
        
        # Создаем новый метод __copy__ для BaseContext совместимый с Python 3.14
        def new_base_copy(self):
            # Определяем правильный класс для создания дубликата
            if isinstance(self, RenderContext):
                duplicate = RenderContext.__new__(RenderContext)
                duplicate.template = self.template
            else:
                duplicate = BaseContext.__new__(BaseContext)
            # Инициализируем dicts
            duplicate._reset_dicts()
            # Копируем dicts из оригинала
            duplicate.dicts = self.dicts[:]
            return duplicate
        
        # Применяем патч к BaseContext
        BaseContext.__copy__ = new_base_copy
        
        # Также нужно исправить метод __copy__ для Context
        
        if hasattr(Context, '__copy__'):
            original_context_copy = Context.__copy__
            
            def new_context_copy(self):
                # Создаем новый экземпляр Context
                duplicate = Context.__new__(Context)
                # Инициализируем базовые атрибуты BaseContext
                duplicate._reset_dicts()
                duplicate.dicts = self.dicts[:]
                # Инициализируем атрибуты Context
                duplicate.autoescape = self.autoescape
                duplicate.use_l10n = self.use_l10n
                duplicate.use_tz = self.use_tz
                duplicate.template_name = self.template_name
                duplicate.template = self.template
                # Правильно копируем render_context используя исправленный метод __copy__
                # RenderContext наследуется от BaseContext, поэтому использует исправленный BaseContext.__copy__
                duplicate.render_context = copy_func(self.render_context)
                return duplicate
            
            Context.__copy__ = new_context_copy
    except (ImportError, AttributeError):
        # Если не удалось применить патч, просто игнорируем
        pass


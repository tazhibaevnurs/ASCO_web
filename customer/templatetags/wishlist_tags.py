from django import template

register = template.Library()


@register.filter
def in_wishlist(product_id, wishlist_ids):
    """Возвращает True, если product_id есть в wishlist_ids (set/list из контекста)."""
    if wishlist_ids is None:
        return False
    return product_id in wishlist_ids

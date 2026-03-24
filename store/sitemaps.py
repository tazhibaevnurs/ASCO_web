from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import Blog
from store.models import Product


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            "store:index",
            "store:shop",
            "store:about",
            "store:contact",
            "store:faqs",
            "blog:blog_list",
        ]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Product.objects.filter(status="Published").order_by("-date")

    def lastmod(self, obj):
        return obj.date


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Blog.objects.filter(status="Published").order_by("-date")

    def lastmod(self, obj):
        return obj.date

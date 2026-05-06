from django import template
from django.utils.html import strip_tags

register = template.Library()


@register.filter(name='strip_html')
def strip_html(value):
    """Strip HTML tags from content for plain-text preview."""
    return strip_tags(value)

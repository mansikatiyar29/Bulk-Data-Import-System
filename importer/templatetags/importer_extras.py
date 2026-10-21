"""Custom template filters for the importer app."""
from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Return mapping[key] or None — used to render a dict value by key."""
    if mapping is None or not isinstance(mapping, dict):
        return None
    return mapping.get(key)
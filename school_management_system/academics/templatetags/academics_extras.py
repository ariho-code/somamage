from django import template

register = template.Library()

@register.filter
def mod_12(value):
    try:
        return int(value) % 12
    except (TypeError, ValueError):
        return 0

@register.filter
def get_item(dictionary, key):
    if not isinstance(dictionary, dict):
        return None
    # Try both the key as-is and as integer (template passes strings sometimes)
    val = dictionary.get(key)
    if val is None:
        try:
            val = dictionary.get(int(key))
        except (TypeError, ValueError):
            pass
    return val

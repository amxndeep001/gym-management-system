from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr):
    """Get attribute from object, handling related fields."""
    if obj is None:
        return ''
    try:
        value = getattr(obj, attr)
        if callable(value):
            value = value()
        return value
    except AttributeError:
        return ''


@register.filter
def display_value(obj, field):
    """Like get_attr, but shows a choice field's label (e.g. 'Accessories' for 'Other')."""
    getter = getattr(obj, f'get_{field}_display', None)
    return getter() if getter else get_attr(obj, field)


@register.filter
def add_class(field, css_class):
    """Add CSS class to form field."""
    return field.as_widget(attrs={'class': css_class})


@register.filter
def replace(value, arg):
    """Replace underscores with spaces."""
    return value.replace('_', ' ')
from .views import ENTITY_CONFIG, NAV_SECTIONS, section_for_entity


def navigation(request):
    """Expose the navbar sections to every template, plus the key of the section being viewed."""
    match = request.resolver_match
    name = match.url_name if match else None
    if name == 'section':
        active = match.kwargs['section_key']
    elif name == 'dashboard':
        entity = request.GET.get('entity', 'member')
        active = section_for_entity(entity if entity in ENTITY_CONFIG else 'member')
    elif name == 'member_profile':
        active = 'membership'
    else:
        active = name
    return {'nav_sections': NAV_SECTIONS, 'active_section': active}

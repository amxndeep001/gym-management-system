from django import template

register = template.Library()


@register.filter
def get_entity_config(entity_key):
    """Get entity configuration from ENTITY_CONFIG."""
    ENTITY_CONFIG = {
        'branch': {'display_name': 'Branches', 'icon': 'building', 'model': None, 'list_fields': ['branch_id', 'branch_name', 'location', 'phone']},
        'staff': {'display_name': 'Staff', 'icon': 'people', 'model': None, 'list_fields': ['staff_id', 'name', 'phone', 'salary', 'role', 'branch']},
        'trainer': {'display_name': 'Trainers', 'icon': 'person-badge', 'model': None, 'list_fields': ['staff', 'specialization', 'experience']},
        'receptionist': {'display_name': 'Receptionists', 'icon': 'person-badge', 'model': None, 'list_fields': ['staff', 'shift_timing']},
        'manager': {'display_name': 'Managers', 'icon': 'person-badge', 'model': None, 'list_fields': ['staff', 'authority_level']},
        'maintenance_staff': {'display_name': 'Maintenance Staff', 'icon': 'person-badge', 'model': None, 'list_fields': ['staff', 'skill_type']},
        'equipment': {'display_name': 'Equipment', 'icon': 'gear', 'model': None, 'list_fields': ['equipment_id', 'name', 'category', 'branch']},
        'cardio_equipment': {'display_name': 'Cardio Equipment', 'icon': 'gear', 'model': None, 'list_fields': ['equipment', 'max_speed', 'incline_levels']},
        'strength_equipment': {'display_name': 'Strength Equipment', 'icon': 'gear', 'model': None, 'list_fields': ['equipment', 'weight_stack', 'max_load']},
        'membership_plan': {'display_name': 'Membership Plans', 'icon': 'credit-card', 'model': None, 'list_fields': ['plan_id', 'plan_name', 'duration', 'fee']},
        'member': {'display_name': 'Members', 'icon': 'person', 'model': None, 'list_fields': ['member_id', 'name', 'gender', 'dob', 'phone', 'join_date', 'branch', 'plan']},
        'standard_member': {'display_name': 'Standard Members', 'icon': 'person', 'model': None, 'list_fields': ['member', 'max_visits_month']},
        'premium_member': {'display_name': 'Premium Members', 'icon': 'person', 'model': None, 'list_fields': ['member', 'assigned_trainer', 'priority_diet_access']},
        'payment': {'display_name': 'Payments', 'icon': 'cash', 'model': None, 'list_fields': ['payment_id', 'member', 'amount', 'pay_date', 'mode']},
        'cash_payment': {'display_name': 'Cash Payments', 'icon': 'cash', 'model': None, 'list_fields': ['payment', 'receipt_no']},
        'card_payment': {'display_name': 'Card Payments', 'icon': 'cash', 'model': None, 'list_fields': ['payment', 'card_last4', 'card_type']},
        'online_payment': {'display_name': 'Online Payments', 'icon': 'cash', 'model': None, 'list_fields': ['payment', 'transaction_id', 'gateway']},
        'locker': {'display_name': 'Lockers', 'icon': 'lock', 'model': None, 'list_fields': ['locker_id', 'member', 'locker_no']},
        'gym_class': {'display_name': 'Gym Classes', 'icon': 'calendar', 'model': None, 'list_fields': ['class_id', 'trainer', 'name', 'capacity']},
        'class_schedule': {'display_name': 'Class Schedules', 'icon': 'calendar', 'model': None, 'list_fields': ['schedule_id', 'gym_class', 'room', 'start_time', 'end_time']},
        'attendance': {'display_name': 'Attendance', 'icon': 'check-circle', 'model': None, 'list_fields': ['attendance_id', 'member', 'schedule', 'date', 'in_time', 'status']},
        'feedback': {'display_name': 'Feedback', 'icon': 'chat', 'model': None, 'list_fields': ['feedback_id', 'member', 'rating', 'comments', 'date']},
        'workout_plan': {'display_name': 'Workout Plans', 'icon': 'heart-pulse', 'model': None, 'list_fields': ['workout_id', 'member', 'plan_name', 'duration', 'goal']},
        'diet_plan': {'display_name': 'Diet Plans', 'icon': 'heart-pulse', 'model': None, 'list_fields': ['diet_id', 'trainer', 'member', 'calories']},
        'equipment_maintenance': {'display_name': 'Equipment Maintenance', 'icon': 'tools', 'model': None, 'list_fields': ['maintenance_id', 'equipment', 'date', 'cost']},
    }
    return ENTITY_CONFIG.get(entity_key)


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
def add_class(field, css_class):
    """Add CSS class to form field."""
    return field.as_widget(attrs={'class': css_class})


@register.filter
def replace(value, arg):
    """Replace underscores with spaces."""
    return value.replace('_', ' ')
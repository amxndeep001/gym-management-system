import calendar
from datetime import date, datetime, timedelta

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Avg, Count, ProtectedError, Q, Sum
from django.db.models.functions import TruncMonth

from .models import (
    add_months,
    Branch, Staff, Trainer, Receptionist, Manager, MaintenanceStaff,
    Equipment, CardioEquipment, StrengthEquipment,
    MembershipPlan, Member, StandardMember, PremiumMember,
    Payment, CashPayment, CardPayment, OnlinePayment,
    Locker, GymClass, ClassSchedule, Attendance, Feedback,
    WorkoutPlan, DietPlan, EquipmentMaintenance
)
from .forms import (
    BranchForm, StaffForm, TrainerForm, ReceptionistForm, ManagerForm, MaintenanceStaffForm,
    EquipmentForm, CardioEquipmentForm, StrengthEquipmentForm,
    MembershipPlanForm, MemberForm, StandardMemberForm, PremiumMemberForm,
    PaymentForm, CashPaymentForm, CardPaymentForm, OnlinePaymentForm,
    LockerForm, GymClassForm, ClassScheduleForm, AttendanceForm, FeedbackForm,
    WorkoutPlanForm, DietPlanForm, EquipmentMaintenanceForm
)


ENTITY_CONFIG = {
    'branch': {
        'model': Branch,
        'form': BranchForm,
        'list_fields': ['branch_id', 'branch_name', 'location', 'phone'],
        'display_name': 'Branches',
        'singular': 'Branch',
        'icon': 'building',
    },
    'staff': {
        'model': Staff,
        'form': StaffForm,
        'list_fields': ['staff_id', 'name', 'phone', 'salary', 'role', 'branch'],
        'display_name': 'Staff',
        'singular': 'Staff Member',
        'icon': 'people',
        'select_related': ['branch', 'trainer_profile', 'receptionist_profile', 'manager_profile',
                           'maintenance_profile'],
        'extra_columns': [('Role details', 'gym/cells/staff_role.html')],
    },
    'trainer': {
        'model': Trainer,
        'form': TrainerForm,
        'list_fields': ['staff', 'specialization', 'experience'],
        'display_name': 'Trainers',
        'singular': 'Trainer',
        'icon': 'person-arms-up',
    },
    'receptionist': {
        'model': Receptionist,
        'form': ReceptionistForm,
        'list_fields': ['staff', 'shift_timing'],
        'display_name': 'Receptionists',
        'singular': 'Receptionist',
        'icon': 'person-workspace',
    },
    'manager': {
        'model': Manager,
        'form': ManagerForm,
        'list_fields': ['staff', 'authority_level'],
        'display_name': 'Managers',
        'singular': 'Manager',
        'icon': 'person-gear',
    },
    'maintenance_staff': {
        'model': MaintenanceStaff,
        'form': MaintenanceStaffForm,
        'list_fields': ['staff', 'skill_type'],
        'display_name': 'Maintenance Staff',
        'singular': 'Maintenance Staff Member',
        'icon': 'wrench-adjustable',
    },
    'equipment': {
        'model': Equipment,
        'form': EquipmentForm,
        'list_fields': ['equipment_id', 'name', 'category', 'branch'],
        'display_name': 'Equipment',
        'singular': 'Equipment',
        'icon': 'gear',
        'select_related': ['branch', 'cardio_details', 'strength_details'],
        'extra_columns': [('Specs', 'gym/cells/equipment_specs.html')],
        'filter': {
            'param': 'category',
            'caption': 'Disjoint + Partial: at most one subclass; Accessories belong to none.',
            'options': [('Cardio', 'Cardio', Q(category='Cardio')),
                        ('Strength', 'Strength', Q(category='Strength')),
                        ('Other', 'Accessories', Q(category='Other'))],
        },
    },
    'cardio_equipment': {
        'model': CardioEquipment,
        'form': CardioEquipmentForm,
        'list_fields': ['equipment', 'max_speed', 'incline_levels'],
        'display_name': 'Cardio Equipment',
        'singular': 'Cardio Equipment',
        'icon': 'gear',
    },
    'strength_equipment': {
        'model': StrengthEquipment,
        'form': StrengthEquipmentForm,
        'list_fields': ['equipment', 'weight_stack', 'max_load'],
        'display_name': 'Strength Equipment',
        'singular': 'Strength Equipment',
        'icon': 'gear',
    },
    'membership_plan': {
        'model': MembershipPlan,
        'form': MembershipPlanForm,
        'list_fields': ['plan_id', 'plan_name', 'duration', 'fee'],
        'display_name': 'Membership Plans',
        'singular': 'Membership Plan',
        'icon': 'card-checklist',
    },
    'member': {
        'model': Member,
        'form': MemberForm,
        'list_fields': ['member_id', 'name', 'gender', 'dob', 'phone', 'join_date', 'branch', 'plan'],
        'display_name': 'Members',
        'singular': 'Member',
        'icon': 'person-vcard',
        'select_related': ['branch', 'plan', 'standard_profile', 'premium_profile__assigned_trainer__staff'],
        'extra_columns': [('Tier', 'gym/cells/member_tier.html'), ('Status', 'gym/cells/member_status.html')],
        'filter': {
            'param': 'tier',
            'caption': 'Overlapping + Partial: a member can hold both tiers or none, so Standard and Premium overlap.',
            'options': [('standard', 'Standard', Q(standard_profile__isnull=False)),
                        ('premium', 'Premium', Q(premium_profile__isnull=False)),
                        ('both', 'Both', Q(standard_profile__isnull=False, premium_profile__isnull=False)),
                        ('none', 'No tier', Q(standard_profile__isnull=True, premium_profile__isnull=True))],
        },
    },
    'standard_member': {
        'model': StandardMember,
        'form': StandardMemberForm,
        'list_fields': ['member', 'max_visits_month'],
        'display_name': 'Standard Members',
        'singular': 'Standard Member',
        'icon': 'person',
    },
    'premium_member': {
        'model': PremiumMember,
        'form': PremiumMemberForm,
        'list_fields': ['member', 'assigned_trainer', 'priority_diet_access'],
        'display_name': 'Premium Members',
        'singular': 'Premium Member',
        'icon': 'person',
    },
    'payment': {
        'model': Payment,
        'form': PaymentForm,
        'list_fields': ['payment_id', 'member', 'amount', 'pay_date', 'mode'],
        'display_name': 'Payments',
        'singular': 'Payment',
        'icon': 'cash-coin',
        'select_related': ['member', 'cash_details', 'card_details', 'online_details'],
        'extra_columns': [('Details', 'gym/cells/payment_details.html')],
        'filter': {
            'param': 'mode',
            'caption': 'Disjoint + Total: every payment is exactly one of Cash, Card or Online.',
            'options': [('Cash', 'Cash', Q(mode='Cash')),
                        ('Card', 'Card', Q(mode='Card')),
                        ('Online', 'Online', Q(mode='Online'))],
        },
    },
    'cash_payment': {
        'model': CashPayment,
        'form': CashPaymentForm,
        'list_fields': ['payment', 'receipt_no'],
        'display_name': 'Cash Payments',
        'singular': 'Cash Payment',
        'icon': 'cash',
    },
    'card_payment': {
        'model': CardPayment,
        'form': CardPaymentForm,
        'list_fields': ['payment', 'card_last4', 'card_type'],
        'display_name': 'Card Payments',
        'singular': 'Card Payment',
        'icon': 'cash',
    },
    'online_payment': {
        'model': OnlinePayment,
        'form': OnlinePaymentForm,
        'list_fields': ['payment', 'transaction_id', 'gateway'],
        'display_name': 'Online Payments',
        'singular': 'Online Payment',
        'icon': 'cash',
    },
    'locker': {
        'model': Locker,
        'form': LockerForm,
        'list_fields': ['locker_id', 'member', 'locker_no'],
        'display_name': 'Lockers',
        'singular': 'Locker',
        'icon': 'lock',
    },
    'gym_class': {
        'model': GymClass,
        'form': GymClassForm,
        'list_fields': ['class_id', 'trainer', 'name', 'capacity'],
        'display_name': 'Gym Classes',
        'singular': 'Gym Class',
        'icon': 'bicycle',
    },
    'class_schedule': {
        'model': ClassSchedule,
        'form': ClassScheduleForm,
        'list_fields': ['schedule_id', 'gym_class', 'room', 'start_time', 'end_time'],
        'display_name': 'Class Schedules',
        'singular': 'Class Schedule',
        'icon': 'calendar-week',
    },
    'attendance': {
        'model': Attendance,
        'form': AttendanceForm,
        'list_fields': ['attendance_id', 'member', 'schedule', 'date', 'in_time', 'status'],
        'display_name': 'Attendance',
        'singular': 'Attendance Record',
        'icon': 'check2-circle',
    },
    'feedback': {
        'model': Feedback,
        'form': FeedbackForm,
        'list_fields': ['feedback_id', 'member', 'rating', 'comments', 'date'],
        'display_name': 'Feedback',
        'singular': 'Feedback',
        'icon': 'chat-heart',
    },
    'workout_plan': {
        'model': WorkoutPlan,
        'form': WorkoutPlanForm,
        'list_fields': ['workout_id', 'member', 'plan_name', 'duration', 'goal'],
        'display_name': 'Workout Plans',
        'singular': 'Workout Plan',
        'icon': 'heart-pulse',
    },
    'diet_plan': {
        'model': DietPlan,
        'form': DietPlanForm,
        'list_fields': ['diet_id', 'trainer', 'member', 'calories'],
        'display_name': 'Diet Plans',
        'singular': 'Diet Plan',
        'icon': 'egg-fried',
    },
    'equipment_maintenance': {
        'model': EquipmentMaintenance,
        'form': EquipmentMaintenanceForm,
        'list_fields': ['maintenance_id', 'equipment', 'date', 'cost'],
        'display_name': 'Equipment Maintenance',
        'singular': 'Maintenance Record',
        'icon': 'tools',
    },
}

# Subtypes entered in their superclass form (Staff / Equipment / Member / Payment) are created and
# deleted there, so their own screens only allow viewing and editing. Each entry gives the superclass,
# the query string that pre-selects the subtype on the superclass's create form, and the hint shown
# instead of an Add button.
MANAGED_SUBTYPES = {
    'trainer': ('staff', 'role=Trainer', 'To add a Trainer, add a Staff member with role Trainer.'),
    'receptionist': ('staff', 'role=Receptionist', 'To add a Receptionist, add a Staff member with role Receptionist.'),
    'manager': ('staff', 'role=Manager', 'To add a Manager, add a Staff member with role Manager.'),
    'maintenance_staff': ('staff', 'role=Maintenance_Staff',
                          'To add Maintenance Staff, add a Staff member with role Maintenance Staff.'),
    'cardio_equipment': ('equipment', 'category=Cardio', 'To add Cardio Equipment, add Equipment with category Cardio.'),
    'strength_equipment': ('equipment', 'category=Strength',
                           'To add Strength Equipment, add Equipment with category Strength.'),
    'standard_member': ('member', 'is_standard=on', 'To add a Standard Member, add a Member with the Standard tier ticked.'),
    'premium_member': ('member', 'is_premium=on', 'To add a Premium Member, add a Member with the Premium tier ticked.'),
    'cash_payment': ('payment', 'mode=Cash', 'To record a Cash Payment, add a Payment with mode Cash.'),
    'card_payment': ('payment', 'mode=Card', 'To record a Card Payment, add a Payment with mode Card.'),
    'online_payment': ('payment', 'mode=Online', 'To record an Online Payment, add a Payment with mode Online.'),
}
for key, (parent, query, hint) in MANAGED_SUBTYPES.items():
    ENTITY_CONFIG[key].update(managed_by=parent, create_query=query, create_hint=hint)

# Top navbar: one entry per section. Sections with `items` open /section/<key>/, a page of
# sub-category cards; `subtypes` adds a second row of cards for a specialization's subclasses.
NAV_SECTIONS = [
    {'key': 'home', 'label': 'Home', 'icon': 'house-door', 'url_name': 'home', 'items': []},
    {'key': 'analytics', 'label': 'Analytics', 'icon': 'bar-chart-line', 'url_name': 'analytics', 'items': []},
    {'key': 'branch_staff', 'label': 'Branch & Staff', 'icon': 'building',
     'description': 'Branches and the people who run them',
     'items': ['branch', 'staff'],
     'subtypes': {'title': 'Staff Specializations (Disjoint, Total)',
                  'items': ['trainer', 'receptionist', 'manager', 'maintenance_staff']}},
    {'key': 'equipment', 'label': 'Equipment', 'icon': 'gear',
     'description': 'Machines, accessories and their upkeep',
     'items': ['equipment', 'equipment_maintenance']},
    {'key': 'membership', 'label': 'Membership & Members', 'icon': 'people',
     'description': 'Plans, members and their tiers',
     'items': ['membership_plan', 'member']},
    {'key': 'payments', 'label': 'Payments', 'icon': 'cash-coin',
     'description': 'Cash, card and online payments',
     'items': ['payment']},
    {'key': 'classes', 'label': 'Classes & Attendance', 'icon': 'calendar-week',
     'description': 'Classes, time slots and check-ins',
     'items': ['gym_class', 'class_schedule', 'attendance']},
    {'key': 'others', 'label': 'Others', 'icon': 'grid',
     'description': 'Lockers, feedback, workout and diet plans',
     'items': ['locker', 'feedback', 'workout_plan', 'diet_plan']},
]
SECTIONS = {section['key']: section for section in NAV_SECTIONS}


def section_entity_keys(section):
    return section['items'] + section.get('subtypes', {}).get('items', [])


ENTITY_SECTION = {key: section['key'] for section in NAV_SECTIONS for key in section_entity_keys(section)}


def section_for_entity(entity_key):
    """Navbar section of an entity; unlinked subtypes (e.g. cash_payment) belong to their superclass's."""
    config = ENTITY_CONFIG.get(entity_key, {})
    return ENTITY_SECTION.get(entity_key) or ENTITY_SECTION.get(config.get('managed_by'))


def entity_cards(keys, counts=False):
    cards = []
    for key in keys:
        config = ENTITY_CONFIG[key]
        card = {'key': key, 'label': config['display_name'], 'icon': config['icon']}
        if counts:
            card['count'] = config['model'].objects.count()
        cards.append(card)
    return cards


def managed_message(config):
    parent_key = config['managed_by']
    return (f'{config["display_name"]} are created and deleted together with their {parent_key} record. '
            f'Use {ENTITY_CONFIG[parent_key]["display_name"]} to add or delete one.')


def get_entity_config(entity_key):
    return ENTITY_CONFIG.get(entity_key)


def get_queryset(entity_key):
    config = get_entity_config(entity_key)
    if config:
        model = config['model']
        return model.objects.select_related(*config.get('select_related', [])).all()
    return None


def apply_list_filter(config, queryset, request):
    """Subtype filter buttons for a superclass list (e.g. ?mode=Card), each with its record count."""
    spec = config.get('filter')
    if not spec:
        return queryset, None
    selected = request.GET.get(spec['param'], '')
    counts = config['model'].objects.aggregate(
        all=Count('pk'), **{value: Count('pk', filter=q) for value, _, q in spec['options']})
    values = [value for value, _, _ in spec['options']]
    buttons = [{'value': '', 'label': 'All', 'count': counts['all'], 'active': selected not in values}]
    for value, label, q in spec['options']:
        buttons.append({'value': value, 'label': label, 'count': counts[value], 'active': selected == value})
        if selected == value:
            queryset = queryset.filter(q)
    return queryset, {'param': spec['param'], 'caption': spec['caption'], 'buttons': buttons}


def protected_message(obj, error):
    """Explain why a delete was blocked by on_delete=PROTECT."""
    blocking = list(error.protected_objects)
    names = ', '.join(str(o) for o in blocking[:3])
    more = f' and {len(blocking) - 3} more' if len(blocking) > 3 else ''
    kind = blocking[0]._meta.verbose_name_plural if blocking else 'records'
    return (f'Cannot delete "{obj}": {len(blocking)} {kind} still reference it ({names}{more}). '
            f'Reassign or delete them first.')


def get_object(entity_key, pk):
    config = get_entity_config(entity_key)
    if config:
        model = config['model']
        return get_object_or_404(model, pk=pk)
    return None


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'gym/login.html')


def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard(request):
    entity_key = request.GET.get('entity', 'member')
    action = request.GET.get('action', 'list')
    pk = request.GET.get('pk')

    config = get_entity_config(entity_key)
    if not config:
        entity_key = 'member'
        config = get_entity_config(entity_key)

    if config.get('managed_by') and action in ('create', 'delete'):
        messages.info(request, managed_message(config))
        return redirect(f'{request.path}?entity={entity_key}&action=list')

    context = {
        'entity_key': entity_key,
        'config': config,
        'section_tabs': entity_cards(section_entity_keys(SECTIONS[section_for_entity(entity_key)])),
        'action': action,
        'object': None,
        'form': None,
        'object_list': None,
        'error_message': None,
    }

    if action == 'list':
        context['object_list'], context['list_filter'] = apply_list_filter(config, get_queryset(entity_key), request)

    elif action == 'create':
        if request.method == 'POST':
            form = config['form'](request.POST)
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, f'{config["display_name"]} created successfully.')
                    return redirect(f'{request.path}?entity={entity_key}&action=list')
                except Exception as e:
                    messages.error(request, f'Error creating record: {str(e)}')
            context['form'] = form
        else:
            # Query parameters naming a form field pre-fill it, e.g. ?role=Trainer from a subtype page
            fields = config['form'].base_fields
            context['form'] = config['form'](initial={k: v for k, v in request.GET.items() if k in fields})

    elif action == 'edit':
        obj = get_object(entity_key, pk)
        if obj:
            context['object'] = obj
            if request.method == 'POST':
                form = config['form'](request.POST, instance=obj)
                if form.is_valid():
                    try:
                        form.save()
                        messages.success(request, f'{config["display_name"]} updated successfully.')
                        return redirect(f'{request.path}?entity={entity_key}&action=list')
                    except Exception as e:
                        messages.error(request, f'Error updating record: {str(e)}')
                context['form'] = form
            else:
                context['form'] = config['form'](instance=obj)
        else:
            messages.error(request, 'Record not found.')
            return redirect(f'{request.path}?entity={entity_key}&action=list')

    elif action == 'delete':
        obj = get_object(entity_key, pk)
        if obj:
            context['object'] = obj
            if request.method == 'POST':
                try:
                    obj.delete()
                    messages.success(request, f'{config["display_name"]} deleted successfully.')
                    return redirect(f'{request.path}?entity={entity_key}&action=list')
                except ProtectedError as e:
                    messages.error(request, protected_message(obj, e))
                    return redirect(f'{request.path}?entity={entity_key}&action=list')
                except Exception as e:
                    messages.error(request, f'Error deleting record: {str(e)}')
        else:
            messages.error(request, 'Record not found.')
            return redirect(f'{request.path}?entity={entity_key}&action=list')

    return render(request, 'gym/dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def ajax_create(request, entity_key):
    config = get_entity_config(entity_key)
    if not config:
        return JsonResponse({'success': False, 'error': 'Invalid entity'})
    if config.get('managed_by'):
        return JsonResponse({'success': False, 'error': managed_message(config)})

    form = config['form'](request.POST)
    if form.is_valid():
        try:
            obj = form.save()
            return JsonResponse({'success': True, 'id': obj.pk, 'message': f'{config["display_name"]} created successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'errors': form.errors})


@login_required
@require_http_methods(["POST"])
def ajax_update(request, entity_key, pk):
    config = get_entity_config(entity_key)
    if not config:
        return JsonResponse({'success': False, 'error': 'Invalid entity'})

    obj = get_object(entity_key, pk)
    if not obj:
        return JsonResponse({'success': False, 'error': 'Record not found'})

    form = config['form'](request.POST, instance=obj)
    if form.is_valid():
        try:
            form.save()
            return JsonResponse({'success': True, 'message': f'{config["display_name"]} updated successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'errors': form.errors})


@login_required
@require_http_methods(["POST"])
def ajax_delete(request, entity_key, pk):
    config = get_entity_config(entity_key)
    if not config:
        return JsonResponse({'success': False, 'error': 'Invalid entity'})
    if config.get('managed_by'):
        return JsonResponse({'success': False, 'error': managed_message(config)})

    obj = get_object(entity_key, pk)
    if not obj:
        return JsonResponse({'success': False, 'error': 'Record not found'})

    try:
        obj.delete()
        return JsonResponse({'success': True, 'message': f'{config["display_name"]} deleted successfully.'})
    except ProtectedError as e:
        return JsonResponse({'success': False, 'error': protected_message(obj, e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def month_starts(today, count):
    """First day of each of the last `count` months, oldest first."""
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(date(year, month, 1))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return months[::-1]


def gym_progress(today, count=12):
    """Gym Progress chart: cumulative members and revenue per month for the last `count` months.

    Members are counted by join month and accumulated on top of everyone who joined earlier;
    months with no joins or payments stay at 0.
    """
    months = month_starts(today, count)
    index = {m: i for i, m in enumerate(months)}
    joined, revenue = [0] * count, [0.0] * count
    for row in (Member.objects.filter(join_date__gte=months[0]).annotate(month=TruncMonth('join_date'))
                .values('month').annotate(n=Count('member_id'))):
        joined[index[row['month']]] = row['n']
    for row in (Payment.objects.filter(pay_date__gte=months[0]).annotate(month=TruncMonth('pay_date'))
                .values('month').annotate(total=Sum('amount'))):
        revenue[index[row['month']]] = float(row['total'])
    total = Member.objects.filter(join_date__lt=months[0]).count()
    members = []
    for n in joined:
        total += n
        members.append(total)
    return {'labels': [m.strftime('%b %Y') for m in months], 'members': members, 'revenue': revenue}


@login_required
def analytics(request):
    today = date.today()
    members = Member.objects.select_related('plan')
    payments = Payment.objects.all()
    feedback = Feedback.objects.all()
    member_list = list(members)
    attended = Attendance.objects.filter(status__in=['Present', 'Late'])

    kpis = {
        'total_members': len(member_list),
        'active_members': sum(m.is_active for m in member_list),
        'revenue_this_month': payments.filter(pay_date__year=today.year, pay_date__month=today.month)
                                      .aggregate(total=Sum('amount'))['total'] or 0,
        'attendance_today': attended.filter(date=today).count(),
        'avg_rating': feedback.aggregate(avg=Avg('rating'))['avg'],
    }

    # 1. Monthly revenue by payment mode (last 12 months)
    months = month_starts(today, 12)
    month_index = {m: i for i, m in enumerate(months)}
    revenue = {mode: [0] * len(months) for mode, _ in Payment.MODE_CHOICES}
    monthly = (payments.filter(pay_date__gte=months[0]).annotate(month=TruncMonth('pay_date'))
               .values('month', 'mode').annotate(total=Sum('amount')))
    for row in monthly:
        revenue[row['mode']][month_index[row['month']]] = float(row['total'])

    # 2. Members per membership plan
    plans = MembershipPlan.objects.order_by('plan_id').annotate(n=Count('members'))

    # 3. MEMBER specialization (overlapping + partial)
    tiers = members.aggregate(
        standard=Count('member_id', filter=Q(standard_profile__isnull=False, premium_profile__isnull=True)),
        premium=Count('member_id', filter=Q(standard_profile__isnull=True, premium_profile__isnull=False)),
        both=Count('member_id', filter=Q(standard_profile__isnull=False, premium_profile__isnull=False)),
        none=Count('member_id', filter=Q(standard_profile__isnull=True, premium_profile__isnull=True)),
    )

    charts = {
        'progress': gym_progress(today),
        'revenue': {'labels': [m.strftime('%b %Y') for m in months], 'series': revenue},
        'plans': {'labels': [p.plan_name for p in plans], 'data': [p.n for p in plans]},
        'tiers': {'labels': ['Standard only', 'Premium only', 'Both', 'No tier'],
                  'data': [tiers['standard'], tiers['premium'], tiers['both'], tiers['none']]},
    }

    return render(request, 'gym/analytics.html', {
        'kpis': kpis,
        'charts': charts,
    })


def trend(current, previous):
    """Percent change for a KPI's "vs last month" arrow, or None when there is nothing to compare to."""
    if not previous:
        return None
    change = (float(current) - float(previous)) / float(previous) * 100
    return {'pct': abs(round(change)), 'up': change >= 0}


@login_required
def home(request):
    today = date.today()
    last_month_day = add_months(today, -1)
    this_month, last_month = today.replace(day=1), last_month_day.replace(day=1)
    members = list(Member.objects.select_related('plan'))
    attended = Attendance.objects.filter(status__in=['Present', 'Late'])

    active_now = sum(m.is_active for m in members)
    active_then = sum(m.join_date <= last_month_day <= m.expiry_date for m in members)
    # Month to date, compared with the same days of last month
    revenue_now = Payment.objects.filter(pay_date__range=(this_month, today)).aggregate(t=Sum('amount'))['t'] or 0
    revenue_then = Payment.objects.filter(pay_date__range=(last_month, last_month_day)) \
                          .aggregate(t=Sum('amount'))['t'] or 0
    checkins_today = attended.filter(date=today).count()
    checkins_last_month = attended.filter(date__range=(last_month, this_month - timedelta(days=1))).count()
    daily_avg = checkins_last_month / calendar.monthrange(last_month.year, last_month.month)[1]
    rating = Feedback.objects.aggregate(avg=Avg('rating'), n=Count('pk'))

    kpis = [
        {'label': 'Active Members', 'icon': 'people-fill', 'value': active_now,
         'trend': trend(active_now, active_then), 'note': 'vs last month'},
        {'label': 'Revenue This Month', 'icon': 'currency-rupee', 'value': revenue_now, 'rupees': True,
         'trend': trend(revenue_now, revenue_then), 'note': 'vs same days last month'},
        {'label': "Today's Check-ins", 'icon': 'door-open-fill', 'value': checkins_today,
         'trend': trend(checkins_today, daily_avg), 'note': "vs last month's daily average"},
        {'label': 'Avg Rating', 'icon': 'star-fill', 'value': rating['avg'], 'rating': True,
         'note': f"from {rating['n']} review{'s' if rating['n'] != 1 else ''}"},
    ]

    # Schedules have a time slot but no weekday, so every slot runs daily
    now = datetime.now().time()
    classes = []
    for slot in ClassSchedule.objects.select_related('gym_class__trainer__staff').order_by('start_time'):
        state = 'done' if slot.end_time <= now else 'live' if slot.start_time <= now else 'upcoming'
        classes.append({'slot': slot, 'state': state})

    soon = today + timedelta(days=15)
    expiring = sorted(((m, (m.expiry_date - today).days) for m in members if today <= m.expiry_date <= soon),
                      key=lambda pair: pair[1])

    tiles = []
    for section in NAV_SECTIONS:
        if section['items']:
            tiles.append({**section, 'counts': entity_cards(section['items'], counts=True)})

    return render(request, 'gym/home.html', {
        'today': today,
        'kpis': kpis,
        'tiles': tiles,
        'classes': classes,
        'expiring': expiring,
        'progress': gym_progress(today),
    })


@login_required
def section(request, section_key):
    section = SECTIONS.get(section_key)
    if not section or not section['items']:
        raise Http404('Unknown section')
    subtypes = section.get('subtypes')
    context = {
        'section': section,
        'cards': entity_cards(section['items'], counts=True),
        'subtype_title': subtypes['title'] if subtypes else None,
        'subtype_cards': entity_cards(subtypes['items'], counts=True) if subtypes else None,
    }
    if section_key == 'equipment':
        today = date.today()
        context['equipment_stats'] = Equipment.objects.aggregate(
            total=Count('pk'),
            cardio=Count('pk', filter=Q(category='Cardio')),
            strength=Count('pk', filter=Q(category='Strength')),
            accessories=Count('pk', filter=Q(category='Other')),
        )
        context['equipment_stats']['maintenance_cost'] = EquipmentMaintenance.objects.filter(
            date__year=today.year, date__month=today.month).aggregate(total=Sum('cost'))['total'] or 0
    return render(request, 'gym/section.html', context)


@login_required
def member_profile(request, pk):
    member = get_object_or_404(Member.objects.select_related('branch', 'plan'), pk=pk)
    payments = member.payments.select_related('cash_details', 'card_details', 'online_details').order_by('-pay_date')
    return render(request, 'gym/member_profile.html', {
        'member': member,
        'standard': StandardMember.objects.filter(member=member).first(),
        'premium': PremiumMember.objects.select_related('assigned_trainer__staff').filter(member=member).first(),
        'locker': Locker.objects.filter(member=member).first(),
        'payments': payments,
        'payment_total': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'attendance': member.attendance_records.select_related('schedule__gym_class').order_by('-date', '-in_time'),
        'workout_plans': member.workout_plans.all(),
        'diet_plans': member.diet_plans.select_related('trainer__staff'),
        'feedback': member.feedback.order_by('-date'),
    })

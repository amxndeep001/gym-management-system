from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Avg, Count, ProtectedError, Q, Sum
from django.db.models.functions import TruncMonth

from .models import (
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
        'icon': 'building',
    },
    'staff': {
        'model': Staff,
        'form': StaffForm,
        'list_fields': ['staff_id', 'name', 'phone', 'salary', 'role', 'branch'],
        'display_name': 'Staff',
        'icon': 'people',
    },
    'trainer': {
        'model': Trainer,
        'form': TrainerForm,
        'list_fields': ['staff', 'specialization', 'experience'],
        'display_name': 'Trainers',
        'icon': 'person-badge',
    },
    'receptionist': {
        'model': Receptionist,
        'form': ReceptionistForm,
        'list_fields': ['staff', 'shift_timing'],
        'display_name': 'Receptionists',
        'icon': 'person-badge',
    },
    'manager': {
        'model': Manager,
        'form': ManagerForm,
        'list_fields': ['staff', 'authority_level'],
        'display_name': 'Managers',
        'icon': 'person-badge',
    },
    'maintenance_staff': {
        'model': MaintenanceStaff,
        'form': MaintenanceStaffForm,
        'list_fields': ['staff', 'skill_type'],
        'display_name': 'Maintenance Staff',
        'icon': 'person-badge',
    },
    'equipment': {
        'model': Equipment,
        'form': EquipmentForm,
        'list_fields': ['equipment_id', 'name', 'category', 'branch'],
        'display_name': 'Equipment',
        'icon': 'gear',
    },
    'cardio_equipment': {
        'model': CardioEquipment,
        'form': CardioEquipmentForm,
        'list_fields': ['equipment', 'max_speed', 'incline_levels'],
        'display_name': 'Cardio Equipment',
        'icon': 'gear',
    },
    'strength_equipment': {
        'model': StrengthEquipment,
        'form': StrengthEquipmentForm,
        'list_fields': ['equipment', 'weight_stack', 'max_load'],
        'display_name': 'Strength Equipment',
        'icon': 'gear',
    },
    'membership_plan': {
        'model': MembershipPlan,
        'form': MembershipPlanForm,
        'list_fields': ['plan_id', 'plan_name', 'duration', 'fee'],
        'display_name': 'Membership Plans',
        'icon': 'credit-card',
    },
    'member': {
        'model': Member,
        'form': MemberForm,
        'list_fields': ['member_id', 'name', 'gender', 'dob', 'phone', 'join_date', 'branch', 'plan'],
        'display_name': 'Members',
        'icon': 'person',
    },
    'standard_member': {
        'model': StandardMember,
        'form': StandardMemberForm,
        'list_fields': ['member', 'max_visits_month'],
        'display_name': 'Standard Members',
        'icon': 'person',
    },
    'premium_member': {
        'model': PremiumMember,
        'form': PremiumMemberForm,
        'list_fields': ['member', 'assigned_trainer', 'priority_diet_access'],
        'display_name': 'Premium Members',
        'icon': 'person',
    },
    'payment': {
        'model': Payment,
        'form': PaymentForm,
        'list_fields': ['payment_id', 'member', 'amount', 'pay_date', 'mode'],
        'display_name': 'Payments',
        'icon': 'cash',
    },
    'cash_payment': {
        'model': CashPayment,
        'form': CashPaymentForm,
        'list_fields': ['payment', 'receipt_no'],
        'display_name': 'Cash Payments',
        'icon': 'cash',
    },
    'card_payment': {
        'model': CardPayment,
        'form': CardPaymentForm,
        'list_fields': ['payment', 'card_last4', 'card_type'],
        'display_name': 'Card Payments',
        'icon': 'cash',
    },
    'online_payment': {
        'model': OnlinePayment,
        'form': OnlinePaymentForm,
        'list_fields': ['payment', 'transaction_id', 'gateway'],
        'display_name': 'Online Payments',
        'icon': 'cash',
    },
    'locker': {
        'model': Locker,
        'form': LockerForm,
        'list_fields': ['locker_id', 'member', 'locker_no'],
        'display_name': 'Lockers',
        'icon': 'lock',
    },
    'gym_class': {
        'model': GymClass,
        'form': GymClassForm,
        'list_fields': ['class_id', 'trainer', 'name', 'capacity'],
        'display_name': 'Gym Classes',
        'icon': 'calendar',
    },
    'class_schedule': {
        'model': ClassSchedule,
        'form': ClassScheduleForm,
        'list_fields': ['schedule_id', 'gym_class', 'room', 'start_time', 'end_time'],
        'display_name': 'Class Schedules',
        'icon': 'calendar',
    },
    'attendance': {
        'model': Attendance,
        'form': AttendanceForm,
        'list_fields': ['attendance_id', 'member', 'schedule', 'date', 'in_time', 'status'],
        'display_name': 'Attendance',
        'icon': 'check-circle',
    },
    'feedback': {
        'model': Feedback,
        'form': FeedbackForm,
        'list_fields': ['feedback_id', 'member', 'rating', 'comments', 'date'],
        'display_name': 'Feedback',
        'icon': 'chat',
    },
    'workout_plan': {
        'model': WorkoutPlan,
        'form': WorkoutPlanForm,
        'list_fields': ['workout_id', 'member', 'plan_name', 'duration', 'goal'],
        'display_name': 'Workout Plans',
        'icon': 'heart-pulse',
    },
    'diet_plan': {
        'model': DietPlan,
        'form': DietPlanForm,
        'list_fields': ['diet_id', 'trainer', 'member', 'calories'],
        'display_name': 'Diet Plans',
        'icon': 'heart-pulse',
    },
    'equipment_maintenance': {
        'model': EquipmentMaintenance,
        'form': EquipmentMaintenanceForm,
        'list_fields': ['maintenance_id', 'equipment', 'date', 'cost'],
        'display_name': 'Equipment Maintenance',
        'icon': 'tools',
    },
}

# Subtypes entered in their superclass form (StaffForm / PaymentForm / MemberForm) are created
# and deleted there, so their own screens only allow viewing and editing.
for key in ('trainer', 'receptionist', 'manager', 'maintenance_staff'):
    ENTITY_CONFIG[key]['managed_by'] = 'staff'
for key in ('cash_payment', 'card_payment', 'online_payment'):
    ENTITY_CONFIG[key]['managed_by'] = 'payment'
for key in ('standard_member', 'premium_member'):
    ENTITY_CONFIG[key]['managed_by'] = 'member'

ENTITY_GROUPS = {
    'Branch & Staff': ['branch', 'staff', 'trainer', 'receptionist', 'manager', 'maintenance_staff'],
    'Equipment': ['equipment', 'cardio_equipment', 'strength_equipment', 'equipment_maintenance'],
    'Membership & Members': ['membership_plan', 'member', 'standard_member', 'premium_member'],
    'Payments': ['payment', 'cash_payment', 'card_payment', 'online_payment'],
    'Classes & Attendance': ['gym_class', 'class_schedule', 'attendance'],
    'Other': ['locker', 'feedback', 'workout_plan', 'diet_plan'],
}


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
        return model.objects.select_related().all()
    return None


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
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
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
        'active_page': entity_key,
        'config': config,
        'entity_groups': ENTITY_GROUPS,
        'action': action,
        'object': None,
        'form': None,
        'object_list': None,
        'error_message': None,
    }

    if action == 'list':
        context['object_list'] = get_queryset(entity_key)

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
            context['form'] = config['form']()

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
        'revenue': {'labels': [m.strftime('%b %Y') for m in months], 'series': revenue},
        'plans': {'labels': [p.plan_name for p in plans], 'data': [p.n for p in plans]},
        'tiers': {'labels': ['Standard only', 'Premium only', 'Both', 'No tier'],
                  'data': [tiers['standard'], tiers['premium'], tiers['both'], tiers['none']]},
    }

    return render(request, 'gym/analytics.html', {
        'active_page': 'analytics',
        'entity_groups': ENTITY_GROUPS,
        'kpis': kpis,
        'charts': charts,
    })


@login_required
def member_profile(request, pk):
    member = get_object_or_404(Member.objects.select_related('branch', 'plan'), pk=pk)
    payments = member.payments.select_related('cash_details', 'card_details', 'online_details').order_by('-pay_date')
    return render(request, 'gym/member_profile.html', {
        'active_page': 'member',
        'entity_groups': ENTITY_GROUPS,
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

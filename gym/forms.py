from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import (
    Branch, Staff, Trainer, Receptionist, Manager, MaintenanceStaff,
    Equipment, CardioEquipment, StrengthEquipment,
    MembershipPlan, Member, StandardMember, PremiumMember,
    Payment, CashPayment, CardPayment, OnlinePayment,
    Locker, GymClass, ClassSchedule, Attendance, Feedback,
    WorkoutPlan, DietPlan, EquipmentMaintenance
)


def limit_parent_choices(form, field_name, queryset):
    """Restrict a subtype's superclass dropdown, keeping the record being edited in it.

    The superclass key is also the subtype's primary key, so it is locked when editing:
    changing it would insert a new row instead of updating this one.
    """
    field = form.fields[field_name]
    if form.instance.pk:
        queryset = queryset.model.objects.filter(Q(pk__in=queryset) | Q(pk=form.instance.pk))
        field.disabled = True
    field.queryset = queryset


def subtype_field(placeholder, number=False, decimal=False, choices=None):
    if choices:
        return forms.ChoiceField(required=False, choices=[('', '---------')] + choices,
                                 widget=forms.Select(attrs={'class': 'form-select'}))
    if decimal:
        return forms.DecimalField(required=False, widget=forms.NumberInput(
            attrs={'class': 'form-control', 'placeholder': placeholder, 'step': '0.01', 'min': '0'}))
    widget = forms.NumberInput if number else forms.TextInput
    field_class = forms.IntegerField if number else forms.CharField
    return field_class(required=False, widget=widget(attrs={'class': 'form-control', 'placeholder': placeholder}))


class TotalSpecializationForm(forms.ModelForm):
    """Superclass form for a Disjoint + Total hierarchy (Staff, Payment).

    The discriminator picks exactly one subtype, whose fields are filled in the same form.
    Superclass and subtype rows are saved together in one transaction.
    """
    discriminator = None   # superclass field that selects the subtype, e.g. 'role'
    parent_field = None    # subtype's one-to-one key to the superclass, e.g. 'staff'
    subtypes = {}          # discriminator value -> (subtype model, [subtype field names])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for value, (model, names) in self.subtypes.items():
            existing = model.objects.filter(pk=self.instance.pk).first() if self.instance.pk else None
            for name in names:
                self.fields[name].subtype = value
                if existing:
                    self.fields[name].initial = getattr(existing, name)

    def clean(self):
        cleaned = super().clean()
        value = cleaned.get(self.discriminator)
        if value not in self.subtypes:
            return cleaned
        model, names = self.subtypes[value]
        for name in names:
            if name not in self.errors and cleaned.get(name) in (None, ''):
                self.add_error(name, f'Required when {self.discriminator} is {value}.')
        # Validate the subtype row against its model rules, skipping fields that already failed
        sub = (model.objects.filter(pk=self.instance.pk).first() if self.instance.pk else None) or model()
        failed = [name for name in names if name in self.errors]
        for name in names:
            if name not in failed:
                setattr(sub, name, cleaned[name])
        try:
            sub.full_clean(exclude=[self.parent_field] + failed)
        except ValidationError as e:
            self.add_error(None, e)
        self._subtype = sub
        return cleaned

    def save(self, commit=True):
        with transaction.atomic():
            obj = super().save()
            value = getattr(obj, self.discriminator)
            # Disjoint: drop any row left in another subtype (e.g. after a role change)
            for other, (model, _) in self.subtypes.items():
                if other != value:
                    model.objects.filter(pk=obj.pk).delete()
            setattr(self._subtype, self.parent_field, obj)
            self._subtype.save()
        return obj


class PartialSpecializationForm(TotalSpecializationForm):
    """Superclass form for a Disjoint + Partial hierarchy (Equipment).

    Works like TotalSpecializationForm, except a discriminator value may have no subtype
    (category 'Other' = Accessories). Such a record is saved without a subtype row, and any
    row left from its old category is deleted.
    """

    def save(self, commit=True):
        if self.cleaned_data[self.discriminator] in self.subtypes:
            return super().save(commit)
        with transaction.atomic():
            obj = forms.ModelForm.save(self)
            for model, _ in self.subtypes.values():
                model.objects.filter(pk=obj.pk).delete()
        return obj


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['branch_name', 'location', 'phone']
        widgets = {
            'branch_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch Name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
        }


class StaffForm(TotalSpecializationForm):
    discriminator = 'role'
    parent_field = 'staff'
    subtypes = {
        'Trainer': (Trainer, ['specialization', 'experience']),
        'Receptionist': (Receptionist, ['shift_timing']),
        'Manager': (Manager, ['authority_level']),
        'Maintenance_Staff': (MaintenanceStaff, ['skill_type']),
    }

    specialization = subtype_field('Specialization')
    experience = subtype_field('Years of Experience', number=True)
    shift_timing = subtype_field('Shift Timing', choices=Receptionist.SHIFT_CHOICES)
    authority_level = subtype_field('Authority Level', choices=Manager.AUTHORITY_CHOICES)
    skill_type = subtype_field('Skill Type')

    class Meta:
        model = Staff
        fields = ['name', 'phone', 'salary', 'role', 'branch']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Staff Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Salary (₹)', 'step': '0.01'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }


class TrainerForm(forms.ModelForm):
    class Meta:
        model = Trainer
        fields = ['staff', 'specialization', 'experience']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specialization'}),
            'experience': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Years of Experience', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'staff', Staff.objects.filter(role='Trainer', trainer_profile__isnull=True))


class ReceptionistForm(forms.ModelForm):
    class Meta:
        model = Receptionist
        fields = ['staff', 'shift_timing']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'shift_timing': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'staff', Staff.objects.filter(role='Receptionist', receptionist_profile__isnull=True))


class ManagerForm(forms.ModelForm):
    class Meta:
        model = Manager
        fields = ['staff', 'authority_level']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'authority_level': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'staff', Staff.objects.filter(role='Manager', manager_profile__isnull=True))


class MaintenanceStaffForm(forms.ModelForm):
    class Meta:
        model = MaintenanceStaff
        fields = ['staff', 'skill_type']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'skill_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Skill Type'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'staff', Staff.objects.filter(role='Maintenance_Staff', maintenance_profile__isnull=True))


class EquipmentForm(PartialSpecializationForm):
    discriminator = 'category'
    parent_field = 'equipment'
    subtypes = {
        'Cardio': (CardioEquipment, ['max_speed', 'incline_levels']),
        'Strength': (StrengthEquipment, ['weight_stack', 'max_load']),
    }

    max_speed = subtype_field('Max Speed (km/h)', decimal=True)
    incline_levels = subtype_field('Incline Levels', number=True)
    weight_stack = subtype_field('Weight Stack (kg)', decimal=True)
    max_load = subtype_field('Max Load (kg)', decimal=True)

    class Meta:
        model = Equipment
        fields = ['name', 'category', 'branch']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Equipment Name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }


class CardioEquipmentForm(forms.ModelForm):
    class Meta:
        model = CardioEquipment
        fields = ['equipment', 'max_speed', 'incline_levels']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select'}),
            'max_speed': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Speed', 'step': '0.01', 'min': '0'}),
            'incline_levels': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Incline Levels', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'equipment', Equipment.objects.filter(category='Cardio', cardio_details__isnull=True))


class StrengthEquipmentForm(forms.ModelForm):
    class Meta:
        model = StrengthEquipment
        fields = ['equipment', 'weight_stack', 'max_load']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select'}),
            'weight_stack': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weight Stack', 'step': '0.01', 'min': '0'}),
            'max_load': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Load', 'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'equipment', Equipment.objects.filter(category='Strength', strength_details__isnull=True))


class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = ['plan_name', 'duration', 'fee']
        widgets = {
            'plan_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Plan Name'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duration (months)', 'min': '1'}),
            'fee': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Fee (₹)', 'step': '0.01', 'min': '0'}),
        }


class MemberForm(forms.ModelForm):
    """Member form with its tiers (Overlapping + Partial).

    Checkboxes rather than a dropdown: a member may hold the Standard tier, the Premium tier,
    both, or neither. Member and tier rows are saved together in one transaction.
    """
    is_standard = forms.BooleanField(required=False, label='Standard tier')
    max_visits_month = forms.IntegerField(
        required=False, label='Max visits per month',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Visits per Month', 'min': '1'}))
    is_premium = forms.BooleanField(required=False, label='Premium tier')
    assigned_trainer = forms.ModelChoiceField(
        queryset=Trainer.objects.select_related('staff'), required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    priority_diet_access = forms.BooleanField(required=False, initial=True)

    # tier checkbox -> (tier model, the tier's fields)
    tiers = {
        'is_standard': (StandardMember, ['max_visits_month']),
        'is_premium': (PremiumMember, ['assigned_trainer', 'priority_diet_access']),
    }

    class Meta:
        model = Member
        fields = ['branch', 'plan', 'name', 'gender', 'dob', 'phone', 'join_date']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'plan': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Member Name'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'join_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['max_visits_month'].required_when_shown = True
        for checkbox, (model, names) in self.tiers.items():
            existing = model.objects.filter(pk=self.instance.pk).first() if self.instance.pk else None
            if existing:
                self.fields[checkbox].initial = True
            for name in names:
                self.fields[name].toggled_by = checkbox
                if existing:
                    self.fields[name].initial = getattr(existing, name)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('is_standard') and not self.has_error('max_visits_month') \
                and cleaned.get('max_visits_month') is None:
            self.add_error('max_visits_month', 'Required for the Standard tier.')
        self._tier_rows = {}
        for checkbox, (model, names) in self.tiers.items():
            if not cleaned.get(checkbox):
                continue
            row = (model.objects.filter(pk=self.instance.pk).first() if self.instance.pk else None) or model()
            failed = [name for name in names if self.has_error(name)]
            for name in names:
                if name not in failed:
                    setattr(row, name, cleaned.get(name))
            try:
                row.full_clean(exclude=['member'] + failed)
            except ValidationError as e:
                self.add_error(None, e)
            self._tier_rows[checkbox] = row
        return cleaned

    def save(self, commit=True):
        with transaction.atomic():
            member = super().save()
            for checkbox, (model, _) in self.tiers.items():
                if checkbox in self._tier_rows:
                    row = self._tier_rows[checkbox]
                    row.member = member
                    row.save()
                else:
                    # Partial: unticking a tier removes that tier's row
                    model.objects.filter(pk=member.pk).delete()
        return member


class StandardMemberForm(forms.ModelForm):
    class Meta:
        model = StandardMember
        fields = ['member', 'max_visits_month']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'max_visits_month': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Visits per Month', 'min': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'member', Member.objects.filter(standard_profile__isnull=True))


class PremiumMemberForm(forms.ModelForm):
    class Meta:
        model = PremiumMember
        fields = ['member', 'assigned_trainer', 'priority_diet_access']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'assigned_trainer': forms.Select(attrs={'class': 'form-select'}),
            'priority_diet_access': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'member', Member.objects.filter(premium_profile__isnull=True))
        self.fields['assigned_trainer'].required = False


class PaymentForm(TotalSpecializationForm):
    discriminator = 'mode'
    parent_field = 'payment'
    subtypes = {
        'Cash': (CashPayment, ['receipt_no']),
        'Card': (CardPayment, ['card_last4', 'card_type']),
        'Online': (OnlinePayment, ['transaction_id', 'gateway']),
    }

    receipt_no = subtype_field('Receipt Number')
    card_last4 = subtype_field('Card Last 4 Digits')
    card_type = subtype_field('Card Type', choices=CardPayment.CARD_TYPE_CHOICES)
    transaction_id = subtype_field('Transaction ID')
    gateway = subtype_field('Gateway', choices=OnlinePayment.GATEWAY_CHOICES)

    class Meta:
        model = Payment
        fields = ['member', 'amount', 'pay_date', 'mode']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount (₹)', 'step': '0.01', 'min': '0'}),
            'pay_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mode': forms.Select(attrs={'class': 'form-select'}),
        }


class CashPaymentForm(forms.ModelForm):
    class Meta:
        model = CashPayment
        fields = ['payment', 'receipt_no']
        widgets = {
            'payment': forms.Select(attrs={'class': 'form-select'}),
            'receipt_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Receipt Number'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'payment', Payment.objects.filter(mode='Cash', cash_details__isnull=True))


class CardPaymentForm(forms.ModelForm):
    class Meta:
        model = CardPayment
        fields = ['payment', 'card_last4', 'card_type']
        widgets = {
            'payment': forms.Select(attrs={'class': 'form-select'}),
            'card_last4': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last 4 Digits', 'maxlength': '4'}),
            'card_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'payment', Payment.objects.filter(mode='Card', card_details__isnull=True))


class OnlinePaymentForm(forms.ModelForm):
    class Meta:
        model = OnlinePayment
        fields = ['payment', 'transaction_id', 'gateway']
        widgets = {
            'payment': forms.Select(attrs={'class': 'form-select'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction ID'}),
            'gateway': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_parent_choices(self, 'payment', Payment.objects.filter(mode='Online', online_details__isnull=True))


class LockerForm(forms.ModelForm):
    class Meta:
        model = Locker
        fields = ['member', 'locker_no']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'locker_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Locker Number'}),
        }


class GymClassForm(forms.ModelForm):
    class Meta:
        model = GymClass
        fields = ['trainer', 'name', 'capacity']
        widgets = {
            'trainer': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Class Name'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Capacity', 'min': '1'}),
        }


class ClassScheduleForm(forms.ModelForm):
    class Meta:
        model = ClassSchedule
        fields = ['gym_class', 'room', 'start_time', 'end_time']
        widgets = {
            'gym_class': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Room'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['member', 'schedule', 'date', 'in_time', 'status']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'schedule': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'in_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['member', 'rating', 'comments', 'date']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Rating (1-5)', 'min': '1', 'max': '5'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Comments', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class WorkoutPlanForm(forms.ModelForm):
    class Meta:
        model = WorkoutPlan
        fields = ['member', 'plan_name', 'duration', 'details', 'goal']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'plan_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Plan Name'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duration (days)', 'min': '1'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Details', 'rows': 3}),
            'goal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Goal'}),
        }


class DietPlanForm(forms.ModelForm):
    class Meta:
        model = DietPlan
        fields = ['trainer', 'member', 'calories', 'details']
        widgets = {
            'trainer': forms.Select(attrs={'class': 'form-select'}),
            'member': forms.Select(attrs={'class': 'form-select'}),
            'calories': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Calories', 'min': '0'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Details', 'rows': 3}),
        }


class EquipmentMaintenanceForm(forms.ModelForm):
    class Meta:
        model = EquipmentMaintenance
        fields = ['equipment', 'date', 'cost']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cost (₹)', 'step': '0.01', 'min': '0'}),
        }
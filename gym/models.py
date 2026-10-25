import calendar
from datetime import date
from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator

# Field-level rules checked on every create/edit (forms and admin run them via full_clean)
validate_name = RegexValidator(
    r"^[A-Za-z][A-Za-z .'-]*$",
    'Only letters, spaces, dots, apostrophes and hyphens are allowed (no digits or special characters).',
)
validate_phone = RegexValidator(r'^[6-9]\d{9}$', 'Enter a valid 10-digit mobile number starting with 6-9.')
validate_code = RegexValidator(r'^[A-Za-z0-9-]+$', 'Only letters, digits and hyphens are allowed.')
validate_room = RegexValidator(r'^[A-Za-z0-9][A-Za-z0-9 -]*$', 'Only letters, digits, spaces and hyphens are allowed.')
validate_last4 = RegexValidator(r'^\d{4}$', 'Enter exactly 4 digits.')


def validate_not_future(value):
    if value > date.today():
        raise ValidationError('Date cannot be in the future.')


def validate_dob(value):
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if not 10 <= age <= 100:
        raise ValidationError('Member must be between 10 and 100 years old.')


def add_months(start, months):
    """Return the date `months` calendar months after `start` (day clamped to month end)."""
    m = start.month - 1 + months
    year, month = start.year + m // 12, m % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def check_discriminator(parent, field, expected, subtype):
    """Disjoint specialization: a subtype row is only valid when the superclass discriminator matches."""
    actual = getattr(parent, field)
    if actual != expected:
        raise ValidationError(
            f"A {subtype} row requires {field} = '{expected}', but this record has {field} = '{actual}'."
        )


class Branch(models.Model):
    branch_id = models.AutoField(primary_key=True)
    branch_name = models.CharField(max_length=100, validators=[validate_name])
    location = models.CharField(max_length=200, validators=[validate_name])
    phone = models.CharField(max_length=20, validators=[validate_phone])

    class Meta:
        db_table = 'branch'
        constraints = [
            models.UniqueConstraint(fields=['phone'], name='branch_phone_unique'),
        ]

    def __str__(self):
        return f"{self.branch_name} ({self.location})"


class Staff(models.Model):
    ROLE_CHOICES = [
        ('Trainer', 'Trainer'),
        ('Receptionist', 'Receptionist'),
        ('Manager', 'Manager'),
        ('Maintenance_Staff', 'Maintenance Staff'),
    ]

    staff_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, validators=[validate_name])
    phone = models.CharField(max_length=20, validators=[validate_phone])
    salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='staff_members')

    class Meta:
        db_table = 'staff'
        constraints = [
            models.CheckConstraint(check=models.Q(salary__gt=0), name='staff_salary_positive'),
        ]

    def __str__(self):
        return f"{self.name} - {self.role}"


class Trainer(models.Model):
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, primary_key=True, related_name='trainer_profile')
    specialization = models.CharField(max_length=100, validators=[validate_name])
    experience = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)])

    class Meta:
        db_table = 'trainer'

    def clean(self):
        if self.staff_id:
            check_discriminator(self.staff, 'role', 'Trainer', 'Trainer')

    def __str__(self):
        return f"Trainer: {self.staff.name} - {self.specialization}"


class Receptionist(models.Model):
    SHIFT_CHOICES = [('Morning', 'Morning'), ('Evening', 'Evening'), ('Night', 'Night')]

    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, primary_key=True, related_name='receptionist_profile')
    shift_timing = models.CharField(max_length=50, choices=SHIFT_CHOICES)

    class Meta:
        db_table = 'receptionist'

    def clean(self):
        if self.staff_id:
            check_discriminator(self.staff, 'role', 'Receptionist', 'Receptionist')

    def __str__(self):
        return f"Receptionist: {self.staff.name} - {self.shift_timing}"


class Manager(models.Model):
    AUTHORITY_CHOICES = [('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')]

    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, primary_key=True, related_name='manager_profile')
    authority_level = models.CharField(max_length=50, choices=AUTHORITY_CHOICES)

    class Meta:
        db_table = 'manager'

    def clean(self):
        if self.staff_id:
            check_discriminator(self.staff, 'role', 'Manager', 'Manager')

    def __str__(self):
        return f"Manager: {self.staff.name} - {self.authority_level}"


class MaintenanceStaff(models.Model):
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, primary_key=True, related_name='maintenance_profile')
    skill_type = models.CharField(max_length=100, validators=[validate_name])

    class Meta:
        db_table = 'maintenance_staff'

    def clean(self):
        if self.staff_id:
            check_discriminator(self.staff, 'role', 'Maintenance_Staff', 'Maintenance_Staff')

    def __str__(self):
        return f"Maintenance: {self.staff.name} - {self.skill_type}"


class Equipment(models.Model):
    CATEGORY_CHOICES = [
        ('Cardio', 'Cardio'),
        ('Strength', 'Strength'),
        ('Other', 'Other'),
    ]

    equipment_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, validators=[validate_name])
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='equipment')

    class Meta:
        db_table = 'equipment'

    def __str__(self):
        return f"{self.name} ({self.category})"


class CardioEquipment(models.Model):
    equipment = models.OneToOneField(Equipment, on_delete=models.CASCADE, primary_key=True, related_name='cardio_details')
    max_speed = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    incline_levels = models.IntegerField(validators=[MinValueValidator(0)])

    class Meta:
        db_table = 'cardio_equipment'

    def clean(self):
        if self.equipment_id:
            check_discriminator(self.equipment, 'category', 'Cardio', 'Cardio_Equipment')

    def __str__(self):
        return f"Cardio: {self.equipment.name}"


class StrengthEquipment(models.Model):
    equipment = models.OneToOneField(Equipment, on_delete=models.CASCADE, primary_key=True, related_name='strength_details')
    weight_stack = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    max_load = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        db_table = 'strength_equipment'

    def clean(self):
        if self.equipment_id:
            check_discriminator(self.equipment, 'category', 'Strength', 'Strength_Equipment')

    def __str__(self):
        return f"Strength: {self.equipment.name}"


class MembershipPlan(models.Model):
    plan_id = models.AutoField(primary_key=True)
    plan_name = models.CharField(max_length=50, validators=[validate_name])
    duration = models.IntegerField(help_text="Duration in months",
                                   validators=[MinValueValidator(1), MaxValueValidator(36)])
    fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        db_table = 'membership_plan'
        constraints = [
            models.CheckConstraint(check=models.Q(fee__gt=0), name='plan_fee_positive'),
        ]

    def __str__(self):
        return f"{self.plan_name} - {self.duration} months - ₹{self.fee}"


class Member(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    member_id = models.AutoField(primary_key=True)
    # PROTECT: deleting a plan/branch must not silently delete its members (Lab 3 deletion anomaly)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='members')
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name='members')
    name = models.CharField(max_length=100, validators=[validate_name])
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    dob = models.DateField(validators=[validate_dob])
    phone = models.CharField(max_length=20, validators=[validate_phone])
    join_date = models.DateField(default=date.today, validators=[validate_not_future])

    class Meta:
        db_table = 'member'

    def __str__(self):
        return f"{self.name} (ID: {self.member_id})"

    def clean(self):
        if self.dob and self.join_date and self.join_date <= self.dob:
            raise ValidationError({'join_date': 'Join date must be after the date of birth.'})

    @property
    def expiry_date(self):
        return add_months(self.join_date, self.plan.duration)

    @property
    def is_active(self):
        return self.expiry_date >= date.today()


class StandardMember(models.Model):
    member = models.OneToOneField(Member, on_delete=models.CASCADE, primary_key=True, related_name='standard_profile')
    max_visits_month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])

    class Meta:
        db_table = 'standard_member'

    def __str__(self):
        return f"Standard Member: {self.member.name}"


class PremiumMember(models.Model):
    member = models.OneToOneField(Member, on_delete=models.CASCADE, primary_key=True, related_name='premium_profile')
    assigned_trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True, related_name='premium_members')
    priority_diet_access = models.BooleanField(default=True)

    class Meta:
        db_table = 'premium_member'

    def __str__(self):
        return f"Premium Member: {self.member.name}"


class Payment(models.Model):
    MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Online', 'Online'),
    ]

    payment_id = models.AutoField(primary_key=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    pay_date = models.DateField(validators=[validate_not_future])
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)

    class Meta:
        db_table = 'payment'
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name='payment_amount_positive'),
        ]

    def clean(self):
        if self.member_id and self.pay_date and self.pay_date < self.member.join_date:
            raise ValidationError({'pay_date': "Payment date cannot be before the member's join date."})

    def __str__(self):
        return f"Payment {self.payment_id} - {self.member.name} - ₹{self.amount}"


class CashPayment(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, primary_key=True, related_name='cash_details')
    receipt_no = models.CharField(max_length=50, unique=True, validators=[validate_code])

    class Meta:
        db_table = 'cash_payment'

    def clean(self):
        if self.payment_id:
            check_discriminator(self.payment, 'mode', 'Cash', 'Cash_Payment')

    def __str__(self):
        return f"Cash Payment: {self.receipt_no}"


class CardPayment(models.Model):
    CARD_TYPE_CHOICES = [('Visa', 'Visa'), ('MasterCard', 'MasterCard'), ('RuPay', 'RuPay'), ('Amex', 'Amex')]

    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, primary_key=True, related_name='card_details')
    card_last4 = models.CharField(max_length=4, validators=[validate_last4])
    card_type = models.CharField(max_length=50, choices=CARD_TYPE_CHOICES)

    class Meta:
        db_table = 'card_payment'

    def clean(self):
        if self.payment_id:
            check_discriminator(self.payment, 'mode', 'Card', 'Card_Payment')

    def __str__(self):
        return f"Card Payment: ****{self.card_last4} ({self.card_type})"


class OnlinePayment(models.Model):
    GATEWAY_CHOICES = [('Razorpay', 'Razorpay'), ('PayPal', 'PayPal'), ('Paytm', 'Paytm'),
                       ('PhonePe', 'PhonePe'), ('Google Pay', 'Google Pay')]

    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, primary_key=True, related_name='online_details')
    transaction_id = models.CharField(max_length=100, unique=True, validators=[validate_code])
    gateway = models.CharField(max_length=50, choices=GATEWAY_CHOICES)

    class Meta:
        db_table = 'online_payment'

    def clean(self):
        if self.payment_id:
            check_discriminator(self.payment, 'mode', 'Online', 'Online_Payment')

    def __str__(self):
        return f"Online Payment: {self.transaction_id} via {self.gateway}"


class Locker(models.Model):
    locker_id = models.AutoField(primary_key=True)
    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name='locker')
    locker_no = models.CharField(max_length=20, unique=True, validators=[validate_code])

    class Meta:
        db_table = 'locker'

    def __str__(self):
        return f"Locker {self.locker_no} - {self.member.name}"


class GymClass(models.Model):
    class_id = models.AutoField(primary_key=True)
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='classes')
    name = models.CharField(max_length=100, validators=[validate_name])
    capacity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])

    class Meta:
        db_table = 'gym_classes'
        constraints = [
            models.CheckConstraint(check=models.Q(capacity__gt=0), name='class_capacity_positive'),
        ]

    def __str__(self):
        return f"{self.name} by {self.trainer.staff.name}"


class ClassSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    gym_class = models.ForeignKey(GymClass, on_delete=models.CASCADE, related_name='schedules')
    room = models.CharField(max_length=50, validators=[validate_room])
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = 'class_schedule'

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after the start time.'})

    def __str__(self):
        return f"{self.gym_class.name} - {self.room} - {self.start_time} to {self.end_time}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
    ]

    attendance_id = models.AutoField(primary_key=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='attendance_records')
    schedule = models.ForeignKey(ClassSchedule, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(validators=[validate_not_future])
    in_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        db_table = 'attendance'
        constraints = [
            models.UniqueConstraint(fields=['member', 'schedule', 'date'], name='attendance_once_per_session'),
        ]

    def clean(self):
        if self.member_id and self.date and self.date < self.member.join_date:
            raise ValidationError({'date': "Attendance date cannot be before the member's join date."})
        if self.schedule_id and self.date:
            booked = Attendance.objects.filter(schedule_id=self.schedule_id, date=self.date).exclude(pk=self.pk)
            if booked.count() >= self.schedule.gym_class.capacity:
                raise ValidationError(f'This class is full on {self.date} '
                                      f'(capacity {self.schedule.gym_class.capacity}).')

    def __str__(self):
        return f"{self.member.name} - {self.date} - {self.status}"


class Feedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True)
    date = models.DateField(default=date.today, validators=[validate_not_future])

    class Meta:
        db_table = 'feedback'
        constraints = [
            models.CheckConstraint(check=models.Q(rating__gte=1, rating__lte=5), name='feedback_rating_1_to_5'),
        ]

    def clean(self):
        if self.member_id and self.date and self.date < self.member.join_date:
            raise ValidationError({'date': "Feedback date cannot be before the member's join date."})

    def __str__(self):
        return f"Feedback from {self.member.name} - Rating: {self.rating}"


class WorkoutPlan(models.Model):
    workout_id = models.AutoField(primary_key=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='workout_plans')
    plan_name = models.CharField(max_length=100, validators=[validate_name])
    duration = models.IntegerField(help_text="Duration in days",
                                   validators=[MinValueValidator(1), MaxValueValidator(365)])
    details = models.TextField()
    goal = models.CharField(max_length=200, validators=[validate_name])

    class Meta:
        db_table = 'workout_plan'

    def __str__(self):
        return f"{self.plan_name} for {self.member.name}"


class DietPlan(models.Model):
    diet_id = models.AutoField(primary_key=True)
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='diet_plans')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='diet_plans')
    calories = models.IntegerField(validators=[MinValueValidator(800), MaxValueValidator(6000)])
    details = models.TextField()

    class Meta:
        db_table = 'diet_plan'

    def __str__(self):
        return f"Diet Plan for {self.member.name} by {self.trainer.staff.name}"


class EquipmentMaintenance(models.Model):
    maintenance_id = models.AutoField(primary_key=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_records')
    date = models.DateField(validators=[validate_not_future])
    cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        db_table = 'equipment_maintenance'

    def __str__(self):
        return f"Maintenance for {self.equipment.name} on {self.date} - ₹{self.cost}"
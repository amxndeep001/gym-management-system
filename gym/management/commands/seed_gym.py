"""Load the Lab 2b sample data, plus a modest amount of generated demo data.

    python manage.py seed_gym           # idempotent: safe to run repeatedly
    python manage.py seed_gym --reset   # wipe all gym tables first
"""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from gym.models import (
    Branch, Staff, Trainer, Receptionist, Manager, MaintenanceStaff,
    Equipment, CardioEquipment, StrengthEquipment,
    MembershipPlan, Member, StandardMember, PremiumMember,
    Payment, CashPayment, CardPayment, OnlinePayment,
    Locker, GymClass, ClassSchedule, Attendance, Feedback,
    WorkoutPlan, DietPlan, EquipmentMaintenance,
)

# ---------------------------------------------------------------------------
# Lab 2b sample data (exactly as in the report, with the corrections noted)
# ---------------------------------------------------------------------------
BRANCHES = [
    (1, 'FitZone Central', 'Chennai', '9876543210'),
    (2, 'FitZone North', 'Bangalore', '9876543211'),
    (3, 'FitZone South', 'Hyderabad', '9876543212'),
    (4, 'FitZone East', 'Kolkata', '9876543213'),
    (5, 'FitZone West', 'Mumbai', '9876543214'),
]

STAFF = [  # id, name, phone, salary, role, branch
    (101, 'Arjun Kumar', '9000000001', 35000, 'Trainer', 1),
    (102, 'Priya Sharma', '9000000002', 30000, 'Receptionist', 1),
    (103, 'Rahul Singh', '9000000003', 50000, 'Manager', 2),
    (104, 'Neha Verma', '9000000004', 28000, 'Maintenance_Staff', 2),
    (105, 'Vikram Patel', '9000000005', 38000, 'Trainer', 3),
    (106, 'Anjali Rao', '9000000006', 32000, 'Receptionist', 3),
    (107, 'Karan Mehta', '9000000007', 36000, 'Trainer', 4),
    (108, 'Sneha Kapoor', '9000000008', 31000, 'Receptionist', 4),
    (109, 'Rohit Nair', '9000000009', 52000, 'Manager', 5),
    (110, 'Pooja Iyer', '9000000010', 29000, 'Maintenance_Staff', 5),
    (111, 'Aakash Jain', '9000000011', 37000, 'Trainer', 1),
    (112, 'Meera Das', '9000000012', 29000, 'Maintenance_Staff', 3),
    (113, 'Dev Malhotra', '9000000013', 39000, 'Trainer', 5),
]
TRAINERS = [(101, 'Strength Training', 5), (105, 'Yoga and Fitness', 4), (107, 'Cardio Training', 6),
            (111, 'Weight Loss', 5), (113, 'CrossFit', 7)]
# Correction: the report also listed 104 and 110 as receptionists, but they are maintenance staff
# (a disjoint specialization allows only one subtype per staff member).
RECEPTIONISTS = [(102, 'Morning'), (106, 'Evening'), (108, 'Morning')]
MANAGERS = [(103, 'High'), (109, 'High')]
MAINTENANCE = [(104, 'Electrical'), (110, 'Mechanical'), (112, 'Equipment Repair')]

EQUIPMENT = [(201, 1, 'Treadmill', 'Cardio'), (202, 2, 'Exercise Bike', 'Cardio'),
             (203, 3, 'Bench Press', 'Strength'), (204, 4, 'Dumbbell Set', 'Strength'),
             (205, 5, 'Elliptical', 'Cardio')]
CARDIO = [(201, 20, 10), (202, 15, 5), (205, 18, 8)]
STRENGTH = [(203, 100, 150), (204, 50, 80)]

PLANS = [(301, 'Monthly', 1, 1500), (302, 'Quarterly', 3, 4000), (303, 'Half Yearly', 6, 7500),
         (304, 'Annual', 12, 14000), (305, 'Premium Annual', 12, 20000)]

MEMBERS = [  # id, branch, plan, name, gender, dob, phone, join_date
    (401, 1, 301, 'Aman Gupta', 'M', '2000-05-12', '9100000001', '2026-01-10'),
    (402, 1, 302, 'Riya Mehta', 'F', '1999-08-20', '9100000002', '2026-01-15'),
    (403, 2, 303, 'Karan Singh', 'M', '1998-03-18', '9100000003', '2026-02-05'),
    (404, 2, 304, 'Sneha Kapoor', 'F', '2001-11-25', '9100000004', '2026-02-20'),
    (405, 3, 301, 'Rohit Sharma', 'M', '1997-07-09', '9100000005', '2026-03-01'),
    (406, 3, 302, 'Pooja Nair', 'F', '2000-12-14', '9100000006', '2026-03-10'),
    (407, 4, 303, 'Aditya Rao', 'M', '1999-06-17', '9100000007', '2026-03-15'),
    (408, 4, 305, 'Nisha Jain', 'F', '2002-02-28', '9100000008', '2026-03-18'),
    (409, 5, 304, 'Varun Das', 'M', '1998-09-11', '9100000009', '2026-03-20'),
    (410, 5, 305, 'Megha Iyer', 'F', '2001-04-22', '9100000010', '2026-03-25'),
]
STANDARD = [(401, 20), (402, 20), (405, 20), (407, 20), (409, 20)]
PREMIUM = [(403, 101), (404, 105), (406, 107), (408, 111), (410, 113)]  # member, assigned trainer

PAYMENTS = [  # id, member, amount, date, mode
    (501, 401, 1500, '2026-01-10', 'Cash'), (502, 402, 4000, '2026-01-15', 'Card'),
    (503, 403, 7500, '2026-02-05', 'Online'), (504, 404, 14000, '2026-02-20', 'Card'),
    (505, 405, 1500, '2026-03-01', 'Cash'), (506, 406, 4000, '2026-03-10', 'Online'),
    (507, 407, 7500, '2026-03-15', 'Card'), (508, 408, 20000, '2026-03-18', 'Online'),
    (509, 409, 14000, '2026-03-20', 'Cash'), (510, 410, 20000, '2026-03-25', 'Card'),
]
CARDS = [(502, '1234', 'Visa'), (504, '5678', 'MasterCard'), (507, '9012', 'Visa'), (510, '3456', 'Visa')]
ONLINE = [(503, 'TXN10001', 'Razorpay'), (506, 'TXN10002', 'Razorpay'), (508, 'TXN10003', 'PayPal')]
# Correction: the report had no Cash_Payment rows, which breaks Disjoint + Total for 501, 505, 509.
CASH = [(501, 'RCPT-2026-0501'), (505, 'RCPT-2026-0505'), (509, 'RCPT-2026-0509')]

LOCKERS = [(601, 401, '101'), (602, 402, '102'), (603, 403, '103'), (604, 404, '104'), (605, 405, '105')]
CLASSES = [(701, 101, 'Strength Training', 20), (702, 105, 'Yoga', 25), (703, 107, 'Cardio Blast', 30),
           (704, 111, 'Weight Loss', 20), (705, 113, 'CrossFit', 15)]
SCHEDULES = [(801, 701, 'Room A', '07:00', '08:00'), (802, 702, 'Room B', '09:00', '10:00'),
             (803, 703, 'Room C', '18:00', '19:00'), (804, 704, 'Room D', '17:00', '18:00'),
             (805, 705, 'Room E', '19:00', '20:00')]
ATTENDANCE = [
    (901, 401, 801, '2026-04-01', '07:05', 'Present'), (902, 402, 801, '2026-04-01', '07:10', 'Present'),
    (903, 403, 802, '2026-04-02', '09:05', 'Present'), (904, 404, 802, '2026-04-02', '09:15', 'Present'),
    (905, 405, 803, '2026-04-03', '18:05', 'Present'), (906, 406, 803, '2026-04-03', '18:10', 'Absent'),
    (907, 407, 804, '2026-04-04', '17:05', 'Present'), (908, 408, 804, '2026-04-04', '17:10', 'Present'),
    (909, 409, 805, '2026-04-05', '19:05', 'Present'), (910, 410, 805, '2026-04-05', '19:10', 'Absent'),
]
FEEDBACK = [(1001, 401, 5, 'Excellent facilities', '2026-04-10'), (1002, 402, 4, 'Good trainers', '2026-04-11'),
            (1003, 403, 5, 'Very clean gym', '2026-04-12'), (1004, 404, 4, 'Good equipment', '2026-04-13'),
            (1005, 405, 5, 'Great atmosphere', '2026-04-14')]
WORKOUTS = [
    (1101, 401, 'Beginner Strength', 60, 'Full body exercises', 'Muscle Gain'),
    (1102, 402, 'Weight Loss', 45, 'Cardio and light weights', 'Weight Loss'),
    (1103, 403, 'Advanced Strength', 75, 'Heavy compound exercises', 'Muscle Gain'),
    (1104, 404, 'Fitness Plan', 60, 'Mixed cardio and strength', 'General Fitness'),
    (1105, 405, 'Cardio Plan', 45, 'Running and cycling', 'Endurance'),
]
DIETS = [(1201, 101, 403, 2500, 'High protein muscle gain diet'), (1202, 105, 404, 2000, 'Balanced diet'),
         (1203, 107, 406, 1800, 'Low calorie weight loss diet'), (1204, 111, 408, 1900, 'High protein fitness diet'),
         (1205, 113, 410, 2300, 'Muscle building diet')]
MAINTENANCE_LOG = [(1301, 201, '2026-04-01', 2500), (1302, 202, '2026-04-02', 1800),
                   (1303, 203, '2026-04-03', 2200), (1304, 204, '2026-04-04', 1500),
                   (1305, 205, '2026-04-05', 2000)]

# ---------------------------------------------------------------------------
# Generated demo data (fixed seed, so every run produces the same data)
# ---------------------------------------------------------------------------
RANDOM_SEED = 2026
EXTRA_MEMBER_START = 411
EXTRA_NAMES = [
    ('Ishaan Verma', 'M'), ('Ananya Reddy', 'F'), ('Kabir Malhotra', 'M'), ('Diya Menon', 'F'),
    ('Arnav Joshi', 'M'), ('Saanvi Pillai', 'F'), ('Vihaan Chopra', 'M'), ('Myra Bhatia', 'F'),
    ('Reyansh Kulkarni', 'M'), ('Aadhya Saxena', 'F'), ('Atharv Desai', 'M'), ('Kiara Sinha', 'F'),
    ('Shaurya Bose', 'M'), ('Avni Chatterjee', 'F'), ('Dhruv Agarwal', 'M'), ('Tara Krishnan', 'F'),
    ('Yash Thakur', 'M'), ('Navya Ghosh', 'F'), ('Rudra Pandey', 'M'), ('Zara Qureshi', 'F'),
    ('Aryan Mishra', 'M'), ('Ira Banerjee', 'F'), ('Krish Shetty', 'M'), ('Riya Dutta', 'F'),
    ('Laksh Arora', 'M'), ('Meher Gill', 'F'), ('Om Tiwari', 'M'), ('Sara Fernandes', 'F'),
    ('Veer Rathore', 'M'), ('Anika Hegde', 'F'),
]
OTHER_EQUIPMENT = [(206, 1, 'Yoga Mat Set'), (207, 2, 'Foam Rollers'), (208, 3, 'Resistance Bands'),
                   (209, 4, 'Battle Ropes')]
PLAN_WEIGHTS = {301: 30, 302: 25, 303: 20, 304: 15, 305: 10}
TIER_WEIGHTS = {'standard': 40, 'premium': 30, 'both': 10, 'none': 20}
PAYMENT_MODES = ['Online', 'Card', 'Cash']  # cycled so every month has all three modes
EXTRA_COMMENTS = {
    5: ['Loved the CrossFit sessions', 'Trainers are very supportive', 'Best gym in the area'],
    4: ['Good equipment, a bit crowded in the evening', 'Clean changing rooms', 'Helpful staff'],
    3: ['Average, needs more cardio machines', 'AC not working sometimes'],
    2: ['Classes often start late'],
    1: ['Locker was broken for a week'],
}

GYM_MODELS_DELETE_ORDER = [
    Attendance, Feedback, WorkoutPlan, DietPlan, Locker,
    CashPayment, CardPayment, OnlinePayment, Payment,
    StandardMember, PremiumMember, Member,
    EquipmentMaintenance, CardioEquipment, StrengthEquipment, Equipment,
    ClassSchedule, GymClass, Trainer, Receptionist, Manager, MaintenanceStaff, Staff,
    MembershipPlan, Branch,
]


def d(value):
    return date.fromisoformat(value)


def t(value):
    return time.fromisoformat(value)


def upsert(model, pk, **fields):
    model.objects.update_or_create(pk=pk, defaults=fields)


def weighted(rng, weights):
    return rng.choices(list(weights), weights=list(weights.values()))[0]


class Command(BaseCommand):
    help = 'Load the Lab 2b sample data plus generated demo data (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete all gym data before seeding.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            for model in GYM_MODELS_DELETE_ORDER:
                model.objects.all().delete()
            self.stdout.write('Deleted existing gym data.')

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', '', 'admin123')
            self.stdout.write('Created login admin / admin123.')

        self.load_report_data()
        self.stdout.write('Loaded Lab 2b report data.')

        if Member.objects.filter(pk=EXTRA_MEMBER_START).exists():
            self.stdout.write('Generated demo data already present; skipped (use --reset to regenerate).')
        else:
            self.load_extra_data(random.Random(RANDOM_SEED), date.today())
            self.stdout.write('Generated extra demo data.')

        counts = ', '.join(f'{m._meta.verbose_name_plural}: {m.objects.count()}'
                           for m in (Member, Payment, Attendance, Feedback))
        self.stdout.write(self.style.SUCCESS(f'Done. {counts}'))

    def load_report_data(self):
        for pk, name, location, phone in BRANCHES:
            upsert(Branch, pk, branch_name=name, location=location, phone=phone)
        for pk, name, phone, salary, role, branch in STAFF:
            upsert(Staff, pk, name=name, phone=phone, salary=salary, role=role, branch_id=branch)
        for pk, spec, exp in TRAINERS:
            upsert(Trainer, pk, specialization=spec, experience=exp)
        for pk, shift in RECEPTIONISTS:
            upsert(Receptionist, pk, shift_timing=shift)
        for pk, level in MANAGERS:
            upsert(Manager, pk, authority_level=level)
        for pk, skill in MAINTENANCE:
            upsert(MaintenanceStaff, pk, skill_type=skill)

        for pk, branch, name, category in EQUIPMENT:
            upsert(Equipment, pk, branch_id=branch, name=name, category=category)
        for pk, speed, incline in CARDIO:
            upsert(CardioEquipment, pk, max_speed=speed, incline_levels=incline)
        for pk, stack, load in STRENGTH:
            upsert(StrengthEquipment, pk, weight_stack=stack, max_load=load)

        for pk, name, duration, fee in PLANS:
            upsert(MembershipPlan, pk, plan_name=name, duration=duration, fee=fee)
        for pk, branch, plan, name, gender, dob, phone, joined in MEMBERS:
            upsert(Member, pk, branch_id=branch, plan_id=plan, name=name, gender=gender,
                   dob=d(dob), phone=phone, join_date=d(joined))
        for pk, visits in STANDARD:
            upsert(StandardMember, pk, max_visits_month=visits)
        for pk, trainer in PREMIUM:
            upsert(PremiumMember, pk, assigned_trainer_id=trainer, priority_diet_access=True)

        for pk, member, amount, paid, mode in PAYMENTS:
            upsert(Payment, pk, member_id=member, amount=amount, pay_date=d(paid), mode=mode)
        for pk, last4, card_type in CARDS:
            upsert(CardPayment, pk, card_last4=last4, card_type=card_type)
        for pk, txn, gateway in ONLINE:
            upsert(OnlinePayment, pk, transaction_id=txn, gateway=gateway)
        for pk, receipt in CASH:
            upsert(CashPayment, pk, receipt_no=receipt)

        for pk, member, number in LOCKERS:
            upsert(Locker, pk, member_id=member, locker_no=number)
        for pk, trainer, name, capacity in CLASSES:
            upsert(GymClass, pk, trainer_id=trainer, name=name, capacity=capacity)
        for pk, gym_class, room, start, end in SCHEDULES:
            upsert(ClassSchedule, pk, gym_class_id=gym_class, room=room, start_time=t(start), end_time=t(end))
        for pk, member, schedule, day, in_time, status in ATTENDANCE:
            upsert(Attendance, pk, member_id=member, schedule_id=schedule, date=d(day),
                   in_time=t(in_time), status=status)
        for pk, member, rating, comments, day in FEEDBACK:
            upsert(Feedback, pk, member_id=member, rating=rating, comments=comments, date=d(day))
        for pk, member, name, duration, details, goal in WORKOUTS:
            upsert(WorkoutPlan, pk, member_id=member, plan_name=name, duration=duration, details=details, goal=goal)
        for pk, trainer, member, calories, details in DIETS:
            upsert(DietPlan, pk, trainer_id=trainer, member_id=member, calories=calories, details=details)
        for pk, equipment, day, cost in MAINTENANCE_LOG:
            upsert(EquipmentMaintenance, pk, equipment_id=equipment, date=d(day), cost=cost)

    def load_extra_data(self, rng, today):
        for pk, branch, name in OTHER_EQUIPMENT:
            Equipment.objects.create(pk=pk, branch_id=branch, name=name, category='Other')

        plans = {p.pk: p for p in MembershipPlan.objects.all()}
        trainers_by_branch = {}
        for trainer in Trainer.objects.select_related('staff'):
            trainers_by_branch.setdefault(trainer.staff.branch_id, []).append(trainer.pk)
        all_trainers = [pk for pks in trainers_by_branch.values() for pk in pks]

        # ~30 members joining evenly over the last 6 months, each paying their plan fee on joining
        members = []
        payment_id = 511
        for i, (name, gender) in enumerate(EXTRA_NAMES):
            pk = EXTRA_MEMBER_START + i
            joined = today - timedelta(days=int(i * 180 / len(EXTRA_NAMES)) + rng.randint(0, 5))
            plan = plans[weighted(rng, PLAN_WEIGHTS)]
            branch = rng.randint(1, 5)
            member = Member.objects.create(
                pk=pk, branch_id=branch, plan=plan, name=name, gender=gender,
                dob=date(rng.randint(1985, 2006), rng.randint(1, 12), rng.randint(1, 28)),
                phone=f'91000{pk:05d}', join_date=joined,
            )
            members.append(member)

            # MEMBER is Overlapping + Partial: standard, premium, both or neither
            tier = weighted(rng, TIER_WEIGHTS)
            if tier in ('standard', 'both'):
                StandardMember.objects.create(member=member, max_visits_month=rng.choice([12, 16, 20]))
            if tier in ('premium', 'both'):
                trainer = rng.choice(trainers_by_branch.get(branch, all_trainers))
                PremiumMember.objects.create(member=member, assigned_trainer_id=trainer,
                                             priority_diet_access=rng.random() < 0.7)

            # PAYMENT is Disjoint + Total: every payment gets exactly one subtype row
            mode = PAYMENT_MODES[i % len(PAYMENT_MODES)]
            payment = Payment.objects.create(pk=payment_id, member=member, amount=plan.fee,
                                             pay_date=joined, mode=mode)
            if mode == 'Cash':
                CashPayment.objects.create(payment=payment, receipt_no=f'RCPT-{joined.year}-{payment_id:04d}')
            elif mode == 'Card':
                CardPayment.objects.create(payment=payment, card_last4=f'{rng.randint(0, 9999):04d}',
                                           card_type=rng.choice(['Visa', 'MasterCard', 'RuPay']))
            else:
                OnlinePayment.objects.create(payment=payment, transaction_id=f'TXN{20000 + payment_id}',
                                             gateway=rng.choice(['Razorpay', 'PayPal', 'Paytm']))
            payment_id += 1

        # Four weeks of class attendance (Mon-Sat), never more records than the class capacity
        everyone = list(Member.objects.all())
        schedules = list(ClassSchedule.objects.select_related('gym_class'))
        records = []
        attendance_id = 911
        for offset in range(27, -1, -1):
            day = today - timedelta(days=offset)
            if day.weekday() == 6:
                continue
            eligible = [m for m in everyone if m.join_date <= day]
            for schedule in schedules:
                capacity = schedule.gym_class.capacity
                count = min(len(eligible), round(capacity * rng.uniform(0.35, 0.9)))
                for member in rng.sample(eligible, count):
                    status = weighted(rng, {'Present': 80, 'Late': 12, 'Absent': 8})
                    late = rng.randint(10, 20) if status == 'Late' else rng.randint(-5, 5)
                    start = datetime.combine(day, schedule.start_time)
                    records.append(Attendance(
                        attendance_id=attendance_id, member=member, schedule=schedule, date=day,
                        in_time=(start + timedelta(minutes=late)).time(), status=status,
                    ))
                    attendance_id += 1
        Attendance.objects.bulk_create(records)

        # Feedback from about half of the new members
        feedback_id = 1006
        for member in rng.sample(members, 15):
            rating = weighted(rng, {5: 35, 4: 35, 3: 18, 2: 8, 1: 4})
            days_since_join = (today - member.join_date).days
            Feedback.objects.create(
                pk=feedback_id, member=member, rating=rating, comments=rng.choice(EXTRA_COMMENTS[rating]),
                date=member.join_date + timedelta(days=rng.randint(0, days_since_join)),
            )
            feedback_id += 1

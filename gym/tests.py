from datetime import date, time, timedelta
from io import StringIO

from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from .forms import (
    AttendanceForm, BranchForm, ClassScheduleForm, EquipmentForm, MemberForm, PaymentForm, PremiumMemberForm,
    StaffForm, StandardMemberForm, TrainerForm,
)
from .models import (
    Attendance, Branch, CardioEquipment, CardPayment, CashPayment, ClassSchedule, Equipment, Feedback, GymClass,
    Manager, MaintenanceStaff, Member,
    MembershipPlan, OnlinePayment, Payment, PremiumMember, Receptionist, Staff, StandardMember, StrengthEquipment,
    Trainer,
)
from .views import NAV_SECTIONS, gym_progress


class GymDataMixin:
    def setUp(self):
        self.branch = Branch.objects.create(branch_name='FitZone Central', location='Chennai', phone='9876543210')
        self.plan = MembershipPlan.objects.create(plan_name='Monthly', duration=1, fee=1500)
        self.member = Member.objects.create(branch=self.branch, plan=self.plan, name='Aman Gupta', gender='M',
                                            dob=date(2000, 5, 12), phone='9100000001', join_date=date(2026, 1, 10))
        self.staff = Staff.objects.create(name='Arjun Kumar', phone='9000000001', salary=35000,
                                          role='Trainer', branch=self.branch)
        self.trainer = Trainer.objects.create(staff=self.staff, specialization='Strength Training', experience=5)


class CheckConstraintTests(GymDataMixin, TestCase):
    """Lab 3 domain constraints are enforced by the database, not just by forms."""

    def assertRejected(self, create):
        with self.assertRaises(IntegrityError), transaction.atomic():
            create()

    def test_fee_must_be_positive(self):
        self.assertRejected(lambda: MembershipPlan.objects.create(plan_name='Bad', duration=1, fee=-500))

    def test_salary_must_be_positive(self):
        self.assertRejected(lambda: Staff.objects.create(name='X', phone='9000000101', salary=0, role='Manager',
                                                         branch=self.branch))

    def test_amount_must_be_positive(self):
        self.assertRejected(lambda: Payment.objects.create(member=self.member, amount=0,
                                                           pay_date=date(2026, 1, 1), mode='Cash'))

    def test_capacity_must_be_positive(self):
        self.assertRejected(lambda: GymClass.objects.create(trainer=self.trainer, name='Yoga', capacity=0))

    def test_rating_between_1_and_5(self):
        self.assertRejected(lambda: Feedback.objects.create(member=self.member, rating=6))
        self.assertRejected(lambda: Feedback.objects.create(member=self.member, rating=0))
        Feedback.objects.create(member=self.member, rating=5)

    def test_branch_phone_unique(self):
        self.assertRejected(lambda: Branch.objects.create(branch_name='Copy', location='Pune', phone='9876543210'))


class ProtectDeleteTests(GymDataMixin, TestCase):
    def test_plan_with_members_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.plan.delete()
        self.assertTrue(Member.objects.filter(pk=self.member.pk).exists())

    def test_branch_with_members_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.branch.delete()

    def test_dashboard_shows_friendly_message(self):
        User.objects.create_user('admin', password='admin123')
        self.client.login(username='admin', password='admin123')
        response = self.client.post(f'/dashboard/?entity=membership_plan&action=delete&pk={self.plan.pk}', follow=True)
        message = str(list(response.context['messages'])[0])
        self.assertIn('Cannot delete', message)
        self.assertIn('Aman Gupta', message)
        self.assertTrue(MembershipPlan.objects.filter(pk=self.plan.pk).exists())


class OverlappingMemberTierTests(GymDataMixin, TestCase):
    """MEMBER is Overlapping + Partial."""

    def member_form(self, instance=None, **tiers):
        data = {'branch': self.branch.pk, 'plan': self.plan.pk, 'name': 'Riya Mehta', 'gender': 'F',
                'dob': '1999-08-20', 'phone': '9100000002', 'join_date': '2026-01-15', **tiers}
        return MemberForm(data, instance=instance)

    def test_member_form_saves_both_tiers_together(self):
        form = self.member_form(is_standard='on', max_visits_month=20, is_premium='on',
                                assigned_trainer=self.trainer.pk, priority_diet_access='on')
        self.assertTrue(form.is_valid(), form.errors)
        member = form.save()
        self.assertEqual(StandardMember.objects.get(pk=member.pk).max_visits_month, 20)
        self.assertEqual(PremiumMember.objects.get(pk=member.pk).assigned_trainer, self.trainer)

    def test_member_form_with_no_tier(self):
        form = self.member_form()
        self.assertTrue(form.is_valid(), form.errors)
        member = form.save()
        self.assertFalse(StandardMember.objects.filter(pk=member.pk).exists())
        self.assertFalse(PremiumMember.objects.filter(pk=member.pk).exists())

    def test_standard_tier_requires_valid_max_visits(self):
        self.assertIn('max_visits_month', self.member_form(is_standard='on').errors)
        self.assertIn('max_visits_month', self.member_form(is_standard='on', max_visits_month=40).errors)
        self.assertFalse(Member.objects.filter(name='Riya Mehta').exists())

    def test_unticking_a_tier_removes_it(self):
        StandardMember.objects.create(member=self.member, max_visits_month=20)
        data = {'branch': self.branch.pk, 'plan': self.plan.pk, 'name': self.member.name, 'gender': 'M',
                'dob': '2000-05-12', 'phone': self.member.phone, 'join_date': '2026-01-10', 'is_premium': 'on'}
        self.assertTrue(MemberForm(instance=self.member).fields['is_standard'].initial)
        form = MemberForm(data, instance=self.member)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertFalse(StandardMember.objects.filter(pk=self.member.pk).exists())
        self.assertTrue(PremiumMember.objects.filter(pk=self.member.pk).exists())

    def test_member_can_hold_both_tiers(self):
        StandardMember.objects.create(member=self.member, max_visits_month=20)
        form = PremiumMemberForm({'member': self.member.pk, 'assigned_trainer': self.trainer.pk,
                                  'priority_diet_access': True})
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertTrue(StandardMember.objects.filter(member=self.member).exists())
        self.assertTrue(PremiumMember.objects.filter(member=self.member).exists())

    def test_premium_member_can_be_added_to_standard_tier(self):
        PremiumMember.objects.create(member=self.member)
        self.assertIn(self.member, StandardMemberForm().fields['member'].queryset)

    def test_member_with_no_tier_is_allowed(self):
        self.assertFalse(hasattr(self.member, 'standard_profile') or hasattr(self.member, 'premium_profile'))

    def test_editing_a_tier_keeps_its_member(self):
        standard = StandardMember.objects.create(member=self.member, max_visits_month=20)
        form = StandardMemberForm({'max_visits_month': 12}, instance=standard)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        standard.refresh_from_db()
        self.assertEqual(standard.max_visits_month, 12)


class SubtypeDiscriminatorTests(GymDataMixin, TestCase):
    """STAFF and PAYMENT are Disjoint + Total; the discriminator decides the subtype."""

    def test_subtype_must_match_discriminator(self):
        receptionist = Staff.objects.create(name='Priya', phone='9000000102', salary=30000, role='Receptionist',
                                            branch=self.branch)
        with self.assertRaises(ValidationError):
            Trainer(staff=receptionist, specialization='Yoga', experience=1).full_clean()
        Receptionist(staff=receptionist, shift_timing='Morning').full_clean()

    def test_staff_form_saves_superclass_and_subtype_together(self):
        form = StaffForm({'name': 'Rahul', 'phone': '9000000103', 'salary': 50000, 'role': 'Manager',
                          'branch': self.branch.pk, 'authority_level': 'High'})
        self.assertTrue(form.is_valid(), form.errors)
        staff = form.save()
        self.assertEqual(Manager.objects.get(pk=staff.pk).authority_level, 'High')

    def test_staff_form_requires_subtype_fields(self):
        form = StaffForm({'name': 'Neha', 'phone': '9000000104', 'salary': 28000, 'role': 'Maintenance_Staff',
                          'branch': self.branch.pk})
        self.assertFalse(form.is_valid())
        self.assertIn('skill_type', form.errors)
        self.assertFalse(Staff.objects.filter(name='Neha').exists())

    def test_role_change_moves_the_subtype_row(self):
        form = StaffForm({'name': self.staff.name, 'phone': self.staff.phone, 'salary': 35000,
                          'role': 'Maintenance_Staff', 'branch': self.branch.pk, 'skill_type': 'Electrical'},
                         instance=self.staff)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertFalse(Trainer.objects.filter(pk=self.staff.pk).exists())
        self.assertTrue(MaintenanceStaff.objects.filter(pk=self.staff.pk).exists())

    def test_payment_form_saves_exactly_one_subtype(self):
        form = PaymentForm({'member': self.member.pk, 'amount': 1500, 'pay_date': '2026-01-10', 'mode': 'Online',
                            'transaction_id': 'TXN1', 'gateway': 'Razorpay'})
        self.assertTrue(form.is_valid(), form.errors)
        payment = form.save()
        self.assertTrue(OnlinePayment.objects.filter(pk=payment.pk).exists())
        self.assertFalse(CashPayment.objects.filter(pk=payment.pk).exists())
        self.assertFalse(CardPayment.objects.filter(pk=payment.pk).exists())

    def test_editing_a_subtype_keeps_its_superclass_in_the_dropdown(self):
        form = TrainerForm({'specialization': 'Powerlifting', 'experience': 6}, instance=self.trainer)
        self.assertIn(self.staff, form.fields['staff'].queryset)
        self.assertTrue(form.is_valid(), form.errors)

    def test_total_subtypes_cannot_be_created_or_deleted_on_their_own(self):
        User.objects.create_user('admin', password='admin123')
        self.client.login(username='admin', password='admin123')
        page = self.client.get('/dashboard/?entity=trainer').content.decode()
        self.assertNotIn('action=create" class="btn btn-primary"', page)
        self.assertNotIn("confirmDelete('", page)
        self.client.post(f'/dashboard/?entity=trainer&action=delete&pk={self.trainer.pk}')
        self.assertTrue(Trainer.objects.filter(pk=self.trainer.pk).exists())
        response = self.client.post('/ajax/create/cash_payment/', {})
        self.assertFalse(response.json()['success'])


class FieldValidationTests(GymDataMixin, TestCase):
    """Every create form rejects malformed input (names, phones, codes, dates)."""

    def member_form(self, **overrides):
        data = {'branch': self.branch.pk, 'plan': self.plan.pk, 'name': 'Riya Mehta', 'gender': 'F',
                'dob': '1999-08-20', 'phone': '9100000002', 'join_date': '2026-01-15'}
        data.update(overrides)
        return MemberForm(data)

    def test_valid_member_is_accepted(self):
        self.assertTrue(self.member_form().is_valid())
        self.assertTrue(self.member_form(name="Anil D'Souza").is_valid())

    def test_name_rejects_digits_and_special_characters(self):
        for bad in ['Riya123', 'Riya@Mehta', '12345', '#$%', ' -Riya']:
            form = self.member_form(name=bad)
            self.assertFalse(form.is_valid(), bad)
            self.assertIn('name', form.errors)

    def test_phone_must_be_10_digit_mobile(self):
        for bad in ['12345', '1234567890', '98765abcde', '+919876543210', '98765 43210']:
            form = self.member_form(phone=bad)
            self.assertFalse(form.is_valid(), bad)
            self.assertIn('phone', form.errors)

    def test_dates_cannot_be_in_the_future(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertIn('dob', self.member_form(dob=tomorrow).errors)
        self.assertIn('join_date', self.member_form(join_date=tomorrow).errors)

    def test_join_date_after_dob(self):
        self.assertIn('dob', self.member_form(dob='2026-01-01', join_date='2026-01-15').errors)

    def test_staff_and_branch_text_fields(self):
        staff = StaffForm({'name': 'R2D2', 'phone': '9000000105', 'salary': 30000, 'role': 'Trainer',
                           'branch': self.branch.pk, 'specialization': 'Yoga!', 'experience': 3})
        self.assertFalse(staff.is_valid())
        self.assertIn('name', staff.errors)
        self.assertIn('specialization', staff.errors)
        branch = BranchForm({'branch_name': 'FitZone 2', 'location': 'Pune', 'phone': '9876500000'})
        self.assertIn('branch_name', branch.errors)

    def test_payment_subtype_fields_are_validated(self):
        form = PaymentForm({'member': self.member.pk, 'amount': 1500, 'pay_date': '2026-02-01', 'mode': 'Card',
                            'card_last4': '12ab', 'card_type': 'Bitcoin'})
        self.assertFalse(form.is_valid())
        self.assertIn('card_last4', form.errors)
        self.assertIn('card_type', form.errors)

    def test_payment_cannot_predate_join_date(self):
        form = PaymentForm({'member': self.member.pk, 'amount': 1500, 'pay_date': '2025-12-31', 'mode': 'Cash',
                            'receipt_no': 'RCPT-1'})
        self.assertIn('pay_date', form.errors)

    def test_schedule_must_end_after_it_starts(self):
        gym_class = GymClass.objects.create(trainer=self.trainer, name='Yoga', capacity=10)
        form = ClassScheduleForm({'gym_class': gym_class.pk, 'room': 'Room A', 'start_time': '09:00',
                                  'end_time': '08:00'})
        self.assertIn('end_time', form.errors)

    def test_attendance_respects_class_capacity(self):
        gym_class = GymClass.objects.create(trainer=self.trainer, name='Yoga', capacity=1)
        schedule = ClassSchedule.objects.create(gym_class=gym_class, room='Room A',
                                                start_time=time(9), end_time=time(10))
        Attendance.objects.create(member=self.member, schedule=schedule, date=date(2026, 2, 1),
                                  in_time=time(9, 5), status='Present')
        other = Member.objects.create(branch=self.branch, plan=self.plan, name='Riya Mehta', gender='F',
                                      dob=date(1999, 8, 20), phone='9100000002', join_date=date(2026, 1, 15))
        form = AttendanceForm({'member': other.pk, 'schedule': schedule.pk, 'date': '2026-02-01',
                               'in_time': '09:05', 'status': 'Present'})
        self.assertFalse(form.is_valid())
        self.assertIn('full', str(form.non_field_errors()))


class SeedCommandTests(TestCase):
    def seed(self, *args):
        call_command('seed_gym', *args, stdout=StringIO())

    def test_seed_runs_cleanly_and_is_idempotent(self):
        self.seed()
        counts = (Member.objects.count(), Payment.objects.count(), Staff.objects.count())
        self.seed()
        self.assertEqual(counts, (Member.objects.count(), Payment.objects.count(), Staff.objects.count()))
        self.seed('--reset')
        self.assertEqual(counts, (Member.objects.count(), Payment.objects.count(), Staff.objects.count()))

        self.assertTrue(User.objects.filter(username='admin').exists())
        self.assertEqual(set(Receptionist.objects.values_list('pk', flat=True)), {102, 106, 108})
        self.assertEqual(set(CashPayment.objects.filter(pk__lte=510).values_list('pk', flat=True)), {501, 505, 509})
        self.assertEqual(Member.objects.filter(pk__range=(401, 410)).count(), 10)

        # All seeded rows, including the report data, pass the same validation as the forms
        for model in apps.get_app_config('gym').get_models():
            if model is not Attendance:  # 1,600+ generated rows; covered by the class capacity test
                for obj in model.objects.all():
                    obj.full_clean()

        # Disjoint + Total: every staff member and every payment has exactly one subtype row
        staff_subtypes = ('trainer_profile', 'receptionist_profile', 'manager_profile', 'maintenance_profile')
        for staff in Staff.objects.all():
            self.assertEqual(sum(hasattr(staff, r) for r in staff_subtypes), 1, staff)
        for payment in Payment.objects.all():
            self.assertEqual(sum(hasattr(payment, r) for r in ('cash_details', 'card_details', 'online_details')),
                             1, payment)


class LoggedInMixin(GymDataMixin):
    def setUp(self):
        super().setUp()
        User.objects.create_user('admin', password='admin123')
        self.client.login(username='admin', password='admin123')

    def list_page(self, query):
        return self.client.get(f'/dashboard/?{query}').context['object_list']


class NavigationTests(LoggedInMixin, TestCase):
    """Top navbar, Home page and section landing pages."""

    def test_login_redirects_to_home(self):
        self.client.logout()
        response = self.client.post('/login/', {'username': 'admin', 'password': 'admin123'})
        self.assertRedirects(response, '/home/')
        self.assertContains(self.client.get('/home/'), 'Welcome back')

    def test_root_redirects_to_home(self):
        self.assertRedirects(self.client.get('/'), '/home/')

    def test_every_section_page_loads(self):
        for section in NAV_SECTIONS:
            if section['items']:
                response = self.client.get(f"/section/{section['key']}/")
                self.assertEqual(response.status_code, 200, section['key'])
        self.assertEqual(self.client.get('/section/nope/').status_code, 404)

    def test_branch_staff_section_links_to_staff_subtypes(self):
        page = self.client.get('/section/branch_staff/').content.decode()
        self.assertIn('Staff Specializations (Disjoint, Total)', page)
        for key in ('trainer', 'receptionist', 'manager', 'maintenance_staff'):
            self.assertIn(f'?entity={key}&action=list', page)

    def test_subtype_pages_point_to_the_superclass_form(self):
        page = self.client.get('/dashboard/?entity=trainer&action=list').content.decode()
        self.assertIn('?entity=staff&action=create&role=Trainer', page)
        form = self.client.get('/dashboard/?entity=staff&action=create&role=Trainer').context['form']
        self.assertEqual(form['role'].value(), 'Trainer')

    def test_filtered_subtypes_are_not_linked_from_navigation(self):
        hidden = ['standard_member', 'premium_member', 'cardio_equipment', 'strength_equipment',
                  'cash_payment', 'card_payment', 'online_payment']
        pages = ['/home/', '/analytics/'] + [f"/section/{s['key']}/" for s in NAV_SECTIONS if s['items']]
        pages += ['/dashboard/?entity=member&action=list', '/dashboard/?entity=equipment&action=list',
                  '/dashboard/?entity=payment&action=list']
        for url in pages:
            page = self.client.get(url).content.decode()
            for key in hidden:
                self.assertNotIn(f'entity={key}&', page, f'{key} linked from {url}')
        # ...but their URLs still work
        self.assertEqual(self.client.get('/dashboard/?entity=cash_payment&action=list').status_code, 200)


class ListFilterTests(LoggedInMixin, TestCase):
    """Superclass list pages filter by subtype through a query parameter."""

    def test_equipment_category_filter(self):
        cardio = Equipment.objects.create(name='Treadmill', category='Cardio', branch=self.branch)
        Equipment.objects.create(name='Bench Press', category='Strength', branch=self.branch)
        Equipment.objects.create(name='Yoga Mat', category='Other', branch=self.branch)
        self.assertEqual(list(self.list_page('entity=equipment&action=list&category=Cardio')), [cardio])
        self.assertEqual(len(self.list_page('entity=equipment&action=list')), 3)

    def test_payment_mode_filter(self):
        card = Payment.objects.create(member=self.member, amount=1500, pay_date=date(2026, 2, 1), mode='Card')
        Payment.objects.create(member=self.member, amount=1500, pay_date=date(2026, 3, 1), mode='Cash')
        self.assertEqual(list(self.list_page('entity=payment&action=list&mode=Card')), [card])

    def test_member_tier_filter_both(self):
        both = Member.objects.create(branch=self.branch, plan=self.plan, name='Riya Mehta', gender='F',
                                     dob=date(1999, 8, 20), phone='9100000002', join_date=date(2026, 1, 15))
        StandardMember.objects.create(member=both, max_visits_month=20)
        PremiumMember.objects.create(member=both)
        StandardMember.objects.create(member=self.member, max_visits_month=10)
        self.assertEqual(list(self.list_page('entity=member&action=list&tier=both')), [both])
        self.assertEqual(len(self.list_page('entity=member&action=list&tier=standard')), 2)


class EquipmentSpecializationTests(GymDataMixin, TestCase):
    """EQUIPMENT is Disjoint + Partial: Cardio, Strength, or no subtype (Accessories)."""

    def equipment_form(self, instance=None, **data):
        return EquipmentForm({'name': 'Treadmill', 'branch': self.branch.pk, **data}, instance=instance)

    def saved_cardio(self):
        form = self.equipment_form(category='Cardio', max_speed=18, incline_levels=12)
        self.assertTrue(form.is_valid(), form.errors)
        return form.save()

    def test_cardio_saves_equipment_and_subtype(self):
        form = self.equipment_form(category='Cardio', max_speed='18.5', incline_levels=12)
        self.assertTrue(form.is_valid(), form.errors)
        equipment = form.save()
        self.assertEqual(CardioEquipment.objects.get(pk=equipment.pk).incline_levels, 12)
        self.assertFalse(StrengthEquipment.objects.filter(pk=equipment.pk).exists())

    def test_switching_to_accessories_deletes_the_cardio_row(self):
        equipment = self.saved_cardio()
        form = self.equipment_form(instance=equipment, category='Other')
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(Equipment.objects.get(pk=equipment.pk).category, 'Other')
        self.assertFalse(CardioEquipment.objects.filter(pk=equipment.pk).exists())

    def test_switching_category_moves_the_subtype_row(self):
        equipment = self.saved_cardio()
        form = self.equipment_form(instance=equipment, category='Strength', weight_stack=90, max_load=150)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertFalse(CardioEquipment.objects.filter(pk=equipment.pk).exists())
        self.assertTrue(StrengthEquipment.objects.filter(pk=equipment.pk).exists())

    def test_accessories_have_no_subtype_row(self):
        form = self.equipment_form(name='Yoga Mat', category='Other')
        self.assertTrue(form.is_valid(), form.errors)
        equipment = form.save()
        self.assertFalse(CardioEquipment.objects.filter(pk=equipment.pk).exists())
        self.assertFalse(StrengthEquipment.objects.filter(pk=equipment.pk).exists())
        self.assertEqual(equipment.get_category_display(), 'Accessories')

    def test_subtype_fields_are_required_for_their_category(self):
        form = self.equipment_form(category='Strength', weight_stack=90)
        self.assertFalse(form.is_valid())
        self.assertIn('max_load', form.errors)
        self.assertFalse(Equipment.objects.exists())


class GymProgressTests(GymDataMixin, TestCase):
    def test_twelve_months_with_cumulative_members(self):
        Member.objects.create(branch=self.branch, plan=self.plan, name='Riya Mehta', gender='F',
                              dob=date(1999, 8, 20), phone='9100000002', join_date=date(2026, 3, 2))
        Payment.objects.create(member=self.member, amount=1500, pay_date=date(2026, 1, 10), mode='Cash')
        Payment.objects.create(member=self.member, amount=500, pay_date=date(2026, 1, 20), mode='Card')
        progress = gym_progress(date(2026, 6, 15))

        self.assertEqual(len(progress['labels']), 12)
        self.assertEqual((progress['labels'][0], progress['labels'][-1]), ('Jul 2025', 'Jun 2026'))
        members = progress['members']
        self.assertEqual(len(members), 12)
        self.assertTrue(all(a <= b for a, b in zip(members, members[1:])))
        # Aman joined in Jan 2026 and Riya in Mar 2026; months with no data stay at 0
        self.assertEqual(members[5:9], [0, 1, 1, 2])
        self.assertEqual(progress['revenue'][6], 2000)
        self.assertEqual(progress['revenue'][7], 0)

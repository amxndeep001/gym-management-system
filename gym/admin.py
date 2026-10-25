from django.contrib import admin
from .models import (
    Branch, Staff, Trainer, Receptionist, Manager, MaintenanceStaff,
    Equipment, CardioEquipment, StrengthEquipment,
    MembershipPlan, Member, StandardMember, PremiumMember,
    Payment, CashPayment, CardPayment, OnlinePayment,
    Locker, GymClass, ClassSchedule, Attendance, Feedback,
    WorkoutPlan, DietPlan, EquipmentMaintenance
)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['branch_id', 'branch_name', 'location', 'phone']
    search_fields = ['branch_name', 'location']
    list_filter = ['location']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'name', 'phone', 'salary', 'role', 'branch']
    search_fields = ['name', 'phone']
    list_filter = ['role', 'branch']
    raw_id_fields = ['branch']


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ['staff', 'specialization', 'experience']
    search_fields = ['staff__name', 'specialization']
    raw_id_fields = ['staff']


@admin.register(Receptionist)
class ReceptionistAdmin(admin.ModelAdmin):
    list_display = ['staff', 'shift_timing']
    search_fields = ['staff__name']
    raw_id_fields = ['staff']


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ['staff', 'authority_level']
    search_fields = ['staff__name']
    raw_id_fields = ['staff']


@admin.register(MaintenanceStaff)
class MaintenanceStaffAdmin(admin.ModelAdmin):
    list_display = ['staff', 'skill_type']
    search_fields = ['staff__name']
    raw_id_fields = ['staff']


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['equipment_id', 'name', 'category', 'branch']
    search_fields = ['name']
    list_filter = ['category', 'branch']
    raw_id_fields = ['branch']


@admin.register(CardioEquipment)
class CardioEquipmentAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'max_speed', 'incline_levels']
    raw_id_fields = ['equipment']


@admin.register(StrengthEquipment)
class StrengthEquipmentAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'weight_stack', 'max_load']
    raw_id_fields = ['equipment']


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ['plan_id', 'plan_name', 'duration', 'fee']
    search_fields = ['plan_name']


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['member_id', 'name', 'gender', 'phone', 'join_date', 'branch', 'plan']
    search_fields = ['name', 'phone']
    list_filter = ['gender', 'branch', 'plan']
    raw_id_fields = ['branch', 'plan']
    date_hierarchy = 'join_date'


@admin.register(StandardMember)
class StandardMemberAdmin(admin.ModelAdmin):
    list_display = ['member', 'max_visits_month']
    raw_id_fields = ['member']


@admin.register(PremiumMember)
class PremiumMemberAdmin(admin.ModelAdmin):
    list_display = ['member', 'assigned_trainer', 'priority_diet_access']
    raw_id_fields = ['member', 'assigned_trainer']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'member', 'amount', 'pay_date', 'mode']
    search_fields = ['member__name']
    list_filter = ['mode', 'pay_date']
    raw_id_fields = ['member']
    date_hierarchy = 'pay_date'


@admin.register(CashPayment)
class CashPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment', 'receipt_no']
    search_fields = ['receipt_no']
    raw_id_fields = ['payment']


@admin.register(CardPayment)
class CardPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment', 'card_last4', 'card_type']
    raw_id_fields = ['payment']


@admin.register(OnlinePayment)
class OnlinePaymentAdmin(admin.ModelAdmin):
    list_display = ['payment', 'transaction_id', 'gateway']
    search_fields = ['transaction_id']
    raw_id_fields = ['payment']


@admin.register(Locker)
class LockerAdmin(admin.ModelAdmin):
    list_display = ['locker_id', 'member', 'locker_no']
    search_fields = ['locker_no']
    raw_id_fields = ['member']


@admin.register(GymClass)
class GymClassAdmin(admin.ModelAdmin):
    list_display = ['class_id', 'trainer', 'name', 'capacity']
    search_fields = ['name']
    raw_id_fields = ['trainer']


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ['schedule_id', 'gym_class', 'room', 'start_time', 'end_time']
    raw_id_fields = ['gym_class']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['attendance_id', 'member', 'schedule', 'date', 'in_time', 'status']
    list_filter = ['status', 'date']
    raw_id_fields = ['member', 'schedule']
    date_hierarchy = 'date'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['feedback_id', 'member', 'rating', 'date']
    list_filter = ['rating', 'date']
    raw_id_fields = ['member']
    date_hierarchy = 'date'


@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ['workout_id', 'member', 'plan_name', 'duration', 'goal']
    search_fields = ['plan_name', 'goal']
    raw_id_fields = ['member']


@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ['diet_id', 'trainer', 'member', 'calories']
    raw_id_fields = ['trainer', 'member']


@admin.register(EquipmentMaintenance)
class EquipmentMaintenanceAdmin(admin.ModelAdmin):
    list_display = ['maintenance_id', 'equipment', 'date', 'cost']
    raw_id_fields = ['equipment']
    date_hierarchy = 'date'
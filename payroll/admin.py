from django.contrib import admin

from .models import Employee, PayrollComponent, PayrollEntry, PayrollEntryItem, PayrollPeriod, School, User


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "school")
    list_filter = ("role", "school")
    search_fields = ("username", "email")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "nip", "school", "employee_type", "is_active")
    list_filter = ("employee_type", "school")
    search_fields = ("full_name", "email", "nip")


@admin.register(PayrollComponent)
class PayrollComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "component_type", "is_fixed", "is_active")
    list_filter = ("component_type", "is_fixed", "school")
    search_fields = ("name", "code")


class PayrollEntryItemInline(admin.TabularInline):
    model = PayrollEntryItem
    extra = 0


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ("school", "month", "year", "status")
    list_filter = ("school", "status")
    search_fields = ("school__name",)


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ("employee", "period", "net_pay", "status")
    list_filter = ("period__school", "status")
    search_fields = ("employee__full_name",)
    inlines = [PayrollEntryItemInline]

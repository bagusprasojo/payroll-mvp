from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone


class School(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    ROLE_SUPER_ADMIN = "super_admin"
    ROLE_SCHOOL_ADMIN = "school_admin"
    ROLE_EMPLOYEE = "employee"

    ROLE_CHOICES = [
        (ROLE_SUPER_ADMIN, "Super Admin"),
        (ROLE_SCHOOL_ADMIN, "Admin Sekolah"),
        (ROLE_EMPLOYEE, "Pegawai"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_SCHOOL_ADMIN)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")

    def is_school_admin(self) -> bool:
        return self.role == self.ROLE_SCHOOL_ADMIN


class Employee(models.Model):
    TYPE_TEACHER = "teacher"
    TYPE_STAFF = "staff"
    EMPLOYEE_TYPES = [
        (TYPE_TEACHER, "Guru"),
        (TYPE_STAFF, "Karyawan"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="employees")
    full_name = models.CharField(max_length=255)
    nip = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField()
    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPES)
    position = models.CharField(max_length=150, blank=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_profile")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "email"], name="unique_school_email"),
            models.UniqueConstraint(
                fields=["school", "nip"],
                condition=~Q(nip__isnull=True),
                name="unique_school_nip",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} - {self.school.name}"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        if self.nip:
            self.nip = self.nip.strip() or None
        super().save(*args, **kwargs)


class PayrollComponent(models.Model):
    TYPE_EARNING = "earning"
    TYPE_DEDUCTION = "deduction"
    COMPONENT_TYPES = [
        (TYPE_EARNING, "Pendapatan"),
        (TYPE_DEDUCTION, "Potongan"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="components")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPES)
    is_fixed = models.BooleanField(default=True)
    default_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("school", "code")

    def __str__(self) -> str:
        return f"{self.name} ({self.get_component_type_display()})"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)


class PayrollPeriod(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_FINAL = "final"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_FINAL, "Final"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="periods")
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    generated_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_periods"
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="finalized_periods"
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month"]
        unique_together = ("school", "month", "year")

    def __str__(self) -> str:
        return f"{self.school.name} {self.month:02d}/{self.year}"

    @property
    def label(self) -> str:
        return f"{self.month:02d}/{self.year}"

    def mark_generated(self, user: User | None = None) -> None:
        self.generated_at = timezone.now()
        if user:
            self.generated_by = user
        self.save(update_fields=["generated_at", "generated_by", "updated_at"])

    def finalize(self, user: User | None = None) -> None:
        self.status = self.STATUS_FINAL
        self.finalized_at = timezone.now()
        if user:
            self.finalized_by = user
        self.save(update_fields=["status", "finalized_at", "finalized_by", "updated_at"])


class PayrollEntry(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_FINAL = "final"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_FINAL, "Final"),
    ]

    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name="entries")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payroll_entries")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("period", "employee")
        ordering = ["employee__full_name"]

    def __str__(self) -> str:
        return f"{self.employee.full_name} - {self.period.label}"

    def recalculate_totals(self) -> None:
        items = self.items.all()
        earnings = sum((item.amount for item in items if item.component_type == PayrollComponent.TYPE_EARNING), Decimal("0"))
        deductions = sum(
            (item.amount for item in items if item.component_type == PayrollComponent.TYPE_DEDUCTION), Decimal("0")
        )
        self.total_earnings = earnings
        self.total_deductions = deductions
        self.net_pay = earnings - deductions
        self.save(update_fields=["total_earnings", "total_deductions", "net_pay", "updated_at"])


class PayrollEntryItem(models.Model):
    entry = models.ForeignKey(PayrollEntry, on_delete=models.CASCADE, related_name="items")
    component = models.ForeignKey(PayrollComponent, on_delete=models.PROTECT)
    component_name = models.CharField(max_length=255)
    component_type = models.CharField(max_length=20, choices=PayrollComponent.COMPONENT_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["component_name"]

    def save(self, *args, **kwargs):
        if not self.component_name:
            self.component_name = self.component.name
        if not self.component_type:
            self.component_type = self.component.component_type
        super().save(*args, **kwargs)
        self.entry.recalculate_totals()

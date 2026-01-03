from django.core.management.base import BaseCommand

from payroll.models import Employee, PayrollComponent, PayrollPeriod, School, User
from payroll.services import generate_payroll


class Command(BaseCommand):
    help = "Membuat data demo untuk sistem payroll."

    def handle(self, *args, **options):
        school, _ = School.objects.get_or_create(
            code="SCH001",
            defaults={
                "name": "Sekolah Nusantara",
                "address": "Jl. Pendidikan No. 1",
            },
        )

        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@sekolah.test",
                "role": User.ROLE_SCHOOL_ADMIN,
                "school": school,
            },
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("User admin/admin123 dibuat."))
        else:
            self.stdout.write("User admin sudah ada.")

        components = [
            ("Gaji Pokok", "GPOK", PayrollComponent.TYPE_EARNING, True, "5000000"),
            ("Tunjangan Transport", "TRANS", PayrollComponent.TYPE_EARNING, False, "500000"),
            ("Potongan BPJS", "BPJS", PayrollComponent.TYPE_DEDUCTION, True, "200000"),
        ]
        for name, code, comp_type, is_fixed, amount in components:
            PayrollComponent.objects.update_or_create(
                school=school,
                code=code,
                defaults={
                    "name": name,
                    "component_type": comp_type,
                    "is_fixed": is_fixed,
                    "default_amount": amount,
                    "is_active": True,
                },
            )

        employees = [
            ("Ani Prasetyo", "1987010101", "ani@sekolah.test", Employee.TYPE_TEACHER, "Guru IPA", "5200000"),
            ("Budi Santoso", "1988020202", "budi@sekolah.test", Employee.TYPE_STAFF, "Staf TU", "4500000"),
        ]
        for full_name, nip, email, emp_type, position, base_salary in employees:
            Employee.objects.update_or_create(
                school=school,
                email=email,
                defaults={
                    "full_name": full_name,
                    "nip": nip,
                    "employee_type": emp_type,
                    "position": position,
                    "base_salary": base_salary,
                    "is_active": True,
                },
            )

        period, _ = PayrollPeriod.objects.get_or_create(school=school, month=1, year=2025)
        if not period.entries.exists():
            generate_payroll(period=period, method="manual", school=school, user=admin_user)
            self.stdout.write(self.style.SUCCESS("Payroll periode 01/2025 digenerate."))
        else:
            self.stdout.write("Payroll periode 01/2025 sudah ada.")

        self.stdout.write(self.style.SUCCESS("Data demo siap digunakan."))

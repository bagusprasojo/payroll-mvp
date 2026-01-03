from __future__ import annotations

from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Sum
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .forms import (
    EmployeeForm,
    PayrollComponentForm,
    PayrollEntryItemFormSet,
    PayrollEntryItemAddForm,
    PayrollEntryAddForm,
    PayrollGenerateForm,
    PayrollPeriodForm,
)
from .models import Employee, PayrollComponent, PayrollEntry, PayrollEntryItem, PayrollPeriod
from .services import PayrollGenerationError, generate_payroll, add_employee_payroll_entry


def _school_guard(request):
    if not request.user.is_school_admin() or not request.user.school:
        return HttpResponseForbidden("Akses hanya untuk admin sekolah.")
    return request.user.school


@login_required
def dashboard(request):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school

    employee_count = school.employees.count()
    component_count = school.components.count()
    latest_period = school.periods.order_by("-year", "-month").first()
    total_payroll = 0
    if latest_period:
        total_payroll = latest_period.entries.aggregate(total=Sum("net_pay"))["total"] or 0

    context = {
        "school": school,
        "employee_count": employee_count,
        "component_count": component_count,
        "latest_period": latest_period,
        "total_payroll": total_payroll,
    }
    return render(request, "payroll/dashboard.html", context)


@login_required
def employee_list(request):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    employees = school.employees.all()
    return render(request, "payroll/employee_list.html", {"employees": employees})


@login_required
def employee_create(request):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.school = school
            employee.save()
            messages.success(request, "Pegawai berhasil ditambahkan.")
            return redirect("employee_list")
    else:
        form = EmployeeForm()
    return render(request, "payroll/employee_form.html", {"form": form, "title": "Tambah Pegawai"})


@login_required
def employee_edit(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    employee = get_object_or_404(Employee, pk=pk, school=school)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Data pegawai diperbarui.")
            return redirect("employee_list")
    else:
        form = EmployeeForm(instance=employee)
    return render(request, "payroll/employee_form.html", {"form": form, "title": "Edit Pegawai"})


@login_required
@require_POST
def employee_delete(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    employee = get_object_or_404(Employee, pk=pk, school=school)
    employee.delete()
    messages.success(request, "Pegawai dihapus.")
    return redirect("employee_list")


@login_required
def component_list(request):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    components = school.components.all()
    return render(request, "payroll/component_list.html", {"components": components})


@login_required
def component_create(request):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    if request.method == "POST":
        form = PayrollComponentForm(request.POST)
        if form.is_valid():
            component = form.save(commit=False)
            component.school = school
            component.save()
            messages.success(request, "Komponen gaji ditambahkan.")
            return redirect("component_list")
    else:
        form = PayrollComponentForm()
    return render(request, "payroll/component_form.html", {"form": form, "title": "Tambah Komponen"})


@login_required
def component_edit(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    component = get_object_or_404(PayrollComponent, pk=pk, school=school)
    if request.method == "POST":
        form = PayrollComponentForm(request.POST, instance=component)
        if form.is_valid():
            form.save()
            messages.success(request, "Komponen diperbarui.")
            return redirect("component_list")
    else:
        form = PayrollComponentForm(instance=component)
    return render(request, "payroll/component_form.html", {"form": form, "title": "Edit Komponen"})


@login_required
@require_POST
def component_delete(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    component = get_object_or_404(PayrollComponent, pk=pk, school=school)
    component.delete()
    messages.success(request, "Komponen dihapus.")
    return redirect("component_list")


@login_required
def period_list(request):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    periods = school.periods.all()
    return render(request, "payroll/period_list.html", {"periods": periods})


@login_required
def period_create(request):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    if request.method == "POST":
        form = PayrollPeriodForm(request.POST, school=school)
        if form.is_valid():
            period = form.save(commit=False)
            period.school = school
            period.save()
            messages.success(request, "Periode gaji dibuat.")
            return redirect("period_list")
    else:
        form = PayrollPeriodForm(school=school)
    return render(request, "payroll/period_form.html", {"form": form})


@login_required
def period_detail(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=pk, school=school)
    entries = period.entries.select_related("employee").all()
    return render(request, "payroll/period_detail.html", {"period": period, "entries": entries})


@login_required
def period_add_entry(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=pk, school=school)
    if period.status != PayrollPeriod.STATUS_DRAFT:
        messages.error(request, "Hanya periode draft yang dapat ditambahkan gaji.")
        return redirect("period_detail", pk=pk)
    form = PayrollEntryAddForm(request.POST or None, school=school, period=period)
    if request.method == "POST" and form.is_valid():
        employee = form.cleaned_data["employee"]
        try:
            add_employee_payroll_entry(period=period, employee=employee, school=school)
            messages.success(request, f"Gaji untuk {employee.full_name} ditambahkan.")
            return redirect("period_detail", pk=pk)
        except PayrollGenerationError as exc:
            messages.error(request, str(exc))
    return render(request, "payroll/period_add_entry.html", {"form": form, "period": period})


@login_required
def period_generate(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=pk, school=school)
    if period.status == PayrollPeriod.STATUS_FINAL:
        messages.info(request, "Periode sudah final.")
        return redirect("period_detail", pk=pk)
    form = PayrollGenerateForm(request.POST or None, request.FILES or None, school=school)
    if request.method == "POST" and form.is_valid():
        method = form.cleaned_data["method"]
        source_period = form.cleaned_data.get("source_period")
        upload_file = form.cleaned_data.get("upload_file")
        try:
            generate_payroll(
                period=period,
                method=method,
                school=school,
                user=request.user,
                source_period=source_period,
                upload_file=upload_file,
            )
            messages.success(request, "Payroll berhasil digenerate.")
            return redirect("period_detail", pk=period.pk)
        except PayrollGenerationError as exc:
            messages.error(request, str(exc))
    return render(request, "payroll/period_generate.html", {"form": form, "period": period})


@login_required
@require_POST
def period_finalize(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=pk, school=school)
    if period.status == PayrollPeriod.STATUS_FINAL:
        messages.info(request, "Periode sudah final.")
        return redirect("period_detail", pk=pk)
    period.finalize(request.user)
    PayrollEntry.objects.filter(period=period).update(status=PayrollEntry.STATUS_FINAL, updated_at=timezone.now())
    messages.success(request, "Periode berhasil difinalisasi.")
    return redirect("period_detail", pk=pk)


@login_required
@require_POST
def period_cancel(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=pk, school=school)
    if period.status != PayrollPeriod.STATUS_FINAL:
        messages.error(request, "Periode belum final.")
        return redirect("period_list")
    period.status = PayrollPeriod.STATUS_DRAFT
    period.finalized_at = None
    period.finalized_by = None
    period.save(update_fields=["status", "finalized_at", "finalized_by", "updated_at"])
    PayrollEntry.objects.filter(period=period).update(status=PayrollEntry.STATUS_DRAFT, updated_at=timezone.now())
    messages.success(request, "Finalisasi periode dibatalkan.")
    return redirect("period_list")


@login_required
@require_POST
def period_delete(request, pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=pk, school=school)
    if period.status == PayrollPeriod.STATUS_FINAL:
        messages.error(request, "Periode final tidak dapat dihapus.")
        return redirect("period_list")
    period.delete()
    messages.success(request, "Periode berhasil dihapus.")
    return redirect("period_list")


@login_required
def payroll_entry_detail(request, period_pk, entry_pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=period_pk, school=school)
    entry = get_object_or_404(PayrollEntry, pk=entry_pk, period=period)
    editable = period.status == PayrollPeriod.STATUS_DRAFT
    if request.method == "POST" and editable:
        formset = PayrollEntryItemFormSet(request.POST, instance=entry)
        if formset.is_valid():
            formset.save()
            entry.recalculate_totals()
            messages.success(request, "Nominal gaji diperbarui.")
            return redirect("payroll_entry_detail", period_pk=period.pk, entry_pk=entry.pk)
    else:
        formset = PayrollEntryItemFormSet(instance=entry)
    earning_forms = [
        form for form in formset.forms if form.instance.component_type == PayrollComponent.TYPE_EARNING
    ]
    deduction_forms = [
        form for form in formset.forms if form.instance.component_type == PayrollComponent.TYPE_DEDUCTION
    ]
    earning_items = entry.items.filter(component_type=PayrollComponent.TYPE_EARNING)
    deduction_items = entry.items.filter(component_type=PayrollComponent.TYPE_DEDUCTION)
    earning_add_form = PayrollEntryItemAddForm(
        school=school,
        component_type=PayrollComponent.TYPE_EARNING,
        prefix="earn_add",
    )
    deduction_add_form = PayrollEntryItemAddForm(
        school=school,
        component_type=PayrollComponent.TYPE_DEDUCTION,
        prefix="ded_add",
    )
    return render(
        request,
        "payroll/entry_detail.html",
        {
            "period": period,
            "entry": entry,
            "formset": formset,
            "editable": editable,
            "earning_forms": earning_forms,
            "deduction_forms": deduction_forms,
            "earning_items": earning_items,
            "deduction_items": deduction_items,
            "earning_add_form": earning_add_form,
            "deduction_add_form": deduction_add_form,
        },
    )


@login_required
def payroll_entry_pdf(request, period_pk, entry_pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=period_pk, school=school)
    entry = get_object_or_404(PayrollEntry, pk=entry_pk, period=period)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 30 * mm
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(20 * mm, y, f"Slip Gaji - {period.label}")
    y -= 10 * mm
    pdf.setFont("Helvetica", 11)
    pdf.drawString(20 * mm, y, f"Pegawai : {entry.employee.full_name}")
    y -= 7 * mm
    pdf.drawString(20 * mm, y, f"Jenis    : {entry.employee.get_employee_type_display()}")
    y -= 7 * mm
    pdf.drawString(20 * mm, y, f"Periode  : {period.label}")
    y -= 12 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Rincian Pendapatan")
    pdf.setFont("Helvetica", 11)
    y -= 8 * mm
    for item in entry.items.filter(component_type=PayrollComponent.TYPE_EARNING):
        pdf.drawString(22 * mm, y, f"{item.component_name}")
        pdf.drawRightString(width - 20 * mm, y, f"{item.amount:,.2f}")
        y -= 6 * mm
    y -= 4 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Rincian Potongan")
    y -= 8 * mm
    pdf.setFont("Helvetica", 11)
    for item in entry.items.filter(component_type=PayrollComponent.TYPE_DEDUCTION):
        pdf.drawString(22 * mm, y, f"{item.component_name}")
        pdf.drawRightString(width - 20 * mm, y, f"{item.amount:,.2f}")
        y -= 6 * mm
    y -= 10 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Gaji Bersih")
    pdf.drawRightString(width - 20 * mm, y, f"{entry.net_pay:,.2f}")
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="slip-{entry.employee.full_name}.pdf"'
    return response


@login_required
@require_POST
def payroll_entry_add_item(request, period_pk, entry_pk, component_type):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    if component_type not in dict(PayrollComponent.COMPONENT_TYPES):
        messages.error(request, "Jenis komponen tidak valid.")
        return redirect("payroll_entry_detail", period_pk=period_pk, entry_pk=entry_pk)
    period = get_object_or_404(PayrollPeriod, pk=period_pk, school=school)
    entry = get_object_or_404(PayrollEntry, pk=entry_pk, period=period)
    if period.status != PayrollPeriod.STATUS_DRAFT:
        messages.error(request, "Tidak dapat mengubah item pada periode final.")
        return redirect("payroll_entry_detail", period_pk=period_pk, entry_pk=entry_pk)
    form = PayrollEntryItemAddForm(
        request.POST,
        school=school,
        component_type=component_type,
        prefix="earn_add" if component_type == PayrollComponent.TYPE_EARNING else "ded_add",
    )
    if form.is_valid():
        component = form.cleaned_data["component"]
        amount = form.cleaned_data["amount"]
        if amount is None:
            amount = component.default_amount
        PayrollEntryItem.objects.create(
            entry=entry,
            component=component,
            component_name=component.name,
            component_type=component.component_type,
            amount=amount,
        )
        entry.recalculate_totals()
        messages.success(request, "Item berhasil ditambahkan.")
    else:
        messages.error(request, "Gagal menambahkan item. Lengkapi data dengan benar.")
    return redirect("payroll_entry_detail", period_pk=period_pk, entry_pk=entry_pk)


@login_required
@require_POST
def payroll_entry_delete_item(request, period_pk, entry_pk, item_pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=period_pk, school=school)
    entry = get_object_or_404(PayrollEntry, pk=entry_pk, period=period)
    if period.status != PayrollPeriod.STATUS_DRAFT:
        messages.error(request, "Tidak dapat menghapus item pada periode final.")
        return redirect("payroll_entry_detail", period_pk=period_pk, entry_pk=entry_pk)
    item = get_object_or_404(PayrollEntryItem, pk=item_pk, entry=entry)
    item.delete()
    entry.recalculate_totals()
    messages.success(request, "Item berhasil dihapus.")
    return redirect("payroll_entry_detail", period_pk=period_pk, entry_pk=entry_pk)


@login_required
@require_POST
def payroll_entry_delete(request, period_pk, entry_pk):
    school = _school_guard(request)
    if isinstance(school, HttpResponse):
        return school
    period = get_object_or_404(PayrollPeriod, pk=period_pk, school=school)
    if period.status == PayrollPeriod.STATUS_FINAL:
        messages.error(request, "Tidak dapat menghapus gaji pada periode final.")
        return redirect("period_detail", pk=period_pk)
    entry = get_object_or_404(PayrollEntry, pk=entry_pk, period=period)
    entry.delete()
    messages.success(request, "Data gaji pegawai dihapus.")
    return redirect("period_detail", pk=period_pk)

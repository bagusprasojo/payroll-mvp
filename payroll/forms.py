from django import forms
from django.forms import inlineformset_factory

from .models import Employee, PayrollComponent, PayrollEntry, PayrollEntryItem, PayrollPeriod


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "full_name",
            "nip",
            "email",
            "employee_type",
            "position",
            "base_salary",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"
        self.fields["nip"].required = True
        self.fields["nip"].help_text = "Nomor Induk Pegawai (unik dalam sekolah)."


class PayrollComponentForm(forms.ModelForm):
    class Meta:
        model = PayrollComponent
        fields = [
            "name",
            "code",
            "component_type",
            "is_fixed",
            "default_amount",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class PayrollPeriodForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = PayrollPeriod
        fields = ["month", "year", "note"]

    def clean_month(self):
        month = self.cleaned_data["month"]
        if month < 1 or month > 12:
            raise forms.ValidationError("Bulan harus antara 1-12.")
        return month

    def clean(self):
        cleaned = super().clean()
        if self.school and cleaned.get("month") and cleaned.get("year"):
            exists = PayrollPeriod.objects.filter(
                school=self.school, month=cleaned["month"], year=cleaned["year"]
            )
            if self.instance.pk:
                exists = exists.exclude(pk=self.instance.pk)
            if exists.exists():
                raise forms.ValidationError("Periode dengan bulan & tahun tersebut sudah ada.")
        return cleaned


class PayrollGenerateForm(forms.Form):
    METHOD_MANUAL = "manual"
    METHOD_COPY = "copy"
    METHOD_IMPORT = "import"

    METHOD_CHOICES = [
        (METHOD_MANUAL, "Generate manual (dengan komponen aktif)"),
        (METHOD_COPY, "Copy dari periode sebelumnya"),
        (METHOD_IMPORT, "Impor Excel"),
    ]

    method = forms.ChoiceField(choices=METHOD_CHOICES)
    source_period = forms.ModelChoiceField(
        queryset=PayrollPeriod.objects.none(),
        required=False,
        label="Periode sumber",
        help_text="Digunakan untuk metode copy",
    )
    upload_file = forms.FileField(required=False, help_text="Template Excel dengan kolom email,component_code,amount")

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)
        if school:
            self.fields["source_period"].queryset = PayrollPeriod.objects.filter(
                school=school, status=PayrollPeriod.STATUS_FINAL
            ).order_by("-year", "-month")

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("method")
        if method == self.METHOD_COPY and not cleaned.get("source_period"):
            self.add_error("source_period", "Pilih periode sumber untuk metode copy.")
        if method == self.METHOD_IMPORT and not cleaned.get("upload_file"):
            self.add_error("upload_file", "Unggah file Excel untuk metode impor.")
        return cleaned


PayrollEntryItemFormSet = inlineformset_factory(
    PayrollEntry,
    PayrollEntryItem,
    fields=["amount"],
    extra=0,
    can_delete=False,
)


class PayrollEntryItemAddForm(forms.Form):
    component = forms.ModelChoiceField(queryset=PayrollComponent.objects.none(), label="Komponen")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, required=False, label="Nominal")

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school")
        component_type = kwargs.pop("component_type")
        super().__init__(*args, **kwargs)
        self.component_type = component_type
        qs = PayrollComponent.objects.filter(
            school=school,
            component_type=component_type,
            is_active=True,
        )
        self.fields["component"].queryset = qs
        self.fields["component"].empty_label = "Pilih komponen"

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount is not None and amount < 0:
            raise forms.ValidationError("Nominal tidak boleh negatif.")
        return amount


class PayrollEntryAddForm(forms.Form):
    employee = forms.ModelChoiceField(queryset=Employee.objects.none(), label="Pegawai")

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school")
        period = kwargs.pop("period")
        super().__init__(*args, **kwargs)
        existing_employee_ids = period.entries.values_list("employee_id", flat=True)
        queryset = school.employees.filter(is_active=True).exclude(id__in=existing_employee_ids)
        self.fields["employee"].queryset = queryset
        if not queryset.exists():
            self.fields["employee"].empty_label = "Tidak ada pegawai tersedia"

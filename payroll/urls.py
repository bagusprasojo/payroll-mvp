from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("employees/", views.employee_list, name="employee_list"),
    path("employees/create/", views.employee_create, name="employee_create"),
    path("employees/<int:pk>/edit/", views.employee_edit, name="employee_edit"),
    path("employees/<int:pk>/delete/", views.employee_delete, name="employee_delete"),
    path("components/", views.component_list, name="component_list"),
    path("components/create/", views.component_create, name="component_create"),
    path("components/<int:pk>/edit/", views.component_edit, name="component_edit"),
    path("components/<int:pk>/delete/", views.component_delete, name="component_delete"),
    path("periods/", views.period_list, name="period_list"),
    path("periods/create/", views.period_create, name="period_create"),
    path("periods/<int:pk>/", views.period_detail, name="period_detail"),
    path("periods/<int:pk>/add-entry/", views.period_add_entry, name="period_add_entry"),
    path("periods/<int:pk>/generate/", views.period_generate, name="period_generate"),
    path("periods/<int:pk>/finalize/", views.period_finalize, name="period_finalize"),
    path("periods/<int:pk>/cancel/", views.period_cancel, name="period_cancel"),
    path("periods/<int:pk>/delete/", views.period_delete, name="period_delete"),
    path(
        "periods/<int:period_pk>/entries/<int:entry_pk>/",
        views.payroll_entry_detail,
        name="payroll_entry_detail",
    ),
    path(
        "periods/<int:period_pk>/entries/<int:entry_pk>/pdf/",
        views.payroll_entry_pdf,
        name="payroll_entry_pdf",
    ),
    path(
        "periods/<int:period_pk>/entries/<int:entry_pk>/add/<str:component_type>/",
        views.payroll_entry_add_item,
        name="payroll_entry_add_item",
    ),
    path(
        "periods/<int:period_pk>/entries/<int:entry_pk>/delete/<int:item_pk>/",
        views.payroll_entry_delete_item,
        name="payroll_entry_delete_item",
    ),
    path(
        "periods/<int:period_pk>/entries/<int:entry_pk>/delete/",
        views.payroll_entry_delete,
        name="payroll_entry_delete",
    ),
]

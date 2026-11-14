from django.urls import path

from . import accounts, companies, contracts, geography, views, visits

app_name = "api"

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="csrf"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/session/", views.SessionView.as_view(), name="session"),
    path("auth/password/", views.PasswordView.as_view(), name="password"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("geography/departments/", geography.DepartmentsView.as_view(), name="departments"),
    path("geography/municipalities/", geography.MunicipalitiesView.as_view(), name="municipalities"),
    path("companies/", companies.CompanyListView.as_view(), name="companies"),
    path("companies/<int:pk>/", companies.CompanyDetailView.as_view(), name="company"),
    path("companies/<int:parent_pk>/sites/", companies.SiteView.as_view(), name="site_create"),
    path("sites/<int:pk>/", companies.SiteView.as_view(), name="site"),
    path("sites/<int:parent_pk>/areas/", companies.AreaView.as_view(), name="area_create"),
    path("areas/<int:pk>/", companies.AreaView.as_view(), name="area"),
    path("areas/<int:parent_pk>/positions/", companies.PositionView.as_view(), name="position_create"),
    path("positions/<int:pk>/", companies.PositionView.as_view(), name="position"),
    path("positions/<int:parent_pk>/workers/", companies.WorkerView.as_view(), name="worker_create"),
    path("workers/<int:pk>/", companies.WorkerView.as_view(), name="worker"),
    path("accounts/", accounts.AccountListView.as_view(), name="accounts"),
    path("accounts/<int:pk>/", accounts.AccountDetailView.as_view(), name="account"),
    path("accounts/<int:pk>/password/", accounts.AccountPasswordView.as_view(), name="account_password"),
    path("accounts/<int:pk>/active/", accounts.AccountActiveView.as_view(), name="account_active"),
    path("contracts/", contracts.ContractListView.as_view(), name="contracts"),
    path("contracts/options/", contracts.ContractOptionsView.as_view(), name="contract_options"),
    path("contracts/read/", contracts.ContractReadView.as_view(), name="contract_read"),
    path("contracts/<int:pk>/", contracts.ContractDetailView.as_view(), name="contract"),
    path("contracts/<int:pk>/summary/", contracts.ContractSummaryView.as_view(), name="contract_summary"),
    path("contracts/<int:pk>/file/", contracts.ContractFileView.as_view(), name="contract_file"),
    path("visits/", visits.VisitListView.as_view(), name="visits"),
    path("visits/calendar/", visits.CalendarView.as_view(), name="visit_calendar"),
    path("visits/agenda/", visits.AgendaView.as_view(), name="visit_agenda"),
    path("visits/options/", visits.VisitOptionsView.as_view(), name="visit_options"),
    path("visits/<int:pk>/", visits.VisitDetailView.as_view(), name="visit"),
    path("visits/<int:pk>/complete/", visits.VisitCompleteView.as_view(), name="visit_complete"),
    path("visits/<int:pk>/cancel/", visits.VisitCancelView.as_view(), name="visit_cancel"),
]

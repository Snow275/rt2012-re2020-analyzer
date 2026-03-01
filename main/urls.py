from django.urls import path
from . import views

urlpatterns = [
    # ── PUBLIC ──────────────────────────────────────
    path('', views.landing, name='landing'),
    path('deposer/', views.import_document, name='import'),
    path('suivi/<str:token>/', views.tracking, name='tracking'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    # Téléchargement rapport public (via lien de suivi)
    path('rapport/<int:document_id>/', views.download_report, name='download_report'),

    # ── AUTH ────────────────────────────────────────
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),

    # ── ADMIN (login requis) ─────────────────────────
    path('dashboard/', views.home, name='home'),
    path('resultats/', views.results, name='results'),
    path('historique/', views.history, name='history'),
    path('parametres/', views.settings_view, name='settings'),
    path('parametres/re2020/', views.update_re2020, name='update_re2020'),
    path('dossier/<int:doc_id>/editer/', views.edit_document, name='edit_document'),
    path('dossier/<int:doc_id>/supprimer/', views.delete_document, name='delete_document'),
    # Téléchargement rapport admin
    path('download_report/<int:document_id>/', views.download_report, name='download_report_admin'),

    # ── DEVIS ───────────────────────────────────────
    path('devis/', views.devis_list, name='devis_list'),
    path('devis/nouveau/', views.devis_create, name='devis_create'),
    path('devis/<int:devis_id>/editer/', views.devis_edit, name='devis_edit'),
    path('devis/<int:devis_id>/supprimer/', views.devis_delete, name='devis_delete'),

    # ── API ─────────────────────────────────────────
    path('api/documents/', views.api_document_list, name='api_document_list'),
    path('api/documents/<int:pk>/', views.api_document_detail, name='api_document_detail'),
    path('api/results/', views.api_results, name='api_results'),
    path('api/history/', views.api_history, name='api_history'),
    path('api/report/<int:pk>/', views.api_report, name='api_report'),
]

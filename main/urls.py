from django.urls import path
from . import views

urlpatterns = [
    # ── PUBLIC ──────────────────────────────────────
    path('', views.landing, name='landing'),
    path('deposer/', views.import_document, name='import'),
    path('suivi/<str:token>/', views.tracking, name='tracking'),
    path('suivi/<str:token>/rapport-ia/', views.rapport_ia_client, name='rapport_ia_client'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('mentions-legales/', views.mentions_legales, name='mentions_legales'),
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
    path('verifier-seuils/', views.verifier_seuils, name='verifier_seuils'),
    path('dossier/<int:doc_id>/editer/', views.edit_document, name='edit_document'),
    path('dossier/<int:doc_id>/email/<str:email_type>/', views.send_email_manual, name='send_email_manual'),
    path('dossier/<int:doc_id>/upload-rapport/', views.upload_rapport_pdf, name='upload_rapport_pdf'),
    path('dossier/<int:doc_id>/rapport-word/', views.download_rapport_word, name='download_rapport_word'),
    path('dossier/<int:doc_id>/supprimer/', views.delete_document, name='delete_document'),
    path('dossier/<int:doc_id>/rapport-ia/', views.generer_rapport_ia, name='generer_rapport_ia'),
    # Téléchargement rapport admin
    path('download_report/<int:document_id>/', views.download_report, name='download_report_admin'),

    # ── DEVIS ───────────────────────────────────────
    path('devis/', views.devis_list, name='devis_list'),
    path('devis/nouveau/', views.devis_create, name='devis_create'),
    path('devis/<int:devis_id>/editer/', views.devis_edit, name='devis_edit'),
    path('devis/<int:devis_id>/supprimer/', views.devis_delete, name='devis_delete'),
    path("devis/accepter/<int:devis_id>/", views.accepter_devis, name="accepter_devis"),
    path("devis/refuser/<int:devis_id>/", views.refuser_devis, name="refuser_devis"),

    # ── API ─────────────────────────────────────────
    path('api/documents/', views.api_document_list, name='api_document_list'),
    path('api/documents/<int:pk>/', views.api_document_detail, name='api_document_detail'),
    path('api/results/', views.api_results, name='api_results'),
    path('api/history/', views.api_history, name='api_history'),
    path('api/report/<int:pk>/', views.api_report, name='api_report'),
]

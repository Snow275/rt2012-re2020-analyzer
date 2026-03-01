from django.urls import path
from . import views

urlpatterns = [
    # Landing page publique
    path('', views.landing, name='landing'),
    # Dashboard interne
    path('dashboard/', views.home, name='home'),
    path('import/', views.import_document, name='import'),
    path('results/', views.results, name='results'),
    path('history/', views.history, name='history'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/update_re2020/', views.update_re2020, name='update_re2020'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('suivi/<str:token>/', views.tracking, name='tracking'),
    path('delete_document/<int:doc_id>/', views.delete_document, name='delete_document'),
    path('download_report/<int:document_id>/', views.download_report, name='download_report'),
    # API
    path('api/documents/', views.api_document_list, name='api_document_list'),
    path('api/documents/<int:pk>/', views.api_document_detail, name='api_document_detail'),
    path('api/results/', views.api_results, name='api_results'),
    path('api/history/', views.api_history, name='api_history'),
    path('api/report/<int:pk>/', views.api_report, name='api_report'),
]

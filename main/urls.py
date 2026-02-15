from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('import/', views.import_document, name='import'),
    path('results/', views.results, name='results'),
    path('history/', views.history, name='history'),
    path('settings/', views.settings, name='settings'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),

    path('delete_document/<int:doc_id>/', views.delete_document, name='delete_document'),
    path('settings/update_re2020', views.update_re2020, name='update_re2020'),
    path('download_report/<int:document_id>/', views.download_report, name='download_report'),
]

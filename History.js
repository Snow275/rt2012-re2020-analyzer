{% extends 'main/base.html' %}

{% block title %}Historique{% endblock %}

{% block content %}
<h1>Historique des analyses</h1>
<ul class="list-group">
    {% for document in documents %}
    <li class="list-group-item">
        {{ document.name }} - {{ document.upload_date }}
        <a href="{% url 'results' %}" class="btn btn-link">Voir les détails</a>
        <a href="{% url 'api_report' document.id %}" class="btn btn-link">Télécharger le rapport</a>
        <form action="{% url 'delete_document' document.id %}" method="post">
            {% csrf_token %}
            <input type="submit" value="Supprimer" class="btn btn-danger">
        </form>
    </li>
    {% endfor %}
</ul>
{% endblock %}

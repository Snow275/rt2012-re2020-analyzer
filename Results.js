<!-- templates/main/home.html -->
{% extends 'base.html' %}
{% block content %}
<h1>Bienvenue sur l'outil de conformité RE2020</h1>
{% for document in documents %}
<p>{{ document.name }}</p>
{% endfor %}
{% endblock %}

<!-- templates/main/results.html -->
{% extends 'base.html' %}
{% block content %}
<h1>Résultats des analyses</h1>
{% for document in documents %}
<div>
    <h2>{{ document.name }}</h2>
    <p>Efficacité énergétique: {{ document.analysis_result.energy_efficiency.value }} (Requis: {{ document.analysis_result.energy_efficiency.requirement }})</p>
    <p>Conformité: {{ document.analysis_result.energy_efficiency.compliance|yesno:"Oui,Non" }}</p>
    <a href="{% url 'detailed_report' document.id %}">Voir le rapport détaillé</a>
</div>
{% endfor %}
{% endblock %}

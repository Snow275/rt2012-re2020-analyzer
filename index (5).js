{% extends 'main/base.html' %}

{% block title %}Paramètres{% endblock %}

{% block content %}
<h1>Paramètres</h1>
<form>
    <div class="form-group">
        <label for="language">Langue :</label>
        <select class="form-control" id="language">
            <option value="fr">Français</option>
            <option value="en">Anglais</option>
        </select>
    </div>
    <div class="form-group">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" value="" id="notifications">
            <label class="form-check-label" for="notifications">
                Notifications par email
            </label>
        </div>
    </div>
    <button type="submit" class="btn btn-primary">Enregistrer les modifications</button>
    <div class="container">
        
        <!-- Ajouter d'autres paramètres ici -->
        <div class="mt-3">
            <h2>Mise à jour des normes RE2020</h2>
            <form method="post" action="{% url 'update_re2020' %}">
                {% csrf_token %}
                <button type="submit" class="btn btn-primary">Mettre à jour RE2020</button>
            </form>
        </div>
    </div>
</form>
{% endblock %}

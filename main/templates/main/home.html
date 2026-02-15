{% extends 'main/base.html' %}

{% block title %}Accueil{% endblock %}

{% block content %}
<div class="jumbotron text-center">
    <h1 class="display-4">Bienvenue sur l'outil de conformité RT2012</h1>
    <p class="lead">Cet outil vous aide à garantir que vos projets respectent les normes de la Réglementation Thermique 2012 (RT2012).</p>
    <hr class="my-4">
    <p>Utilisez le menu pour naviguer entre les différentes sections.</p>
    <a class="btn btn-primary btn-lg" href="{% url 'import' %}" role="button">Importer un document</a>
    <a class="btn btn-secondary btn-lg" href="{% url 'results' %}" role="button">Voir les résultats</a>
</div>

<div class="container mt-5">
    <div class="row">
        <div class="col-md-6 mb-4">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Comment utiliser cet outil</h5>
                    <p class="card-text">1. Allez à la section <a href="{% url 'import' %}">Importer</a> pour télécharger vos documents de projet.</p>
                    <p class="card-text">2. Consultez les <a href="{% url 'results' %}">résultats</a> pour voir si vos projets sont conformes aux exigences de la RT2012.</p>
                    <p class="card-text">3. Téléchargez des rapports détaillés à partir de la section <a href="{% url 'history' %}">Historique</a>.</p>
                </div>
            </div>
        </div>
        <div class="col-md-6 mb-4">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Statistiques récentes</h5>
                    <p class="card-text"><strong>Projets analysés :</strong> 150</p>
                    <p class="card-text"><strong>Taux de conformité :</strong> 85%</p>
                    <p class="card-text"><strong>Émissions de carbone moyennes :</strong> 70 kg CO2/m²</p>
                </div>
            </div>
            <div class="card mt-4">
                <div class="card-body">
                    <h5 class="card-title">Statistiques des projets</h5>
                    <select id="documentSelect" class="form-select mb-4">
                        {% for document in documents %}
                            <option value="{{ document.id }}">{{ document.name }}</option>
                        {% endfor %}
                    </select>
                    <canvas id="documentChart" width="200" height="200"></canvas>
                </div>
            </div>
        </div>
    </div>

    <div class="row mt-5">
        <div class="col-md-12 mb-4">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Témoignages</h5>
                    <p class="card-text">"Cet outil a grandement simplifié notre processus de vérification de conformité RT2012." - <em>Entreprise A</em></p>
                    <p class="card-text">"Grâce à cet outil, nous avons pu réduire nos émissions de carbone et améliorer notre efficacité énergétique." - <em>Entreprise B</em></p>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Bandeau en bas de la page -->
<footer class="footer mt-auto py-3 bg-light">
    <div class="container text-center">
        <span class="text-muted"><a href="{% url 'contact' %}">Contactez-nous</a> | <a href="{% url 'faq' %}">FAQ</a></span>
    </div>
</footer>

<script>
    const documentData = {
        {% for document in documents %}
            {{ document.id }}: {
                labels: ['Conforme', 'Non conforme'],
                datasets: [{
                    data: [
                        {{ document.analysis_result.energy_efficiency.compliance|yesno:"1,0" }},
                        {{ document.analysis_result.energy_efficiency.compliance|yesno:"0,1" }}
                    ],
                    backgroundColor: ['#4CAF50', '#F44336']
                }]
            },
        {% endfor %}
    };

    const ctx = document.getElementById('documentChart').getContext('2d');
    let documentChart = new Chart(ctx, {
        type: 'pie',
        data: documentData[{{ documents.0.id }}],
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        }
    });

    document.getElementById('documentSelect').addEventListener('change', function() {
        const selectedDocument = this.value;
        documentChart.data = documentData[selectedDocument];
        documentChart.update();
    });
</script>
{% endblock %}

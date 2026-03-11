@csrf_exempt
def generer_rapport_ia(request, doc_id):
    """
    Endpoint AJAX rapport IA.
    - GET  : retourne le rapport déjà sauvegardé (si existant)
    - POST : génère via Claude, sauvegarde en BDD, retourne le JSON
    - POST ?force=1 : force la régénération même si déjà sauvegardé
    """
    import json, os, base64, urllib.request, urllib.error

    document = get_object_or_404(Document, id=doc_id)

    # ── GET ou POST sans force → retourner le rapport sauvegardé si présent ──
    force = request.GET.get('force') == '1'
    if not force and document.rapport_ia_json:
        try:
            return JsonResponse({'success': True, 'rapport': json.loads(document.rapport_ia_json), 'cached': True})
        except Exception:
            pass  # JSON corrompu → on régénère

    if request.method not in ('POST', 'GET'):
        return JsonResponse({'error': 'Méthode invalide'}, status=405)

    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    if not ANTHROPIC_API_KEY:
        return JsonResponse({'error': 'Clé API Anthropic manquante (ANTHROPIC_API_KEY)'}, status=500)

    # ── 1. Tenter de lire le PDF ──────────────────────────────────────────────
    pdf_b64 = None
    try:
        if document.upload and document.upload.name:
            with open(document.upload.path, 'rb') as f:
                pdf_b64 = base64.standard_b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"PDF indisponible (fallback BDD) : {e}")

    # ── 2. Contexte du dossier ────────────────────────────────────────────────
    norme = document.norme
    pays_map = {'FR': 'France', 'BE': 'Belgique', 'CH': 'Suisse', 'CA': 'Canada', 'LU': 'Luxembourg'}
    pays_label = pays_map.get(document.pays, document.pays)
    batiment_label = document.get_building_type_display()
    zone = document.climate_zone or 'H2'
    ref = f"DOC-{document.id:04d}"

    champs_norme = {
        'RT2012': [
            ('rt2012_bbio', 'Bbio', ''), ('rt2012_cep', 'Cep', 'kWh ep/m².an'),
            ('rt2012_tic', 'Tic', '°C'), ('rt2012_airtightness', 'Étanchéité', 'm³/h.m²'),
            ('rt2012_enr', 'ENR', ''),
        ],
        'RE2020': [
            ('re2020_energy_efficiency', 'Cep,nr', 'kWh/m².an'),
            ('re2020_carbon_emissions', 'Ic énergie CO₂', 'kgCO2eq/m².an'),
            ('re2020_thermal_comfort', 'DH (confort été)', 'DH'),
        ],
        'PEB': [
            ('peb_espec', 'Espec', 'kWh/m².an'), ('peb_ew', 'Ew', ''),
            ('peb_u_mur', 'U mur', 'W/m².K'), ('peb_u_toit', 'U toit', 'W/m².K'),
            ('peb_u_plancher', 'U plancher', 'W/m².K'),
        ],
        'MINERGIE': [
            ('minergie_qh', 'Qh', 'kWh/m².an'), ('minergie_qtot', 'Qtot', 'kWh/m².an'),
            ('minergie_n50', 'n50', 'h⁻¹'),
        ],
        'SIA380': [('sia380_qh', 'Qh', 'kWh/m².an')],
        'CNEB2015': [
            ('cneb_ei', 'Intensité énergétique', 'kWh/m².an'),
            ('cneb_u_mur', 'U mur', 'W/m².K'), ('cneb_u_toit', 'U toit', 'W/m².K'),
            ('cneb_u_fenetre', 'U fenêtre', 'W/m².K'), ('cneb_infiltration', 'Infiltration', 'L/s.m²'),
        ],
        'CNEB2020': [
            ('cneb_ei', 'Intensité énergétique', 'kWh/m².an'),
            ('cneb_u_mur', 'U mur', 'W/m².K'), ('cneb_u_toit', 'U toit', 'W/m².K'),
            ('cneb_u_fenetre', 'U fenêtre', 'W/m².K'), ('cneb_infiltration', 'Infiltration', 'L/s.m²'),
        ],
        'LENOZ': [
            ('lenoz_ep', 'Énergie primaire', 'kWh/m².an'), ('lenoz_ew', 'Ew', ''),
            ('lenoz_u_mur', 'U mur', 'W/m².K'), ('lenoz_u_toit', 'U toit', 'W/m².K'),
        ],
    }

    valeurs_connues = {}
    for field, label, unit in champs_norme.get(norme, []):
        val = getattr(document, field, None)
        if val is not None:
            valeurs_connues[label] = f"{val} {unit}".strip()

    valeurs_str = '\n'.join([f"  - {k} : {v}" for k, v in valeurs_connues.items()]) or "  (aucune valeur encore saisie)"

    SEUILS_LABELS = {
        'RT2012': "Bbio ≤ 60 | Cep ≤ 50 kWh ep/m².an | Tic ≤ 27°C | Étanchéité ≤ 0,6 m³/h.m² (maison) ou 1,0 (ERP)",
        'RE2020': "Cep,nr ≤ 100 kWh/m².an | Ic énergie ≤ 160 kgCO2/m².an | DH ≤ 1250 (zone H2)",
        'PEB': "Espec ≤ 100 kWh/m².an | U mur ≤ 0,24 | U toit ≤ 0,20 | U plancher ≤ 0,30 W/m².K",
        'MINERGIE': "Qh ≤ 60 kWh/m².an | Qtot ≤ 38 kWh/m².an | n50 ≤ 0,6 h⁻¹",
        'SIA380': "Qh ≤ 90 kWh/m².an selon SIA 380/1",
        'CNEB2015': "EI ≤ 170 kWh/m².an | U mur ≤ 0,24 | U toit ≤ 0,18 | U fenêtre ≤ 1,8 W/m².K | Infiltration ≤ 0,30 L/s.m²",
        'CNEB2020': "EI ≤ 150 kWh/m².an | U mur ≤ 0,21 | U toit ≤ 0,16 | U fenêtre ≤ 1,6 W/m².K | Infiltration ≤ 0,25 L/s.m²",
        'LENOZ': "EP ≤ 90 kWh/m².an | Ew ≤ 100 | U mur ≤ 0,22 | U toit ≤ 0,17 W/m².K",
    }
    seuils_str = SEUILS_LABELS.get(norme, "Voir réglementation applicable")
    source_donnees = "le PDF joint ET les valeurs extraites ci-dessous" if pdf_b64 else "les valeurs extraites ci-dessous (PDF non disponible sur le serveur)"

    system_prompt = f"""Tu es ConformExpert, un expert en réglementation thermique et énergétique des bâtiments.
Tu analyses des documents techniques (notices thermiques, attestations, CCTP, études STD) et tu génères des rapports de conformité professionnels, précis et adaptés à la réglementation applicable.

Contexte du dossier :
- Référence : {ref}
- Projet : {document.name}
- Client : {document.client_name or 'Non renseigné'}
- Norme applicable : {norme}
- Pays / Zone : {pays_label} — Zone climatique {zone}
- Type de bâtiment : {batiment_label}
- Source des données : {source_donnees}
- Valeurs extraites :
{valeurs_str}
- Seuils réglementaires {norme} :
  {seuils_str}

Tu dois générer un rapport structuré complet.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans explication, sans balises.

Structure JSON attendue :
{{
  "verdict": "Conforme" | "Non Conforme" | "Données insuffisantes",
  "resume_executif": "Paragraphe de 3-5 phrases résumant les conclusions principales.",
  "criteres": [
    {{
      "nom": "Nom du critère",
      "valeur": 72.0,
      "seuil": 50.0,
      "unite": "kWh ep/m².an",
      "conforme": false,
      "ecart_pct": 44.0,
      "commentaire": "Explication courte de la situation."
    }}
  ],
  "points_forts": ["Point fort 1", "Point fort 2"],
  "non_conformites": [
    {{
      "critere": "Nom",
      "gravite": "bloquant" | "majeur" | "mineur",
      "description": "Description du problème.",
      "action": "Action corrective recommandée.",
      "delai": "2 à 6 semaines",
      "cout_estime": "8 000 — 15 000 €"
    }}
  ],
  "recommandations": [
    {{
      "priorite": "URGENT" | "RECOMMANDÉ" | "OPTIONNEL",
      "titre": "Titre de la recommandation",
      "description": "Description détaillée de l'action à mener.",
      "impact_reglementaire": "Impact sur le critère concerné.",
      "delai": "2 à 6 semaines"
    }}
  ],
  "analyse_enveloppe": {{
    "synthese": "Paragraphe sur l'enveloppe thermique.",
    "points_attention": ["Point 1", "Point 2"]
  }},
  "systemes_energetiques": {{
    "synthese": "Paragraphe sur les systèmes CVC, ECS, éclairage.",
    "equipements": [
      {{"poste": "Chauffage", "equipement": "PAC air-eau", "performance": "COP 3,24", "evaluation": "Performant"}}
    ]
  }},
  "contexte_reglementaire": "Paragraphe expliquant la réglementation {norme} applicable à ce projet.",
  "mentions_legales": "Ce rapport est établi sur la base des documents fournis et constitue une analyse documentaire indépendante. Il ne se substitue pas à une attestation officielle de conformité."
}}

Si une valeur n'est pas disponible pour un critère, omets ce critère du tableau.
Sois précis, factuel, professionnel. Adapte le niveau de détail à la norme {norme}."""

    # ── 4. Message Claude ─────────────────────────────────────────────────────
    if pdf_b64:
        user_content = [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
            {"type": "text", "text": f"Analyse ce document thermique pour le dossier {ref} ({norme} — {pays_label}) et génère le rapport JSON complet selon les instructions."}
        ]
        headers_extra = {"anthropic-beta": "pdfs-2024-09-25"}
    else:
        user_content = [
            {"type": "text", "text": f"Le PDF original n'est pas disponible sur le serveur. Génère le rapport JSON complet pour le dossier {ref} ({norme} — {pays_label}) en te basant exclusivement sur les valeurs extraites et les seuils fournis dans le contexte."}
        ]
        headers_extra = {}

    # ── 5. Appel API Claude ───────────────────────────────────────────────────
    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-5",
            "max_tokens": 4000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}]
        }).encode('utf-8')

        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        }
        headers.update(headers_extra)

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            raw = result['content'][0]['text'].strip().replace('```json', '').replace('```', '').strip()
            rapport = json.loads(raw)

            # ── Sauvegarder en BDD ────────────────────────────────────────────
            document.rapport_ia_json = json.dumps(rapport, ensure_ascii=False)
            document.save(update_fields=['rapport_ia_json'])

            return JsonResponse({'success': True, 'rapport': rapport, 'cached': False})

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"CLAUDE API ERROR {e.code}: {body}")
        return JsonResponse({'error': f'Erreur API Claude ({e.code}) : {body[:300]}'}, status=500)
    except json.JSONDecodeError as e:
        print(f"JSON PARSE ERROR: {e}")
        return JsonResponse({'error': f'Erreur parsing JSON : {str(e)}'}, status=500)
    except Exception as e:
        print(f"GENERER_RAPPORT_IA ERROR: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def rapport_ia_client(request, token):
    """Page publique rapport IA — accessible via lien de suivi, sans login."""
    document = get_object_or_404(Document, tracking_token=token, status='termine')
    return render(request, 'main/rapport_ia_client.html', {'document': document})

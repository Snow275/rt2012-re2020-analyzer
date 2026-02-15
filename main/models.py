def analyze_document(document, data):

    document.energy_efficiency = data.get("energy_efficiency", 0)
    document.thermal_comfort = data.get("thermal_comfort", 0)
    document.carbon_emissions = data.get("carbon_emissions", 0)
    document.water_management = data.get("water_management", 0)
    document.indoor_air_quality = data.get("indoor_air_quality", 0)

    document.save()

    # Supprimer anciennes analyses
    Analysis.objects.filter(document=document).delete()

    standards = Standard.objects.all()

    for standard in standards:
        requirements = {
            "energy_efficiency": standard.energy_efficiency,
            "thermal_comfort": standard.thermal_comfort,
            "carbon_emissions": standard.carbon_emissions,
            "water_management": standard.water_management,
            "indoor_air_quality": standard.indoor_air_quality,
        }

        for criteria, requirement in requirements.items():
            value = getattr(document, criteria)

            # règle spéciale carbone (plus petit = mieux)
            if criteria == "carbon_emissions":
                compliance = value <= requirement
            else:
                compliance = value >= requirement

            Analysis.objects.create(
                document=document,
                standard=standard,
                criteria=criteria,
                value=value,
                requirement=requirement,
                compliance=compliance,
            )

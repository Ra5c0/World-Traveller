import json

def adjust_coordinates(input_file, output_file):
    data = []

    with open(input_file, 'r', encoding='utf-8') as file:
        cities = json.load(file)  # Charger les données JSON existantes

        for city in cities:
            # Récupérer les informations de la ville
            city_id = city["id"]
            city_name = city["name"]
            latitude = city["latitude"]
            longitude = city["longitude"]

            # Ajuster les coordonnées pour s'adapter à Leaflet
            adjusted_latitude = latitude + 0.0032
            adjusted_longitude = longitude + 0.0034

            # Créer un nouvel objet de ville avec les coordonnées ajustées
            adjusted_city = {
                "id": city_id,
                "name": city_name,
                "latitude": adjusted_latitude,
                "longitude": adjusted_longitude
            }

            # Ajouter la ville ajustée à la liste des données
            data.append(adjusted_city)

    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile, indent=4)

# Utilisation du script
adjust_coordinates('output_with_ids.json', 'output_adjusted.json')

import json

def parse_txt_to_json_with_ids(input_file, output_file):
    data = []
    city_id = 1  # Compteur d'ID pour les villes

    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split('\t')
            if len(parts) >= 6:
                city_name = parts[1]
                latitude = float(parts[4])
                longitude = float(parts[5])

                city_data = {
                    "id": str(city_id),  # Convertir en chaîne pour JSON
                    "name": city_name,
                    "latitude": latitude,
                    "longitude": longitude
                }

                data.append(city_data)
                city_id += 1  # Incrémenter l'ID pour la prochaine ville

    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile, indent=4)

# Utilisation du script
parse_txt_to_json_with_ids('cities1000.txt', 'output_with_ids.json')

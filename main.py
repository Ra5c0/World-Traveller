import sys
import os
import json
import folium
import logging
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QThread
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QDialog, 
    QListWidget, QAbstractItemView, QDialogButtonBox, 
    QMessageBox, QCheckBox, QInputDialog
)
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Dialogue pour rechercher un lieu
class SearchLocationDialog(QDialog):
    def __init__(self, parent=None):
        super(SearchLocationDialog, self).__init__(parent)
        self.setWindowTitle("Rechercher un lieu")

        layout = QVBoxLayout(self)

        # Champ de recherche
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher...")
        self.search_input.textChanged.connect(self.filter_locations)
        layout.addWidget(self.search_input)

        # Liste des lieux
        self.location_list_widget = QListWidget(self)
        self.location_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.location_list_widget)

        # Case à cocher pour marquer un lieu comme visité
        self.visited_checkbox = QCheckBox("Visited", self)
        layout.addWidget(self.visited_checkbox)

        # Boutons Ok et Annuler
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.locations = None
        self.load_locations()

    # Charger les lieux depuis le fichier JSON en arrière-plan
    def load_locations(self):
        self.loading_thread = LocationLoaderThread()
        self.loading_thread.locations_loaded.connect(self.populate_locations)
        self.loading_thread.start()

    # Mettre à jour la liste des lieux dans la fenêtre de dialogue
    def populate_locations(self, locations):
        self.locations = locations
        self.filter_locations()

    # Filtrer les lieux en fonction du texte de recherche
    def filter_locations(self):
        if self.locations is None:
            return
        filter_text = self.search_input.text().strip().lower()
        self.location_list_widget.clear()
        filtered_locations = [location for location in self.locations if filter_text in location['name'].lower()]
        self.location_list_widget.addItems([location['name'] for location in filtered_locations])

    # Obtenir le lieu sélectionné avec l'état de la case à cocher
    def get_selected_location(self):
        selected_items = self.location_list_widget.selectedItems()
        if selected_items:
            selected_location_name = selected_items[0].text()
            selected_location = next((loc for loc in self.locations if loc['name'] == selected_location_name), None)
            if selected_location:
                selected_location['visited'] = self.visited_checkbox.isChecked()
                return selected_location
        return None

# Thread pour charger les lieux depuis le fichier JSON
class LocationLoaderThread(QThread):
    locations_loaded = pyqtSignal(list)

    def run(self):
        all_locations = self.load_all_locations()
        self.locations_loaded.emit(all_locations)

    def load_all_locations(self):
        try:
            with open('json/allLocations.json', 'r') as f:
                all_locations = json.load(f)
                # Tri des lieux par nom
                all_locations.sort(key=lambda x: x['name'].lower())
                return all_locations
        except FileNotFoundError:
            logging.error("Le fichier 'allLocations.json' est introuvable.")
            QMessageBox.warning(self, "Erreur", "Le fichier 'allLocations.json' est introuvable.")
            return []
        except json.JSONDecodeError:
            logging.error("Erreur de décodage JSON dans 'allLocations.json'.")
            QMessageBox.warning(self, "Erreur", "Erreur de décodage JSON dans 'allLocations.json'. Veuillez vérifier la syntaxe du fichier.")
            return []
    
class EditLocationDialog(QDialog):
    def __init__(self, location, parent=None):
        super(EditLocationDialog, self).__init__(parent)
        self.setWindowTitle("Modifier un lieu")
        self.location = location

        layout = QVBoxLayout(self)

        # Afficher le nom du lieu
        self.location_label = QLabel(self.location['name'])
        layout.addWidget(self.location_label)

        # Case à cocher pour l'état du lieu (visitée ou non visitée)
        self.visited_checkbox = QCheckBox("Visited", self)
        self.visited_checkbox.setChecked(self.location.get('visited', True))
        layout.addWidget(self.visited_checkbox)

        # Boutons Ok et Annuler
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    # Obtenir l'état modifié du lieu
    def get_updated_location(self):
        self.location['visited'] = self.visited_checkbox.isChecked()
        return self.location

# Dialogue pour supprimer un lieu
class DeleteLocationDialog(QDialog):
    def __init__(self, locations, parent=None):
        super(DeleteLocationDialog, self).__init__(parent)
        self.setWindowTitle("Supprimer un lieu")

        layout = QVBoxLayout(self)
        self.location_list_widget = QListWidget(self)
        self.location_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Trier les noms de villes par ordre alphabétique
        sorted_locations = sorted(locations, key=lambda x: x['name'].lower())
        self.location_list_widget.addItems([location['name'] for location in sorted_locations])
        
        layout.addWidget(self.location_list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    # Obtenir l'index du lieu sélectionné
    def selected_location_index(self):
        selected_items = self.location_list_widget.selectedItems()
        if selected_items:
            return self.location_list_widget.row(selected_items[0])
        return None

# Visionneuse de la carte
class MapViewer(QWidget):
    def __init__(self, parent=None):
        super(MapViewer, self).__init__(parent)
        self.setWindowTitle("World Traveller")
        self.setWindowIcon(QIcon("img/logoNoBG.png"))
        self.locations = []

        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        # Barre latérale pour les actions
        self.sidebar_layout = QVBoxLayout()
        main_layout.addLayout(self.sidebar_layout, 0) 

        # Titre de la barre latérale
        sidebar_title = QLabel("Barre latérale")
        sidebar_title.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(sidebar_title)

        # Bouton pour ajouter un lieu
        add_location_button = QPushButton("Ajouter un lieu")
        add_location_button.clicked.connect(self.show_add_location_dialog)
        self.sidebar_layout.addWidget(add_location_button)

        # Bouton pour modifier l'état d'un lieu
        edit_location_button = QPushButton("Modifier un lieu")
        edit_location_button.clicked.connect(self.show_edit_location_dialog)
        self.sidebar_layout.addWidget(edit_location_button)

        # Bouton pour supprimer un lieu
        self.delete_location_button = QPushButton("Supprimer un lieu")
        self.delete_location_button.clicked.connect(self.show_delete_location_dialog)
        self.sidebar_layout.addWidget(self.delete_location_button)

        # Mise en page pour la carte
        self.map_layout = QVBoxLayout()
        main_layout.addLayout(self.map_layout, 4) 

        # Vue de la carte
        self.web_view = QWebEngineView()
        self.map_layout.addWidget(self.web_view)

        # Charger les lieux depuis le fichier JSON et afficher la carte
        self.load_locations_from_json()
        self.show_map()

    # Charger tous les lieux depuis le fichier JSON
    def load_all_locations(self):
        try:
            with open('json/allLocations.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error("Le fichier 'allLocations.json' est introuvable.")
            QMessageBox.warning(self, "Erreur", "Le fichier 'allLocations.json' est introuvable.")
            return []
        except json.JSONDecodeError:
            logging.error("Erreur de décodage JSON dans 'allLocations.json'.")
            QMessageBox.warning(self, "Erreur", "Erreur de décodage JSON dans 'allLocations.json'. Veuillez vérifier la syntaxe du fichier.")
            return []
        
    # Charger les lieux visités depuis le fichier JSON
    def load_locations_from_json(self):
        try:
            with open('json/visitedLocations.json', 'r') as f:
                self.locations = json.load(f)
        except FileNotFoundError:
            logging.error("Le fichier 'visitedLocations.json' est introuvable.")
            self.locations = []
        except json.JSONDecodeError:
            logging.error("Erreur de décodage JSON dans 'visitedLocations.json'.")
            self.locations = []

    # Sauvegarder les lieux visités dans le fichier JSON
    def save_locations_to_json(self):
        with open('json/visitedLocations.json', 'w') as f:
            json.dump(self.locations, f)

    # Afficher le dialogue pour ajouter un lieu
    def show_add_location_dialog(self):
        dialog = SearchLocationDialog()
        if dialog.exec_() == QDialog.Accepted:
            selected_location = dialog.get_selected_location()
            if selected_location:
                self.add_location(selected_location['name'], selected_location['latitude'], selected_location['longitude'], selected_location.get('visited', True))

    # Ajouter un lieu à la liste des lieux et afficher la carte
    def add_location(self, location_name, latitude, longitude, visited):
        if not location_name or not latitude or not longitude:
            logging.error("Champs manquants lors de l'ajout d'un lieu.")
            QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs.")
            return

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            logging.error("Coordonnées invalides lors de l'ajout d'un lieu.")
            QMessageBox.warning(self, "Erreur", "Veuillez saisir des valeurs de latitude et longitude valides.")
            return

        self.locations.append({
            'name': location_name,
            'latitude': latitude,
            'longitude': longitude,
            'visited': visited
        })

        self.save_locations_to_json()
        self.show_map()

    # Fonction pour afficher le dialogue de modification de l'état d'un lieu
    def show_edit_location_dialog(self):
        if not self.locations:
            QMessageBox.warning(self, "Aucun lieu", "Il n'y a aucun lieu à modifier.")
            return

        # Trier les noms de lieux par ordre alphabétique
        location_names = sorted([location['name'] for location in self.locations], key=lambda x: x.lower())
        location_name, ok = QInputDialog.getItem(self, "Choisir un lieu", "Lieu :", location_names, 0, False)
        if ok and location_name:
            selected_location = next((loc for loc in self.locations if loc['name'] == location_name), None)
            if selected_location:
                dialog = EditLocationDialog(selected_location, self)
                if dialog.exec_() == QDialog.Accepted:
                    updated_location = dialog.get_updated_location()
                    for loc in self.locations:
                        if loc['name'] == updated_location['name']:
                            loc['visited'] = updated_location['visited']
                    self.save_locations_to_json()
                    self.show_map()

    # Afficher le dialogue pour supprimer un lieu
    def show_delete_location_dialog(self):
        dialog = DeleteLocationDialog(self.locations, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            location_index = dialog.selected_location_index()
            if location_index is not None:
                self.remove_location(location_index)

    # Supprimer un lieu de la liste des lieux et afficher la carte
    def remove_location(self, index):
        if 0 <= index < len(self.locations):
            # Trouver l'index de la ville dans la liste non triée
            original_index = self.locations.index(sorted(self.locations, key=lambda x: x['name'].lower())[index])
            del self.locations[original_index]
            self.save_locations_to_json()
            self.show_map()

    # Afficher la carte avec les marqueurs pour les lieux visités
    def show_map(self):
        m = folium.Map(location=[0, 0], zoom_start=2, min_zoom=2, max_zoom=18, max_bounds=True, max_bounds_viscosity=0.7)
        for location in self.locations:
            if location.get('visited', False):
                icon_path = 'img/visited.png'
                popup_content = f"<p style='font-size: 16px; white-space: nowrap; margin: 0; padding: 5px 0;'><b>{location['name']}</b></p><br><i>Visited</i>"
            else:
                icon_path = 'img/tovisit.png'
                popup_content = f"<p style='font-size: 16px; white-space: nowrap; margin: 0; padding: 5px 0;'><b>{location['name']}</b></p><br><i>To Visit</i>"

            folium.Marker(
                [location['latitude'], location['longitude']], 
                icon=folium.CustomIcon(icon_path, icon_size=(96, 96)),
                popup=popup_content
            ).add_to(m)

        map_file = "html/map.html"
        m.save(map_file)

        html_url = QUrl.fromLocalFile(os.path.abspath(map_file))
        self.web_view.load(html_url)

# Fonction principale pour exécuter l'application
def main():
    app = QApplication(sys.argv)
    map_viewer = MapViewer()
    map_viewer.resize(900, 600)
    map_viewer.show()

    sys.exit(app.exec_())

# Exécuter l'application si ce fichier est le point d'entrée
if __name__ == "__main__":
    main()

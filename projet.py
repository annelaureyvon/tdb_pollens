import dash
from dash import dcc, html, Input, Output
import requests
from bs4 import BeautifulSoup
import pandas as pd
import geopandas as gpd
import folium
from folium import plugins


# Charger les données du fichier "communes-departement-region.csv"
donnees = pd.read_csv("communes-departement-region.csv", sep=",")

# Sélectionner les lignes où la colonne "nom_region" vaut "Hauts-de-France"
donnees_hdf = donnees[donnees['nom_region'] == "Hauts-de-France"]

# Sélectionner uniquement les colonnes requises
donnees_finales = donnees_hdf[['nom_commune_postal', 'latitude', 'longitude', 'code_postal', 'code_commune_INSEE', 'nom_departement']]

# Ajouter le zéro devant les codes postaux à 4 chiffres
donnees_finales['code_postal'] = donnees_finales['code_postal'].apply(lambda x: str(x).zfill(5))

# Enregistrer les données dans un nouveau fichier CSV
donnees_finales.to_csv("villes_hauts_de_france.csv", index=False)


# Charger les données des villes des Hauts-de-France à partir du fichier CSV
data = pd.read_csv("villes_hauts_de_france.csv")

# Garder la colonne "nom_département" dans le DataFrame
nom_departement = data['nom_departement']

def ajouter_zero(code_postal):
    if len(str(code_postal)) == 4:
        return str(code_postal).zfill(5)  # Ajoute un zéro devant le code postal à 4 chiffres
    else:
        return str(code_postal)  # Retourne le code postal inchangé s'il a déjà 5 chiffres ou plus

# Appliquer la fonction à la colonne 'code_postal'
data['code_postal'] = data['code_postal'].apply(ajouter_zero)

def ajouter_zero(code_INSEE):
    return str(code_INSEE).zfill(5)  # Ajoute un zéro devant le code INSEE si nécessaire

# Appliquer la fonction à la colonne 'code_commune_INSEE'
data['code_commune_INSEE'] = data['code_commune_INSEE'].apply(ajouter_zero)

# Ajouter la colonne "nom_département" au DataFrame modifié
data['nom_département'] = nom_departement

# Enregistrer le DataFrame modifié dans un nouveau fichier CSV
data.to_csv("villes_hauts_de_france_modifie.csv", index=False)


# Afficher les premières lignes du DataFrame modifié
#print(data.head())

data = pd.read_csv("villes_hauts_de_france_modifie.csv", dtype={'code_postal': str, 'code_commune_INSEE': str})

# Fonction pour ajuster les noms de communes en supprimant les espaces
def ajuster_nom_commune(nom_commune):
    return nom_commune.replace(" ", "")

# Appliquer la fonction à la colonne 'nom_commune_postal'
data['nom_commune_postal'] = data['nom_commune_postal'].apply(ajuster_nom_commune)

# Fonction pour construire l'URL pour chaque commune
def construire_url(nom_commune, code_commune_INSEE, code_postal):
    base_url = "https://www.atmo-hdf.fr/air-commune/"
    # Remplacez les espaces dans le nom de la commune par des tirets
    nom_commune = nom_commune.replace(" ", "-")
    # Construisez l'URL avec le nom de la commune et le code commune INSEE
    url = f"{base_url}{nom_commune}/{code_commune_INSEE}/pollen?adresse={nom_commune}+({code_postal})&date=2024-04-19"
    return url

# Charger le fichier GeoJSON
geojson_file = "departements.geojson"
gdf = gpd.read_file(geojson_file)
# Filtrer les départements d'intérêt
departements_interet = ["Aisne", "Nord", "Pas-de-Calais", "Oise", "Somme"]
gdf = gdf[gdf['nom'].isin(departements_interet)]
# Créer la carte Folium
map = folium.Map(location=[49.5, 2.5], zoom_start=8)
# Ajouter les départements à la carte
folium.GeoJson(gdf).add_to(map)
# Convertir la carte Folium en HTML
map_html = map._repr_html_()

# Initialisation de l'application Dash
app = dash.Dash(__name__)

# Mise en page de l'application Dash
app.layout = html.Div([
    html.H1("Indice de risque pollinique par commune"),
    html.Label("Recherchez une commune : "),
    dcc.Input(id="input-ville", type="text", value="", debounce=True),
    html.Div(id="output-container"),
    html.Iframe(id='carte-departements', srcDoc=map_html, width='100%', height='600px', style={'border': 'none'})
])

# Callback pour récupérer les données de pollen pour la ville saisie
@app.callback(
    Output("output-container", "children"),
    [Input("input-ville", "value")]
)
def update_output(ville):
    if ville:
        # Recherche de la ville dans le DataFrame
        row = data[data['nom_commune_postal'].str.lower() == ville.lower()]
        if not row.empty:
            # Construction de l'URL pour la ville
            url = construire_url(row.iloc[0]['nom_commune_postal'], row.iloc[0]['code_commune_INSEE'], row.iloc[0]['code_postal'])
            # Récupération des données
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                balises_pollens = soup.find_all('p', class_='c-indice-pollen-taxon-title font-weight-bold text-center')
                balises_categories = soup.find_all('p', class_='text-uppercase mt-2')
                balise_departement = soup.find('p', class_='font-weight-bold text-uppercase mt-3').get_text(strip=True)

                associations = []
                for pollen, categorie in zip(balises_pollens, balises_categories):
                    nom_pollen = pollen.get_text(strip=True)
                    nom_categorie = categorie.get_text(strip=True)
                    associations.append((nom_pollen, nom_categorie))

                # Diviser la liste des associations en deux sous-listes pour deux lignes
                associations_ligne1 = associations[:3]
                associations_ligne2 = associations[3:6]

                # Construction de la sortie
                output = html.Div([
                    html.Div([
                        html.Div([
                            html.P(assoc[0], style={'text-align': 'center', 'font-family': 'Arial', 'font-size': '16px', 'width': '100px'}),
                            html.P(assoc[1], style={'text-align': 'center', 'font-family': 'Arial', 'font-size': '14px', 'color': 'grey' if assoc[1] == 'Nul' else 'green' if assoc[1] == 'Faible' else 'yellow' if assoc[1] == 'Moyen' else 'red', 'width': '100px'})
                        ], style={'margin-bottom': '10px'}) for assoc in associations_ligne1
                    ], style={'display': 'flex', 'justify-content': 'space-around'}),
                    html.Div([
                        html.Div([
                            html.P(assoc[0], style={'text-align': 'center', 'font-family': 'Arial', 'font-size': '16px', 'width': '100px'}),
                            html.P(assoc[1], style={'text-align': 'center', 'font-family': 'Arial', 'font-size': '14px', 'color': 'grey' if assoc[1] == 'Nul' else 'green' if assoc[1] == 'Faible' else 'yellow' if assoc[1] == 'Moyen' else 'red', 'width': '100px'})
                        ], style={'margin-bottom': '10px'}) for assoc in associations_ligne2
                    ], style={'display': 'flex', 'justify-content': 'space-around'}),
                    html.Div([
                    html.P(f"Niveau de risque de pollen par département : {balise_departement}")
                    ])
                ])
                return output
            else:
                return "La requête a échoué avec le code : {}".format(response.status_code)
        else:
            return "Ville non trouvée."


if __name__ == '__main__':
    app.run_server(debug=True)



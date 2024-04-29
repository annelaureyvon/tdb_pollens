# Import des bibliothèques et des modules
import dash
from dash import html, dcc, Input, Output
import requests
from bs4 import BeautifulSoup
import pandas as pd
import base64
from io import BytesIO
import folium
import dash_bootstrap_components as dbc
import datetime

# Fonction pour récupérer et encoder une image depuis une URL
def fetch_and_encode_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        return 'data:image/jpg;base64,' + base64.b64encode(response.content).decode('ascii')
    else:
        return None

# Fonction de création de la carte
def create_map():
    # Coordonnées du centre des Hauts-de-France
    center_lat, center_lon = 49.894483, 2.985636
    # Créer une carte centrée sur les Hauts-de-France
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7.5)
    # URL du fichier GeoJSON
    geojson_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions/hauts-de-france/departements-hauts-de-france.geojson"
    # Télécharger les données GeoJSON
    response = requests.get(geojson_url)
    if response.status_code == 200:
        geojson_data = response.json()
        # Ajouter la superposition GeoJSON
        folium.GeoJson(
            geojson_data,
            name='geojson',
            style_function=lambda x: {'fillOpacity': 0, 'color': 'black', 'weight': 2}
        ).add_to(m)
    else:
        print("Failed to download GeoJSON data")
    # Enregistrer la carte sous forme de fichier HTML
    m.save('hauts_de_france_map.html')

# Fonction pour convertir le niveau de risque en couleur
def risk_to_color(risk_level):
    colors = {
        'Nul': '#ADD8E6',
        'Faible': 'green',
        'Moyen': 'yellow',
        'Élevé': 'red'
    }
    return colors.get(risk_level, 'gray')

# Fonction pour aller chercher les recommandation sur le site atmo France
def fetch_pollen_recommendations():
    # Obtenir la date actuelle
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Utiliser la date actuelle dans l'URL
    url = f'https://www.atmo-france.org/article/lindice-pollinique?date={current_date}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Ensure the request was successful

        soup = BeautifulSoup(response.text, 'html.parser')
        content_section = soup.find('h2', id='item-4755')

        if content_section:
            recommendations_list = content_section.find_next('ul')
            if recommendations_list:
                return [item.text for item in recommendations_list.find_all('li')]
            else:
                return ["List of recommendations not found!"]
        else:
            return ["Content section not found!"]
    except requests.RequestException as e:
        return [str(e)]

# Initialisation de l'application Dash avec le thème Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Lecture des données CSV pour les données de la ville
data = pd.read_csv("villes_hauts_de_france_modifie.csv", dtype={'code_postal': str, 'code_commune_INSEE': str})

# Appliquer une fonction pour ajuster les noms de communes
def ajuster_nom_commune(nom_commune):
    return nom_commune.replace(" ", "-")

# Appliquer la fonction à la colonne 'nom_commune_postal'
data['nom_commune_postal'] = data['nom_commune_postal'].apply(ajuster_nom_commune)

# Création de la carte
create_map()

# Mise en place des différentes parties du tableau de bord
app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.Div("Tableau de bord Pollen", style={
                'backgroundColor': '#004d00',
                'color': 'white',
                'padding': '10px 20px',
                'fontSize': '40px',
                'fontWeight': 'bold',
                'textAlign': 'left'
            })
        ], width=12)
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Tabs(id='tabs', value='tab-1', children=[
                dcc.Tab(label='Accueil', value='tab-1'),
                dcc.Tab(label="L'air de ma commune", value='tab-2'),
                dcc.Tab(label='Recommandations', value='tab-3'),
                dcc.Tab(label='Informations sur le Pollen', value='tab-5'),
                dcc.Tab(label='La mesure des pollens', value='tab-4')
            ], vertical=True, style={'height': '100vh', 'borderRight': 'thin lightgrey solid', 'textAlign': 'left'}),
        ], width=2),  # Colonne pour les onglets
        dbc.Col([
            html.Div(id='tabs-content', style={'padding': '20px'})
        ], width=10)  # Colonne pour le contenu des onglets
    ])
])

# Callback pour changer le contenu de l'onglet
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
            html.H2("Bienvenue sur le Tableau de bord des Pollens en Hauts-de-France !"),
            html.P("Explorez les différents onglets pour obtenir des informations sur les pollens dans votre région.")
        ])
    elif tab == 'tab-5':
        image_url = "https://www.atmo-hdf.fr/sites/hdf/files/styles/large_w1500/public/medias/images/2023-08/Calendrier_pollens_Hauts-de-France.jpg"
        encoded_image = fetch_and_encode_image(image_url)
        if encoded_image:
            image_html = html.Img(src=encoded_image, style={'width': '100%', 'height': 'auto'})
        else:
            image_html = "Image du calendrier non disponible"

        return html.Div([
            html.H1("Info générale sur les pollens"),
            html.Div(id='pollen-info'),
            dcc.Interval(id='interval-component', interval=3600000, n_intervals=0),
            html.H4("Pour les Hauts-de-France, on observe le calendrier :"),
            html.Img(src=encoded_image, style={'width': '80%', 'height': 'auto'}) if encoded_image else "Image non disponible"
        ])
    elif tab == 'tab-2':
        image_url = "https://www.atmo-hdf.fr/sites/hdf/files/medias/images/2022-03/echelle_pollens_2022.jpg"
        encoded_image = fetch_and_encode_image(image_url)
        if encoded_image:
            image_html = html.Img(src=encoded_image, style={'width': '100%', 'height': 'auto'})
        else:
            image_html = "Image de l'échelle des pollens non disponible"

        return [
            html.Div([
                html.H1("Indice de risque pollinique par commune"),
            ]),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H1(" "),
                        html.Label("Recherchez une commune : "),
                        # Menu de choix déroulant avec autocomplétion (liste: data["nom_commune_postal"])
                        dcc.Dropdown(
                            id="input-ville",
                            options=[{'label': i, 'value': i} for i in data["nom_commune_postal"].unique()],
                            value="",
                            placeholder="Entrez une commune"
                        ),
                        html.Div(id="output-container"),
                        html.H1(" "),
                        image_html,
                    ]),
                ], width=4),
                dbc.Col([
                    html.H1(" "),
                    html.Div(id="map-container", children=[
                        html.Iframe(
                            id="map-iframe",
                            srcDoc=open('hauts_de_france_map.html', 'r').read(),
                            width='95%',
                            height='450'
                        )]),
                ], width=8)
            ])
        ]
    elif tab == 'tab-3':
        recommendations = fetch_pollen_recommendations()
        return html.Div([
            html.H1("Quelles sont les recommandations en cas d'allergie ?"),
            html.Ul([html.Li(item) for item in recommendations])
        ])
    elif tab == 'tab-4':
        image_url = "https://www.atmo-hdf.fr/sites/hdf/files/medias/images/2022-09/capteur_pollens_info.jpg"
        encoded_image = fetch_and_encode_image(image_url)
        if encoded_image:
            image_html = html.Img(src=encoded_image, style={'width': '40%', 'height': 'auto'})
        else:
            image_html = "Image de l'échelle des pollens non disponible"

        url = "https://www.atmo-hdf.fr/article/surveillance-des-pollens"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            iframe_tag = soup.find("iframe", src=True)  # Updated to find any iframe with a src attribute
            if iframe_tag:
                video_url = iframe_tag["src"]
                return html.Div([
                    html.H1("Comment ça marche la mesure des pollens?"),
                    image_html,
                    html.H1(" "),
                    html.Iframe(src=video_url, width="840", height="472", style={'border': 'none'})
                ])
            else:
                return html.Div("La balise iframe spécifiée n'a pas été trouvée sur la page.")
        else:
            return html.Div(f"La requête a échoué avec le code de statut: {response.status_code}")

# Callback pour mettre à jour les informations sur les pollens
@app.callback(
    Output('pollen-info', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_pollen_info(n):
    url = "https://www.atmo-hdf.fr/article/surveillance-des-pollens"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        div_field_item = soup.find("div", class_="field__item")
        paragraphs = div_field_item.find_all("p")
        return html.Ul([html.Li(p.text) for p in paragraphs])
    else:
        return "La requête a échoué avec le code de statut: {}".format(response.status_code)

# Callback pour les données sur les pollens par ville
@app.callback(
    Output("output-container", "children"),
    Input("input-ville", "value")
)
def update_output(ville):
    if ville:
        ville_clean = ville.replace(" ", "")
        row = data[data['nom_commune_postal'].str.lower() == ville_clean.lower()]
        if not row.empty:
            url = f"https://www.atmo-hdf.fr/air-commune/{ville_clean}/{row.iloc[0]['code_commune_INSEE']}/pollen?adresse={ville}+({row.iloc[0]['code_postal']})&date=2024-04-19"
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                balises_pollens = soup.find_all('p', class_='c-indice-pollen-taxon-title font-weight-bold text-center')
                balises_categories = soup.find_all('p', class_='text-uppercase mt-2')

                associations = []
                for pollen, categorie in zip(balises_pollens, balises_categories):
                    nom_pollen = pollen.get_text(strip=True)
                    nom_categorie = categorie.get_text(strip=True)
                    color = risk_to_color(nom_categorie)
                    color_circle = html.Span(style={'height': '20px', 'width': '20px', 'backgroundColor': color, 'borderRadius': '50%', 'display': 'inline-block', 'marginRight': '10px', 'marginLeft': '40px'})
                    associations.append((nom_pollen, color_circle, nom_categorie))

                output_rows = []
                for assoc in associations:
                    output_rows.append(html.Tr([html.Td(assoc[0]), html.Td([assoc[1], assoc[2]])]))
                    output_rows.append(html.Tr([html.Td('', style={'height': '10px'})]))  # Ligne vide avec hauteur

                output = html.Table([
                    html.Thead(html.Tr([html.Th("Pollen"), html.Th("Risque")])),
                    html.Tbody(output_rows)
                ])
                return output
            else:
                return "La requête a échoué avec le code : {}".format(response.status_code)
        else:
            return "Ville non trouvée."

# Fonction pour mettre à jour la carte
def update_map(ville):
    if ville:
        ville_clean = ville.replace(" ", "")
        row = data[data['nom_commune_postal'].str.lower() == ville_clean.lower()]
        if not row.empty:
            center_lat = row.iloc[0]['latitude']
            center_lon = row.iloc[0]['longitude']
            m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
            # Ajouter les contours de la ville
            ville_geojson_url = f"https://nominatim.openstreetmap.org/search.php?q={ville_clean}&polygon_geojson=1&format=json"
            response = requests.get(ville_geojson_url)
            if response.status_code == 200:
                ville_geojson = response.json()
                if len(ville_geojson) > 0:
                    folium.GeoJson(ville_geojson[0]['geojson'], name='Ville').add_to(m)
                else:
                    print("No GeoJSON data found for the city")
            else:
                print("Failed to download city GeoJSON data")
            m.save('zoomed_map.html')
            return open('zoomed_map.html', 'r').read()
        else:
            return open('hauts_de_france_map.html', 'r').read()
    else:
        return open('hauts_de_france_map.html', 'r').read()

# Callback pour mettre à jour la source de la carte lorsque la sélection de la ville change
@app.callback(
    Output('map-iframe', 'srcDoc'),
    Input('input-ville', 'value')
)
def update_map_src(ville):
    return update_map(ville)

if __name__ == '__main__':
    app.run_server(debug=False)
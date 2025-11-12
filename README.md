# GitHub Codespaces ♥️ Jupyter Notebooks

Hi collega! (English below)

Deze code berekent welke afvoerlocaties (postcodes) binnen een opgegeven straal liggen rondom een perceelcode en hoeveel paardenmest (in ton/jaar) daar vandaan komt.
Het script:
- haalt automatisch de coördinaten van het perceel op via de PDOK Locatieserver;
- leest de dataset met mestafvoer in;
- zet postcodes om naar coördinaten met pgeocode;
- berekent de afstand (haversine) van elk postcodegebied tot het perceel; 
- somt per postcode de tonnen en laadlocaties binnen de radius.
Daarnaast is er een optimalisatiefunctie: je geeft een doelwaarde in ton/jaar op en het script kiest greedily de grootste locaties (hoogste tonnage) binnen de radius totdat het target is bereikt.

Vereisten:
- Python ≥ 3.10
- Packages: pandas, numpy, requests, pgeocode, folium 
- Internettoegang (voor PDOK en pgeocode)
Installeer packages door dit in de terminal te typen en klik op enter: pip install pandas numpy requests pgeocode folium

Gebruik:
- Klik rechtsboven op "Run Python file" (driehoek-icoon), of open de terminal en voer het script uit met: python src/perceel_radius.py
- In de terminal verschijnt de vraag “Parcel code:” → vul hier de perceelcode in, bijvoorbeeld SLD02 H 1842 (perceelcodes kan je vinden op deze site: https://perceelloep.nl/)
- Vervolgens wordt gevraagd om de radius in kilometers → vul bijvoorbeeld 50 in.
- Daarna vraagt het script of Duitse postcodes moeten worden meegenomen → typ n of y
- Vervolgens vraagt het programma om het target in ton per jaar → geef aan hoeveel ton paardenmest je wilt selecteren binnen die radius (bijv. 60000)
- De resultaten worden direct in de terminal getoond. Je krijgt:
    Een overzicht van alle postcodes binnen de opgegeven radius;
    Het totale aantal ton mest en laadlocaties in dat gebied;
    En een optimalisatielijst met de grootste locaties (postcodes, ton mest, aantal laadlocaties en afstand tot het perceel) die samen het opgegeven target halen.

Na het uitvoeren van het script wordt automatisch een interactieve kaart opgeslagen in: ouputs/kaart.html
In GitHub Codespaces:
- Open de Explorer-zijbalk → navigeer naar de map outputs/
- Klik met de rechtermuisknop op het bestand → kies Download om het lokaal in je browser te openen
De kaart toont: een blauwe ster (de locatie van het perceel) en rode cirkels (de geselecteerde laadlocaties binnen de opgegeven straal) 

Opmerking over ontbrekende postcodes:
In de dataset zitten twee postcodes die niet worden herkend door pgeocode, omdat ze niet bestaan of geen geldige geografische coördinaten hebben: 000BL en 47264. Deze postcodes worden automatisch overgeslagen tijdens de verwerking.







Parcel Radius Analysis (EN)

This script calculates which disposal locations (zip codes) fall within a specified radius around a given parcel code and how much horse manure (in tons per year) originates from those locations. The script:
- automatically retrieves the parcel’s coordinates via the PDOK Locatieserver;
- reads the manure disposal dataset;
- converts postcodes to coordinates using pgeocode;
- calculates the distance (using the Haversine formula) from each postcode area to the parcel;
- aggregates the total tons and number of loading sites per postcode within the radius.
In addition, there is an optimization function: you can specify a target value in tons per year, and the script will greedily select the largest locations (those with the highest tonnage) within the radius until the target is reached.

Requirements:
- Python ≥ 3.10
- Packages: pandas, numpy, requests, pgeocode, folium 
- Internet connection (required for PDOK and pgeocode)
Install the packages by typing this in your terminal and pressing Enter: pip install pandas numpy requests pgeocode folium

Usage:
- Click “Run Python File” (triangle icon) in the top right corner, or open a terminal and run: python src/perceel_radius.py
- When prompted for “Parcel code:”, enter the parcel code, for example: SLD02 H 1842 (You can look up parcel codes at https://perceelloep.nl/)
- Then enter the radius in kilometers, for example: 50
- The script will then ask whether to include German postcodes → type y or n
- Next, it will ask for the target in tons per year → enter how many tons of horse manure you want to accumulate within that radius (e.g. 60000)
- The results are displayed directly in the terminal. You will see:
    An overview of all zip codes within the given radius;
    The total amount of manure (tons) and number of loading sites in that area;
    And an optimization list showing the largest contributing locations (with postcode, tons per year, number of loading sites, and distance to the parcel) that together reach your specified target.

After execution, the script saves an interactive map to: outputs/kaart.html
In GitHub Codespaces:
- Open the Explorer sidebar → navigate to outputs/
- Right-click the file → Download to view it in your local browser
The map displays: a blue star (parcel location) and red circles (selected loading locations within the radius)

Note about missing zip codes:
There are two postcodes in the dataset that are not recognized by pgeocode, as they are invalid or have no valid geographic coordinates: 0000BL and 47264. These zip codes are automatically skipped during processing. 
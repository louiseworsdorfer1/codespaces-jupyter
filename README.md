# GitHub Codespaces ♥️ Jupyter Notebooks

Hi collega!

Deze code berekent welke afvoerlocaties (postcodes) binnen een opgegeven straal liggen rondom een perceelcode en hoeveel paardenmest (in tonnen) daar jaarlijks vandaan komt.
Het script haalt automatisch de coördinaten van het perceel op via de PDOK Locatieserver, leest de dataset met mestafvoer in, zet postcodes om naar coördinaten met behulp van pgeocode en rekent vervolgens de afstand van elk postcodegebied tot het perceel uit.
Daarna telt het per jaar en per postcode de totale hoeveelheid mest (in ton) en het aantal laadlocaties binnen de ingestelde radius.
De resultaten worden samengevat in de console, inclusief een overzicht van de totaalstatistieken.

Daarnaast bevat het script een optimalisatiefunctie waarmee gebruikers een doelwaarde in ton per jaar kunnen invullen. Op basis daarvan selecteert het programma automatisch de grootste laadlocaties, dus de locaties met de hoogste mesthoeveelheid, binnen de opgegeven radius, totdat het opgegeven target is bereikt. De uitvoer toont vervolgens een overzicht van deze geselecteerde locaties, inclusief hun postcode (PC6 of PC4), de hoeveelheid mest in ton per jaar, het aantal laadlocaties en de afstand tot het perceel.
Op deze manier kun je snel zien welke locaties het meest bijdragen aan het totaalvolume en welke combinatie van locaties samen voldoende is om het gewenste doel te behalen.

Gebruik:
- Klik rechtsboven op Run Python file (driehoek-icoon) of open de temrinal en voer het script uit met: python src/perceel_radius.py
- In de terminal verschijnt de vraag “Perceelcode:” → vul hier de perceelcode in, bijvoorbeeld ASD06 I 4008
- Vervolgens wordt gevraagd om de radius in kilometers → vul bijvoorbeeld 50 in.
- Daarna vraagt het script om het target in ton per jaar → geef aan hoeveel ton paardenmest je wilt halen binnen die radius (bijv. 60000)
- De resultaten worden direct in de terminal getoond. Je krijgt:
    Een overzicht van alle postcodes binnen de opgegeven radius;
    Het totale aantal ton mest en laadlocaties in dat gebied;
    En een optimalisatielijst met de grootste locaties (met postcode, ton mest, aantal laadlocaties en afstand tot het perceel) die samen het opgegeven target halen.
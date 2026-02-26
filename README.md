# Abschlussprojekt -- 2D-Federstruktur mit Topologieoptimierung

Dieses Projekt implementiert eine 2D-Federstruktur (Massenpunkte +
lineare Federn) mit numerischer Lösung des Gleichungssystems **K · u =
F** sowie einer schrittweisen Topologieoptimierung.\
Die Anwendung wird als interaktive Web-App mit **Streamlit**
bereitgestellt.

------------------------------------------------------------------------

## Installation

### 1. Repository klonen

Zuerst das Repository von GitHub klonen:

``` bash
git clone <REPOSITORY-URL>
cd <REPOSITORY-ORDNER>
```

Beispiel:

``` bash
git clone https://github.com/username/abschlussprojekt.git
cd abschlussprojekt
```

------------------------------------------------------------------------

### 2. Virtuelle Umgebung erstellen

Im Projekt-Hauptordner eine virtuelle Python-Umgebung erstellen:

``` bash
python -m venv .venv
```

------------------------------------------------------------------------

### 3. Virtuelle Umgebung aktivieren

**Windows (PowerShell):**

``` bash
.venv\Scripts\activate
```

**Mac / Linux:**

``` bash
source .venv/bin/activate
```

Nach erfolgreicher Aktivierung erscheint `(.venv)` vor dem Konsolenpfad.

------------------------------------------------------------------------

### 4. Abhängigkeiten installieren

Die benötigten Python-Pakete werden über die `requirements.txt`
installiert:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

### 5. Installation überprüfen

Mit folgendem Befehl kann überprüft werden, ob die Pakete korrekt
installiert wurden:

``` bash
pip list
```

In der Liste sollten unter anderem folgende Pakete erscheinen:

-   numpy
-   matplotlib
-   streamlit
-   scipy
-   tindb

------------------------------------------------------------------------

### 6. Überprüfen der .gitignore-Konfiguration

Um sicherzustellen, dass die virtuelle Umgebung (`.venv`) nicht ins
Repository aufgenommen wird, kann folgender Befehl ausgeführt werden:

``` bash
git status
```

Die `.venv` darf in der Ausgabe **nicht** unter „Untracked files" oder
„Changes to be committed" erscheinen.

Falls `.venv` doch angezeigt wird, muss geprüft werden, ob die
`.gitignore`-Datei folgende Einträge enthält:

    .venv/
    venv/
    __pycache__/
    *.pyc

------------------------------------------------------------------------

### 7. Anwendung starten

Nach erfolgreicher Installation kann die Streamlit-Anwendung gestartet
werden:

``` bash
streamlit run app.py
```

Die Anwendung öffnet sich anschließend automatisch im Browser.

------------------------------------------------------------------------

## Projektstruktur

    abschlussprojekt/
    │
    ├── .venv/                 # Virtuelle Umgebung (nicht im Repository)
    ├── src/                   # Quellcode
    │   |-- model.py
    │   |-- solver.py
    │   |-- viz.py
    |   |-- optimizer.py
    │   |-- __init__.py
    │
    ├── app.py                 # Streamlit-Hauptanwendung
    ├── requirements.txt       # Projektabhängigkeiten
    ├── README.md
    └── .gitignore

------------------------------------------------------------------------

## Verwendete Technologien

-   Python
-   NumPy (lineare Algebra)
-   Matplotlib (Visualisierung)
-   Streamlit (Web-Interface)
-   Tinydb (Datenbank)
-   Scipy

------------------------------------------------------------------------

## Funktionsweise Optimizer

1. Modell initialisieren
2. K * u = F lösen
3. Verformungsenergie berechnen
4. Wichtigkeit der Punkte bestimmen
5. Schwächste Punkte entfernen
6. Neue Masse berechnen
7. Wiederholen bis Soll-Masse erreicht

-----------------------------------------------------------------------

## Autor:innen

Artur Surberg und Julian Köll

Projekt im Rahmen des Moduls Softwaredesign.

# Abschlussprojekt -- 2D-Federstruktur mit Topologieoptimierung

Dieses Projekt implementiert eine 2D-Federstruktur (Massenpunkte + lineare Federn) mit numerischer Lösung des Gleichungssystems **K · u = F** sowie einer schrittweisen Topologieoptimierung.  
Die Anwendung wird als interaktive Web-App mit **Streamlit** bereitgestellt.

Neben den Minimalanforderungen wurden mehrere Erweiterungen implementiert, die im Folgenden beschrieben werden.

---

# Installation

## 1. Repository klonen

```bash
git clone <REPOSITORY-URL>
cd <REPOSITORY-ORDNER>
```

Beispiel:

```bash
git clone https://github.com/username/abschlussprojekt.git
cd abschlussprojekt
```

---

## 2. Virtuelle Umgebung erstellen

```bash
python -m venv .venv
```

---

## 3. Virtuelle Umgebung aktivieren

**Windows (PowerShell):**

```bash
.venv\Scripts\activate
```

**Mac / Linux:**

```bash
source .venv/bin/activate
```

---

## 4. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

---

## 5. Anwendung starten

```bash
streamlit run app.py
```

Die Anwendung öffnet sich anschließend automatisch im Browser.

---

# Projektstruktur

```
abschlussprojekt/
│
├── .venv/                 # Virtuelle Umgebung (nicht im Repository)
├── src/                   # Quellcode
│   ├── model.py
│   ├── solver.py
│   ├── viz.py
│   ├── optimizer.py
│   └── __init__.py
│
├── app.py                 # Streamlit-Hauptanwendung
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Verwendete Technologien

- Python  
- NumPy  
- SciPy  
- Matplotlib  
- Streamlit  
- TinyDB  
- ImageIO  

---

# Funktionsweise des Optimizers

1. Modell initialisieren  
2. Gleichungssystem **K · u = F** lösen  
3. Verformungsenergie berechnen  
4. Wichtigkeit der Knoten bestimmen  
5. Schwächste Knoten entfernen  
6. Neue Masse berechnen  
7. Wiederholen bis Zielmasse erreicht ist oder die Struktur instabil wird  

---

# Erweiterungen gegenüber den Minimalanforderungen

Im Rahmen dieses Abschlussprojekts wurden mehrere zusätzliche Features implementiert.

---

## Auswahl der Lagerung

In der Sidebar kann eingestellt werden, wie die Struktur gelagert werden soll.

- Lager befinden sich am linken unteren und rechten unteren Knoten
- Auswahl zwischen **Loslager** und **Festlager**
- Loslager blockieren nur die Bewegung in **z-Richtung**

---

## Auswahl des Kraftangriffspunkts

In der Sidebar befinden sich zwei Schieberegler:

- Auswahl des Knotens, an dem die Kraft angreift
- Kraft wirkt ausschließlich in **z-Richtung**
- Betrag der Kraft ist einstellbar

---

## Einstellbares Optimierungsziel

Die Stärke der Optimierung kann über einen Slider eingestellt werden:

- Faktor für die Zielmasse (0–1)
- Optimierung läuft, bis:
  - Zielmasse erreicht ist  
  - oder die Struktur instabil werden würde  

---

## Fortschrittsanzeige der Optimierung

Während der Optimierung wird eine Fortschrittsleiste angezeigt mit:

- Aktuelle Iteration
- Aktuelle Masse
- Anzahl verbleibender Knoten
- Prozentualer Fortschritt
- Visuelle Anzeige der Gewichtsreduktion

Die Leiste ist vollständig gefüllt, wenn das Zielgewicht erreicht wurde.

---

## Download aller Grafiken

Zusätzlich zur Minimalanforderung (Download der optimierten Struktur) können nun:

- Alle erzeugten Plots
- Heatmaps
- GIFs  

als **.png-Dateien** heruntergeladen werden.  
Unter jeder Grafik befindet sich ein Download-Button.

---

## Erweitertes Speichersystem (TinyDB)

Über die Minimalanforderung hinaus wurde ein erweitertes Speichersystem implementiert:

- Beliebig viele Strukturen können gespeichert werden
- Speicherung erfolgt in einer TinyDB-Datenbank
- Jede Struktur erhält eine ID
- Speicherung nur der optimierten Struktur
- Bestehende Namen werden überschrieben

### Verwaltung gespeicherter Strukturen

- Auswahl gespeicherter Strukturen über Dropdown-Menü
- Laden per „Laden“-Button
- Löschen per „Löschen“-Button
- Geladene Strukturen können weiter optimiert werden

---

## Plot-Modi

Die Darstellung der Struktur kann angepasst werden:

### 1️⃣ Nodes only
- Nur Knoten als Punkte
- Ideal für große Strukturen
- Übersichtlicher bei vielen Elementen

### 2️⃣ Lines (Federn)
- Knoten + Federn sichtbar
- Detaillierte Darstellung
- Geeignet für kleinere Strukturen

### 3️⃣ Auto-Modus (Standard)
- Automatische Umschaltung je nach Strukturgröße
- Kombination aus Übersichtlichkeit und Detailtiefe

---

## Heatmap-Darstellung

Für deformierte Strukturen kann eine Heatmap aktiviert werden:

- Farbige Darstellung abhängig von Verformungsenergie
- Funktioniert für:
  - Nodes only
  - Lines (Federn)
- Umschaltbar auch nach abgeschlossener Optimierung

---

## Darstellung der Optimierung als GIF

Optional kann während der Optimierung ein GIF erzeugt werden:

- Checkbox vor Start der Optimierung aktivieren
- Jede Iteration wird als Bild gespeichert
- Am Ende werden alle Bilder zu einem GIF zusammengefügt
- Anzeige auf der Webseite
- Download möglich

---

# Autor:innen

Artur Surberg  
Julian Köll  

Projekt im Rahmen des Moduls **Softwaredesign**.

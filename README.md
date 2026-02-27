# Abschlussprojekt -- 2D-Federstruktur mit Topologieoptimierung

Dieses Projekt implementiert eine 2D-Federstruktur (Massenpunkte + lineare Federn) mit numerischer Lösung des Gleichungssystems **K · u = F** sowie einer schrittweisen Topologieoptimierung.  
Die Anwendung wird als interaktive Web-App mit **Streamlit** bereitgestellt.

Neben den Minimalanforderungen wurden mehrere Erweiterungen implementiert.

---

# Installation

## 1. Repository klonen

```bash
git clone <REPOSITORY-URL>
cd <REPOSITORY-ORDNER>
```

## 2. Virtuelle Umgebung erstellen

```bash
python -m venv .venv
```

## 3. Virtuelle Umgebung aktivieren

**Windows (PowerShell):**

```bash
.venv\Scripts\activate
```

**Mac / Linux:**

```bash
source .venv/bin/activate
```

## 4. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

## 5. Anwendung starten

```bash
streamlit run app.py
```

---

# Projektstruktur

```
abschlussprojekt/
│
├── .venv/
├── src/
│   ├── __init__.py
│   ├── model.py
│   ├── solver.py
│   ├── viz.py
│   ├── optimizer.py
│   └── database.json
│
├── images/
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Erklärung der einzelnen Python-Dateien

### `app.py`
Hauptanwendung der Streamlit-Web-App.

Aufgaben:
- Aufbau der Benutzeroberfläche
- Verarbeitung der Benutzereingaben
- Steuerung von Solver und Optimizer
- Darstellung der Plots
- Download-Funktionen
- GIF-Erstellung
- Speicherung und Laden von Strukturen

`app.py` verbindet alle Module miteinander und bildet die zentrale Steuerungsschicht.

---

### `src/model.py`
Definiert die Datenstruktur des mechanischen Modells.

Enthält:
- Klasse `Node` (Knoten mit Koordinaten, Randbedingungen, Kräften)
- Klasse `Spring` (Feder zwischen zwei Knoten)
- Klasse `Structure` (Gesamtstruktur mit:
  - Knotensammlung
  - Federliste
  - Massenberechnung
  - Adjazenzberechnung
  - Entfernen von Knoten
  - Speichern/Laden über TinyDB)

Warum wichtig?
→ Trennt die Modelllogik sauber von Berechnung und Visualisierung.  
→ Macht die Struktur serialisierbar (Speichern in Datenbank).

---

### `src/solver.py`
Implementiert die numerische Lösung des Gleichungssystems:

\[
K \cdot u = F
\]

Aufgaben:
- Assemblierung der globalen Steifigkeitsmatrix
- Sparse- oder Dense-Berechnung (je nach Verfügbarkeit von SciPy)
- Behandlung von Randbedingungen
- Regularisierung bei singulären Matrizen
- Berechnung der Verschiebungen

Warum wichtig?
→ Herzstück der mechanischen Simulation  
→ Ermöglicht physikalisch korrekte Berechnung der Verformung

---

### `src/optimizer.py`
Implementiert die Topologieoptimierung.

Aufgaben:
- Berechnung der Verformungsenergie
- Bewertung der Knoten (Score-System)
- Entfernen energetisch unwichtiger Knoten
- Sicherstellung der Konnektivität
- Dead-End-Pruning
- Fortschritts-Callback
- Snapshot-Erstellung für GIF

Warum wichtig?
→ Realisiert die eigentliche Optimierungslogik  
→ Reduziert Masse bei Erhalt der strukturellen Stabilität

---

### `src/viz.py`
Verantwortlich für alle Visualisierungen.

Enthält:
- Plot der Originalstruktur
- Plot der deformierten Struktur
- Optimierte Struktur
- Nodes-only-Darstellung (Performance)
- Heatmap-Darstellung
- PNG-Export
- GIF-Erstellung

Warum wichtig?
→ Saubere Trennung zwischen Berechnung und Darstellung  
→ Ermöglicht verschiedene Plot-Modi ohne Logik-Duplikation

---

### `src/__init__.py`
Leere Datei zur Kennzeichnung des Ordners als Python-Package.

Warum wichtig?
→ Ermöglicht Imports wie `from src.model import ...`  
→ Erhöht Portabilität und Kompatibilität

---

### `src/database.json`
TinyDB-Datenbank zur Speicherung optimierter Strukturen.

Warum wichtig?
→ Ermöglicht dauerhaftes Speichern mehrerer Strukturen  
→ Realisiert das erweiterte Speichersystem

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
4. Wichtigkeit der Punkte bestimmen  
5. Schwächste Punkte entfernen  
6. Neue Masse berechnen  
7. Wiederholen bis Soll-Masse erreicht  

---

# Erweiterungen

Im Rahmen dieses Abschlussprojekts wurden nicht nur die Minimalanforderungen erfüllt, sondern ebenfalls einige Erweiterungen implementiert. Folgend wird jedes zusätzlich implementierte Feature kurz erklärt und beschrieben.

---

## Auswahl der Lagerung

In der Sidebar des User Interface lässt sich einstellen, wie die Struktur gelagert werden soll. Die Lager befinden sich hierbei immer am Knoten in der linken und in der rechten unteren Ecke der Struktur. Es lässt sich über ein Drop-Down Menü auswählen, ob Loslager oder Festlager verwendet werden sollen. Die Loslager blockieren hierbei nur die Bewegung in die z-Richtung.

![Auswahl der Lagerung](images/Auswahl_der_Lagerung.png)

---

## Auswahl des Kraftangriffspunkts

In der Sidebar sind zwei Schieberegler eingebaut, welche bestimmen, an welchem Knoten die Kraft angreifen soll. Die Richtung der Kraft ist hierbei immer in z-Richtung. Der Betrag der Kraft lässt sich ebenfalls einstellen.

![Auswahl des Kraftangriffspunkts](images/Auswahl_des_Kraftangriffspunktes.png)

---

## Optimierungsziel

Wie stark die Struktur optimiert wird, lässt sich in unserem Abschlussprojekt einstellen. Diese “Stärke” der Optimierung wird mithilfe der Zielmasse eingestellt. Dafür gibt es im UI einen Slider, mit der ein Faktor für die Zielmasse eingestellt werden kann (0-1). Die Struktur wird nach Bestätigung durch den Optimierungs-Button so lange optimiert, bis entweder Zielmasse erreicht wird oder die Struktur nicht mehr zusammenhalten würde.

![Optimierungsziel](images/Optimierungsziel.png)

---

## Fortschrittsanzeige der Optimierung

Während der laufenden Optimierung wird ganz oben eine Leiste dargestellt, welche anzeigt, wie weit die Optimierung bereits fortgeschritten ist. Die Leiste spiegelt hierbei den Fortschritt der Gewichtsreduzierung wieder, bei voller Leiste wurde das Zielgewicht erreicht. Ebenfalls wird angezeigt bei der wievielten Iteration das Programm gerade ist, wie hoch die Masse gerade ist, wieviele Knoten die Struktur noch besitzt und der Fortschritt in Prozent. In folgender Abbildung ist diese Anzeige dargestellt:

![Fortschrittsanzeige](images/Fortschrittsanzeige_der_Optimierung.png)

---

## Herunterladen der Grafiken

In den Minimalanforderungen ist festgelegt, dass man die optimierte Struktur als Bilddatei herunterladen können soll. In diesem Projekt haben wir zusätzlich implementiert, dass alle Plots und Grafiken als .png-Dateien heruntergeladen werden können. Dafür befindet sich unter jeder Grafik ein Button, mit dem man den Download starten kann.

---

## erweitertes Speichersystem

Die Minimalanforderungen verlangen, dass man die optimierte Struktur speichern und zu einem späteren Zeitpunkt wieder laden kann. In diesem Projekt wurde zusätzlich implementiert, dass beliebig viele Strukturen in der Datenbank, welche mit TinyDB umgesetzt wurde, abgespeichert werden können. Dafür gibt es in der Sidebar der UI ein Feld, wo ein Name für die Struktur festgelegt werden kann. Die Struktur wird dann mit einer bestimmten ID in die Datenbank gespeichert. Hierbei kann nur die optimierte Struktur abgespeichert werden. Existiert bereits eine Struktur mit dem gleichen Namen, so wird diese Struktur überschrieben.

Über das Drop-Down Menü ganz oben in der Seitenleiste können gespeicherte Strukturen anhand ihres Namens aus der Datenbank geladen werden und anschließend weiter optimiert werden. Dafür wird mit dem Drop-Down Menü eine Struktur ausgewählt und auf den Button “Laden” geklickt. Es besteht ebenfalls die Möglichkeit die ausgewählte Struktur mit dem Button “Löschen” wieder aus der Datenbank zu löschen.

![Speichersystem](images/Erweitertes_Speicherungssystem.png)

---

## Plot-Modus

Für dieses Abschlussprojekt wurde ein Feature implementiert, das die Darstellung der Plots einstellbar macht. Hierbei gibt es 3 verschiedene Modi: 

Im Modus “Nodes only” werden nur die Knoten der Struktur als Punkte im Plot gezeichnet. Dies eignet sich vor allem für Strukturen mit vielen Knoten, da das Diagramm sonst unübersichtlich werden würde.

Im Modus “Lines (Federn)” hingegen werden die Knoten samt allen Federn der Struktur geplottet, was vor allem bei kleineren Strukturen eine genauere Darstellung der Verformung ermöglicht.

Im standardmäßig eingestellten Modus “Auto” wird je nach Größe der Struktur (Anzahl der Knoten) umgeschalten zwischen der Darstellung mit den Federn und der Darstellung von den Knoten allein. In folgender Darstellung ist der Plot einer größeren Struktur (unverformt) dargestellt, der nur die Knoten enthält.

Hier ist nun eine kleinere Struktur (verformt) dargestellt. Hierbei sind auch die Federn abgebildet.

### Beispiel: Nodes only (optimiert)

![Optimized Nodes Only](images/optimized_(nodes_only).png)

### Beispiel: Lines (Federn) (deformiert)

![Optimized Lines](images/optimized.png)

### Auswahl im UI (Auto / Nodes only / Lines)

![Plot Modus](images/Plot_Modus.png)

---

## Plot als Heatmap

Für die Plots, die eine deformierte Struktur darstellen, wurde eine Option implementiert, mit der die Knoten/Federn je nach aufgenommener Verformungsenergie unterschiedlich eingefärbt werden. Dies geschieht über die Checkbox in der Sidebar:

Wenn die Option aktiviert ist, werden die beiden Grafiken der deformierten Plots als Heatmap dargestellt. Das funktioniert für beide Plot-Modi, nachfolgend ist eine Heatmap im “Lines (Federn)” Modus und eine im “Nodes only” Modus dargestellt. Es lässt sich auch nach der Optimierung noch zwischen der normalen Darstellung und der als Heatmap umschalten.

![Heatmap Option](images/Plot_als_Heatmap.png)

### Heatmap – Nodes only

![Heatmap Nodes](images/Energie_Heatmap_(Deformed).png)

### Heatmap – Lines (Federn)

![Heatmap Lines](images/Energie_Heatmap_(Deformed_2).png)

---

## Darstellung der Optimierung als GIF

In der Sidebar des UI gibt es eine Checkbox, die einstellt, ob für die Optimierung auch ein GIF erstellt werden soll. Für Erstellung eines GIFs muss die Option jedoch schon vor der Optimierung ausgewählt werden. Ist die Option aktiv, so wird für jeden Iterationsschritt des Optimierers eine Grafik erstellt. Diese Grafiken werden am Ende der Optimierung zu einem GIF zusammengefügt und ganz unten auf der Webseite angezeigt. Das GIF lässt sich so wie die anderen Grafiken herunterladen. Folgend ist ein solches GIF dargestellt.

![Optimierung GIF](images/optimization.gif)

---

# Autor:innen

Artur Surberg  
Julian Köll  

Projekt im Rahmen des Moduls **Softwaredesign**

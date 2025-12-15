# PDF-Creator - Automatische Rechnungserfassung mit KI-Lernsystem

## 🚀 Installation
```bash
pip install -r requirements.txt
cd webapp && python3 app.py
```
→ http://127.0.0.1:5001

## 📋 Projektbeschreibung
Entwicklung einer Webanwendung zur automatischen Erfassung und Verarbeitung von PDF-Eingangs- und Ausgangsrechnungen. Die Anwendung extrahiert Daten aus text-basierten PDFs mittels Regex-Pattern-Matching und nutzt ein selbstlernendes System (Confidence-Based Learning) zur kontinuierlichen Verbesserung der Extraktionsgenauigkeit.

## ✨ Funktionen
- **📄 PDF-Extraktion**: Hybrid-Ansatz mit pdfplumber (primär) und PyMuPDF (Fallback)
- **🎯 Intelligente Datenextraktion**: Über 50 Regex-Muster für robuste Erkennung verschiedener Formate
- **🤖 Selbstlernendes KI-System**: Vertrauensbasiertes Lernen (70% → 95% → 100%) mit Auto-Learning
- **🏢 Firmenspezifisches Lernen**: Korrekturen werden kontext-abhängig gespeichert
- **🖼️ Visuelles Highlighting**: Farbige Markierung extrahierter Daten im PDF mit Zoom-Funktion
- **📊 Sortierbare Tabellen**: Datenseite mit Sortierfunktion für alle Spalten
- **💯 Vertrauenswerte**: Individueller Sicherheitswert für jedes extrahierte Feld
- **🔧 Dynamische Konfiguration**: Ausschlusslisten in `config.json` - keine Code-Änderungen nötig
- **📊 Excel/CSV-Export**: Strukturierter Datenexport mit pandas
- **💾 JSON-Datenbank**: Selbstentwickelte SimpleDB-Klasse für Datenpersistenz
- **🎨 Weboberfläche**: Bootstrap-basierte Benutzeroberfläche mit Flask

## 👥 Team
- Rojda Polat
- Julia Kanter
- Malte Albig

## 🛠️ Technologie-Stack
- **Sprache**: Python 3.11+
- **Web-Framework**: Flask 2.3.3
- **PDF-Verarbeitung**: PyMuPDF 1.26.6, pdfplumber 0.11.4
- **Text-Extraktion**: Regex-basiert (KEIN OCR - nur text-basierte PDFs)
- **KI/ML**: Deterministisches vertrauensbasiertes Lernen (regelbasiert, kein neuronales Netz)
- **Datenbank**: Selbstentwickelte JSON-basierte SimpleDB-Klasse
- **Export**: pandas 2.0.3, openpyxl 3.1.2
- **Frontend**: Bootstrap 5.1.3, Jinja2-Vorlagen
- **Methodik**: SCRUM (1-2 Wochen Sprints)

## 📂 Projekt-Struktur
```
webapp/
├── app.py                  # Flask-Routen & Webserver (214 Zeilen)
├── database.py             # SimpleDB-Klasse & KI-Lernlogik (190 Zeilen)
├── pdf_processor.py        # PDF-Extraktion & Regex-Verarbeitung (411 Zeilen)
├── config.json             # Dynamische Ausschlusslisten (Auto-Learning)
├── templates/              # HTML-Vorlagen (Jinja2)
│   ├── home.html          # Upload-Seite
│   ├── result.html        # Verarbeitungsergebnis mit Vertrauenswerten
│   ├── training.html      # KI-Dashboard
│   └── data.html          # Rechnungsübersicht mit Sortierfunktion
├── static/uploads/         # Hochgeladene PDFs
└── invoices.json          # JSON-Datenbank
```

## 🎯 Kernfunktionalitäten

### 1. PDF-Verarbeitung (pdf_processor.py)
- **Hybrid-Extraktion**: pdfplumber für Tabellen/Layout, PyMuPDF als Fallback mit aussagekräftigen Konsolen-Meldungen
- **50+ Regex-Muster**: Firmenname, Rechnungsnummer, Datum, Beträge, Steuersätze
- **Intelligente Suchstrategien**: Anbieter-spezifische Logik (z.B. Tausendkraut oben, Parfumdreams unten)
- **Dynamische Ausschlusslisten**: `config.json` statt fest codiert - einfach editierbar ohne Code-Änderung
- **Vertrauenswerte**: Individueller Sicherheitswert (0-100%) für jedes extrahierte Feld
- **Visuelles Hervorheben**: Farbcodierte Markierungen mit Zoom-Modal
- **Auto-Learning**: Häufig korrigierte Wörter werden automatisch zur Ausschlussliste hinzugefügt

### 2. KI-Lernsystem (database.py)
- **Überwachtes Lernen**: Nutzer-Korrekturen werden als Trainingsdaten verwendet
- **Vertrauenswert-Bewertung**: 70% (1. Mal) → 95% (2. Mal) → 100% (3. Mal)
- **Firmenspezifisch**: Zuordnung wird nur für entsprechenden Anbieter angewendet
- **Auto-Korrektur**: Ab 60% Vertrauenswert automatische Anwendung (direkt ins Feld eingesetzt)
- **Auto-Learning**: Alle 5 Rechnungen werden häufig korrigierte Wörter (≥3x) automatisch zur `config.json` hinzugefügt
- **Intelligente Vorschläge**: KI-Vorschläge mit 75% Vertrauenswert bei fehlenden Werten

### 3. Modulare Architektur & Benutzeroberfläche
- **Trennung der Zuständigkeiten**: Webserver (app.py), Datenlogik (database.py), PDF-Verarbeitung (pdf_processor.py)
- **Sauberer Code**: Klare Verantwortlichkeiten und gut wartbare Modulstruktur
- **Wartbarkeit**: Jedes Modul hat eine eindeutige Aufgabe
- **Dynamische Konfiguration**: `config.json` für Ausschlusslisten (keine Code-Änderungen)
- **Sortierbare Tabellen**: Sortierfunktion auf Datenseite (JavaScript-basiert)
- **Zoom-Funktion**: Klick-zum-Zoomen für PDF-Vorschau (Modal mit ESC-Taste)
- **Vertrauensabzeichen**: 🟢 Grün (85-100%), 🟡 Gelb (60-84%), 🔴 Rot (0-59%)

## 🔍 Technische Details

### Vertrauensbasiertes Lernen
```python
# Extraktions-Vertrauenswerte (pdf_processor.py)
Firma (andere): 90%
Gesamtbetrag: 60-95% (je nach Muster-Übereinstimmung)
Nettobetrag: 85%
Steuersatz: 90%
Rechnungsnummer: 70-95% (je nach Muster)
Datum: 75-95%
Leistungsdatum: 60-95%
Beschreibung: 70%

# Lern-Vertrauenswerte (database.py)
1x Korrektur = 70% Vertrauenswert
2x Korrektur = 95% Vertrauenswert
3x Korrektur = 100% Vertrauenswert

# KI-Vorschläge
Fehlende Werte mit KI-Vorschlag = 75% Vertrauenswert
```

### Auto-Learning-Mechanismus
```python
# Alle 5 Rechnungen wird automatisch analysiert
if len(invoices) % 5 == 0:
    # Finde Wörter die ≥3x korrigiert wurden
    false_positives = get_frequently_corrected_words(field, min=3)
    # Füge automatisch zu config.json hinzu
    update_exclude_list("company_top", false_positives)
```

### Extraktions-Beispiele
```python
# Dynamische Ausschlusslisten aus config.json
exclude_company_top = ["Versandkosten", "Porto", "Lieferung", "Straße", ...]
exclude_description = ["Versandkosten", "Menge", "Preis", "€", ...]

# Intelligente Datumserkennung
parse_date("27 Dezember 2024") → "2024-12-27"
parse_date("27.12.2024") → "2024-12-27"

# Plausibilitätsprüfung Steuersatz
if 0 <= tax_rate <= 25:  # Nur gültige Steuersätze

# Vertrauenswert-basierte Anzeige
if confidence >= 0.85: badge = "🟢 Grün (85-100%)"
elif confidence >= 0.60: badge = "🟡 Gelb (60-84%)"
else: badge = "🔴 Rot (0-59%)"
```

## ⚠️ Einschränkungen
- **Nur text-basierte PDFs**: Keine OCR-Unterstützung für gescannte Dokumente
- **JSON-Datenbank**: Nicht für Mehrbenutzerbetrieb geeignet
- **Keine Authentifizierung**: Kein Benutzer-Login/Passwort-System
- **Entwicklungsserver**: Flask-Entwicklungsserver, nicht für Produktivbetrieb gedacht

## 🚀 Roadmap für kommerzielle Nutzung
1. **Sicherheit**: Benutzer-Login, HTTPS, Sitzungsverwaltung
2. **Datenbank**: Migration zu PostgreSQL/MySQL
3. **Produktionsserver**: Gunicorn + Nginx
4. **OCR-Integration**: Tesseract für gescannte PDFs
5. **DSGVO**: Datenschutzerklärung, Cookie-Zustimmung
6. **Testing**: Unit-Tests, CI/CD-Pipeline
7. **Überwachung**: Protokollierung, Fehler-Tracking (Sentry)
8. **Funktionen**: Batch-Upload, PDF-Hervorhebung-Download, DATEV-Export

## 📝 Lizenz
Dieses Projekt wurde im Rahmen eines Universitätsprojekts entwickelt.

## 🙏 Danksagungen
- PyMuPDF (fitz) für PDF-Verarbeitung
- pdfplumber für Layout-Erkennung
- Flask Community für das Web-Framework

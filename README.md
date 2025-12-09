# PDF-Creator - Automatische Rechnungserfassung mit KI-Lernsystem

## 🚀 Setup
```bash
pip install -r requirements.txt
cd webapp && python3 app.py
```
→ http://127.0.0.1:5001

## 📋 Projektbeschreibung
Entwicklung einer Webanwendung zur automatischen Erfassung und Verarbeitung von PDF-Eingangs- und Ausgangsrechnungen. Die Anwendung extrahiert Daten aus text-basierten PDFs mittels Regex-Pattern-Matching und nutzt ein selbstlernendes System (Confidence-Based Learning) zur kontinuierlichen Verbesserung der Extraktionsgenauigkeit.

## ✨ Features
- **📄 PDF-Extraktion**: Hybrid-Ansatz mit pdfplumber (primär) und PyMuPDF (Fallback)
- **🎯 Intelligente Datenextraktion**: Über 50 Regex-Pattern für robuste Erkennung verschiedener Formate
- **🤖 Selbstlernendes KI-System**: Confidence-Based Learning (70% → 95% → 100%)
- **🏢 Firmenspezifisches Lernen**: Korrekturen werden kontext-abhängig gespeichert
- **🖼️ Visuelles Highlighting**: Farbige Markierung extrahierter Daten im PDF
- **📊 Excel/CSV-Export**: Strukturierter Datenexport mit pandas
- **💾 JSON-Datenbank**: Selbstentwickelte SimpleDB-Klasse für Datenpersistenz
- **🎨 Webinterface**: Bootstrap-basierte Benutzeroberfläche mit Flask

## 👥 Team
- Rojda Polat
- Julia Kanter
- Malte Albig

## 🛠️ Technologie-Stack
- **Sprache**: Python 3.11+
- **Web-Framework**: Flask 2.3.3
- **PDF-Verarbeitung**: PyMuPDF 1.26.6, pdfplumber 0.11.4
- **Text-Extraktion**: Regex-basiert (KEIN OCR - nur text-basierte PDFs)
- **KI/ML**: Deterministisches Confidence-Based Learning (regelbasiert, kein neuronales Netz)
- **Datenbank**: Selbstentwickelte JSON-basierte SimpleDB-Klasse
- **Export**: pandas 2.0.3, openpyxl 3.1.2
- **Frontend**: Bootstrap 5.1.3, Jinja2-Templates
- **Methodik**: SCRUM (1-2 Wochen Sprints)

## 📂 Projekt-Struktur
```
webapp/
├── app.py                  # Flask-Routen & Webserver (198 Zeilen)
├── database.py             # SimpleDB-Klasse & KI-Lernlogik (197 Zeilen)
├── pdf_processor.py        # PDF-Extraktion & Regex-Parsing (306 Zeilen)
├── templates/              # HTML-Templates (Jinja2)
│   ├── home.html          # Upload-Seite
│   ├── result.html        # Verarbeitungsergebnis & Training
│   ├── training.html      # KI-Dashboard
│   └── data.html          # Rechnungsübersicht
├── static/uploads/         # Hochgeladene PDFs
└── invoices.json          # JSON-Datenbank
```

## 🎯 Kernfunktionalitäten

### 1. PDF-Verarbeitung (pdf_processor.py)
- **Hybrid-Extraktion**: pdfplumber für Tabellen/Layout, PyMuPDF als Fallback
- **50+ Regex-Pattern**: Firmenname, Rechnungsnummer, Datum, Beträge, Steuersätze
- **Intelligente Suchstrategien**: Anbieter-spezifische Logik (z.B. Tausendkraut oben, Parfumdreams unten)
- **False-Positive-Vermeidung**: Exclude-Listen für Begriffe wie "Versandkosten"
- **Visuelles Highlighting**: Farbcodierte Bounding-Boxes (Rot=Firma, Blau=Betrag, Grün=Nummer, etc.)

### 2. KI-Lernsystem (database.py)
- **Überwachtes Lernen**: Nutzer-Korrekturen werden als Training-Daten verwendet
- **Confidence-Scoring**: 70% (1. Mal) → 95% (2. Mal) → 100% (3. Mal)
- **Firmenspezifisch**: Mapping wird nur für entsprechenden Anbieter angewendet
- **Auto-Korrektur**: Ab 60% Confidence automatische Anwendung
- **Vorschläge**: Ab 40% Confidence als Hinweis angezeigt

### 3. Modulare Architektur
- **Separation of Concerns**: Webserver (app.py), Datenlogik (database.py), PDF-Verarbeitung (pdf_processor.py)
- **79% Code-Reduktion**: Von monolithischen 941 Zeilen auf 198 Zeilen (app.py)
- **Wartbarkeit**: Klare Verantwortlichkeiten pro Modul

## 🔍 Technische Details

### Confidence-Based Learning
```python
# Formel: min(1.0, 0.7 + (count - 1) * 0.25)
1x Korrektur = 70% Confidence
2x Korrektur = 95% Confidence
3x Korrektur = 100% Confidence
```

### Extraktions-Beispiele
```python
# Firmenname mit Exclude-Terms
exclude_terms = r'(Versandkosten|Porto|Lieferung|Straße|...)'

# Intelligente Datum-Erkennung
parse_date("27 Dezember 2024") → "2024-12-27"
parse_date("27.12.2024") → "2024-12-27"

# Plausibilitätsprüfung Steuersatz
if 0 <= tax_rate <= 25:  # Nur gültige Steuersätze
```

## ⚠️ Limitationen
- **Nur text-basierte PDFs**: Keine OCR-Unterstützung für gescannte Dokumente
- **JSON-Datenbank**: Nicht für Multi-User-Produktivbetrieb geeignet
- **Keine Authentifizierung**: Kein User-Login/Passwort-System
- **Development Server**: Flask-Dev-Server, nicht für Production gedacht

## 🚀 Roadmap für kommerzielle Nutzung
1. **Sicherheit**: User-Login, HTTPS, Session-Management
2. **Datenbank**: Migration zu PostgreSQL/MySQL
3. **Production-Server**: Gunicorn + Nginx
4. **DSGVO**: Datenschutzerklärung, Cookie-Consent
5. **Testing**: Unit-Tests, CI/CD Pipeline
6. **Monitoring**: Logging, Error-Tracking (Sentry)

## 📝 Lizenz
Dieses Projekt wurde im Rahmen eines Universitätsprojekts entwickelt.

## 🙏 Acknowledgments
- PyMuPDF (fitz) für PDF-Verarbeitung
- pdfplumber für Layout-Erkennung
- Flask Community für das Web-Framework

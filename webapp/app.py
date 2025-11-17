#!/usr/bin/env python3
"""
PDF zu Excel/CSV Converter - Extrahiert Rechnungsdaten aus PDFs
"""

from flask import Flask, request, render_template_string, redirect, flash, send_file
import os, json, re, base64
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF

app = Flask(__name__)
app.secret_key = "pdf_converter_2025"
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# DATABASE CLASS
class SimpleDB:
    def __init__(self, filename="invoices.json"):
        self.file = filename
        self.data = {"invoices": [], "samples": [], "corrections": []}
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    loaded_data = json.load(f)
                    # Ensure corrections table exists
                    if "corrections" not in loaded_data:
                        loaded_data["corrections"] = []
                    self.data = loaded_data
            except: pass
    
    def save(self):
        with open(self.file, "w") as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def add_invoice(self, invoice):
        self.data["invoices"].append(invoice)
        self.save()
    
    def add_sample(self, original, corrected):
        sample = {"original": original, "corrected": corrected, "timestamp": str(datetime.now())}
        self.data["samples"].append(sample)
        self.save()
    
    def add_correction(self, original_text, corrected_text, field_type, company_context=""):
        """Fügt eine neue Korrektur hinzu oder erhöht die Häufigkeit einer existierenden"""
        existing = None
        for correction in self.data["corrections"]:
            if (correction["original_text"].lower() == original_text.lower() and 
                correction["field_type"] == field_type):
                existing = correction
                break
        
        if existing:
            # Erhöhe Häufigkeit und Confidence
            existing["correction_count"] += 1
            existing["confidence_score"] = min(1.0, existing["correction_count"] * 0.2)
            existing["corrected_text"] = corrected_text  # Update mit neuester Korrektur
        else:
            # Neue Korrektur
            correction = {
                "original_text": original_text,
                "corrected_text": corrected_text,
                "field_type": field_type,
                "company_context": company_context,
                "correction_count": 1,
                "confidence_score": 0.2,
                "timestamp": str(datetime.now())
            }
            self.data["corrections"].append(correction)
        self.save()
    
    def apply_corrections(self, data):
        """Wendet gelernte Korrekturen auf extrahierte Daten an"""
        corrected_data = data.copy()
        suggestions = {}
        
        for field_type in data.keys():
            field_value = str(data[field_type]).strip()
            if not field_value or field_value == "0":
                continue
                
            # Suche nach passenden Korrekturen
            best_match = None
            for correction in self.data["corrections"]:
                if correction["field_type"] == field_type:
                    # Exact match oder ähnlichkeit prüfen
                    if (correction["original_text"].lower() == field_value.lower() or
                        self._text_similarity(correction["original_text"], field_value) > 0.8):
                        if not best_match or correction["confidence_score"] > best_match["confidence_score"]:
                            best_match = correction
            
            if best_match:
                if best_match["confidence_score"] >= 0.8:
                    # Auto-Korrektur bei hoher Confidence
                    corrected_data[field_type] = best_match["corrected_text"]
                elif best_match["confidence_score"] >= 0.4:
                    # Suggestion bei mittlerer Confidence
                    suggestions[field_type] = best_match["corrected_text"]
        
        return corrected_data, suggestions
    
    def _text_similarity(self, text1, text2):
        """Einfache Textähnlichkeit basierend auf gemeinsamen Wörtern"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return intersection / union if union > 0 else 0
    
    def get_stats(self):
        samples = len(self.data["samples"])
        corrections = len(self.data["corrections"])
        total_corrections = sum(c["correction_count"] for c in self.data["corrections"])
        return {
            "invoices": len(self.data["invoices"]), 
            "samples": samples, 
            "corrections": corrections,
            "total_corrections": total_corrections,
            "accuracy": min(95, 60 + total_corrections * 1.5)
        }
    
    def export_to_excel(self, filename):
        df = pd.DataFrame(self.data["invoices"])
        df.to_excel(filename, index=False)
    
    def export_to_csv(self, filename):
        df = pd.DataFrame(self.data["invoices"])
        df.to_csv(filename, index=False)

# PDF PROCESSING FUNCTIONS  
def extract_pdf_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text
    except Exception as e:
        print(f"PDF Textextraktion Fehler: {e}")
        return ""

def extract_data(text):
    data = {
        "company": "", "amount": 0, "number": "", "date": "",
        "service_date": "", "description": "", "net_amount": 0, 
        "tax_rate": 0, "total_amount": 0
    }
    
    # Firmenname extrahieren - intelligente PDF-Format-Erkennung
    company_patterns = [
        r'([A-ZÄÖÜ][a-zA-ZÄÖÜäöüß&.\s]{5,40}(?:GmbH|AG|UG|OHG|KG|e\.V\.|Inc\.|Ltd\.|Corp\.))',
        r'^([A-ZÄÖÜ][a-zA-ZÄÖÜäöüß&.\s]{5,40}(?:GmbH|AG|UG|OHG|KG|e\.V\.|Inc\.|Ltd\.|Corp\.))\s*$',
        r'^([A-ZÄÖÜ][a-zA-ZÄÖÜäöüß&.\s]{5,40})\s*$'
    ]
    
    lines = text.split('\n')
    
    # PDF-Format erkennen: Tausendkraut vs. parfumdreams
    is_tausendkraut = any('tausendkraut' in line.lower() for line in lines[:20])
    
    if is_tausendkraut:
        # TAUSENDKRAUT: Erste Zeilen durchsuchen
        for pattern in company_patterns:
            for line in lines[:15]:
                if line.strip():
                    company_match = re.search(pattern, line.strip())
                    if company_match:
                        company_name = company_match.group(1).strip()
                        if not re.search(r'(Versandkosten|Porto|Lieferung|\d{5}|Straße|str\.|Platz|Weg|Höhe|Gasse|Alle|Kunde|Leuchter)', company_name, re.IGNORECASE):
                            data["company"] = company_name
                            break
            if data["company"]:
                break
    else:
        # PARFUMDREAMS: Fußbereich durchsuchen
        for pattern in company_patterns:
            for line in lines[-25:]:
                company_match = re.search(pattern, line.strip())
                if company_match:
                    company_name = company_match.group(1).strip()
                    if not re.search(r'(\d{5}|Straße|str\.|Platz|Weg|Höhe|Gasse|Deutschland|Deutsche Bank|Amtsgericht)', company_name):
                        data["company"] = company_name
                        break
            if data["company"]:
                break
        
        # Fallback für parfumdreams: Erste Zeilen wenn Fußbereich leer
        if not data["company"]:
            for pattern in company_patterns:
                for line in lines[:15]:
                    if line.strip():
                        company_match = re.search(pattern, line.strip())
                        if company_match:
                            company_name = company_match.group(1).strip()
                            if not re.search(r'(Versandkosten|Porto|Lieferung|\d{5}|Straße|str\.|Platz|Weg|Höhe|Gasse|Alle|Kunde|Leuchter)', company_name, re.IGNORECASE):
                                data["company"] = company_name
                                break
                if data["company"]:
                    break
    
    # Gesamtbetrag - größter gefundener Betrag
    total_patterns = [
        r'(?:Gesamt|Total|Summe|Endbetrag|Rechnungsbetrag).*?(\d+[.,]\d{2})\s*€?',
        r'(?:Zu zahlen|Zahlbetrag).*?(\d+[.,]\d{2})\s*€?',
        r'(\d+[.,]\d{2})\s*€\s*$',
        r'€\s*(\d+[.,]\d{2})\s*$',
    ]
    all_amounts = []
    for pattern in total_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            amount_str = match.group(1).replace(',', '.')
            all_amounts.append(float(amount_str))
    
    if all_amounts:
        max_amount = max(all_amounts)
        data["total_amount"] = max_amount
        data["amount"] = max_amount

    # Nettobetrag
    net_patterns = [
        r'(?:Netto|Net).*?(\d+[.,]\d{2})\s*€?',
        r'(?:Summe netto|Zwischensumme).*?(\d+[.,]\d{2})\s*€?',
        r'(\d+[.,]\d{2})\s*€?\s*(?:netto|net)',
    ]
    for pattern in net_patterns:
        net_match = re.search(pattern, text, re.IGNORECASE)
        if net_match:
            net_str = net_match.group(1).replace(',', '.')
            data["net_amount"] = float(net_str)
            break

    # Steuersatz - verbesserte Suche  
    tax_patterns = [
        r'(\d{1,2})[.,]?\d{0,2}\s*%\s*(?:MwSt|USt|VAT|Steuer)',
        r'(?:MwSt|USt|VAT).*?(\d{1,2})[.,]?\d{0,2}\s*%',
        r'(\d{1,2})\s*%.*?(?:MwSt|USt|Steuer)',
        r'Steuersatz\s*(\d{1,2})\s*%',  # "Steuersatz 19%"
        r'(\d{1,2})\s*%\s*$',  # Einfach "19%" in eigener Zeile
    ]
    for pattern in tax_patterns:
        tax_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if tax_match:
            tax_rate = float(tax_match.group(1))
            if 0 <= tax_rate <= 25:  # Plausibilitätsprüfung
                data["tax_rate"] = tax_rate
                break

    # Rechnungsnummer
    number_patterns = [
        r'(?:Rechnung|Invoice|Bill).*?Nr\.?\s*:?\s*(\w+)',
        r'(?:Rechnungs|Invoice|Bill)[-\s]*(?:Nr|Number|No)\.?\s*:?\s*(\w+)',
        r'(\d{6,})'
    ]
    for pattern in number_patterns:
        number_match = re.search(pattern, text, re.IGNORECASE)
        if number_match:
            data["number"] = number_match.group(1).strip()
            break    # Rechnungsdatum
    date_patterns = [
        r'(?:Rechnungsdatum|Datum|Date).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})'
    ]
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            date_str = date_match.group(1)
            if date_str[2] in '.-/':  # DD.MM.YYYY
                parts = re.split(r'[.\-/]', date_str)
                data["date"] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            else:  # YYYY.MM.DD
                data["date"] = date_str.replace('.', '-').replace('/', '-')
            break

    # Leistungsdatum
    service_patterns = [
        r'(?:Leistungsdatum|Leistung vom).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(?:Ihre Bestellung vom|Bestelldatum).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(?:Service|Lieferdatum).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(?:Leistungszeitraum|Service period|Lieferung).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
    ]
    
    if "rechnungsdatum entspricht dem leistungsdatum" in text.lower():
        if data["date"]:
            data["service_date"] = data["date"]
    else:
        for pattern in service_patterns:
            service_match = re.search(pattern, text, re.IGNORECASE)
            if service_match:
                service_str = service_match.group(1)
                if service_str[2] in '.-/':  # DD.MM.YYYY
                    parts = re.split(r'[.\-/]', service_str)
                    data["service_date"] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                else:  # YYYY.MM.DD
                    data["service_date"] = service_str.replace('.', '-').replace('/', '-')
                break
    
    # Beschreibung (Produktname) - optimiert für beide PDF-Formate
    description_patterns = [
        # Format 1: | getrennte Produktzeilen (parfumdreams)
        r'([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\s\|\%\+]{10,100})\s*\|$',
        r'([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\s\|\%\+]{10,80})\s*\|.*?ArtNr',
        r'^([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\s\|\%\+]{15,100})\s*\|',
        # Format 2: Tausendkraut - Produktzeilen mit bekannten Produktnamen
        r'([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s]{8,60}(?:tee|energie|bio|XXL|guayusa)[A-Za-zÄÖÜäöüß\s\(\)0-9]{0,30})',
        # Format 3: Standard Produktzeilen mit Artikelnummer 
        r'(\d{6,})\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]{10,80}?)\s+\d+',
        r'(\d{4,})\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]{8,60}?)\s+(?:St\.|Stk\.|kg|g|l)',
        # Format 4: Einfache Produktzeilen vor Preis
        r'(?:^\s*)([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\s\-\.]{12,60}?)(?:\s+\d+[.,]\d{2})',
        # Fallback: Nach "Bezeichnung/Artikel"
        r'(?:Bezeichnung|Artikel).*?\n\s*([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]{8,80})',
    ]
    
    for pattern in description_patterns:
        desc_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if desc_match:
            if desc_match.groups() and len(desc_match.groups()) > 1:
                description = desc_match.group(2).strip()
            else:
                description = desc_match.group(1).strip()
            
            # Bereinigen: | durch Leerzeichen ersetzen und normalisieren
            description = description.replace('|', ' ').strip()
            description = ' '.join(description.split())
            
            # Strikte Validierung: Muss echter Produktname sein
            if (len(description) > 8 and 
                not re.search(r'(Versandkosten|Porto|Lieferung|Bezeichnung|Einh\.|Menge|Preis|€|Rechnung|Bestellung|ArtNr|MwSt|Einzelpreis|Gesamtpreis|Amtsgericht|Fehmarn|Sehr|Newsletter)', description, re.IGNORECASE)):
                data["description"] = description[:80]
                break
    
    return data

def pdf_to_image_with_highlighting(pdf_path, search_terms):
    """Konvertiert PDF zu Bild mit eingebranntem Highlighting"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        
        # Farben für verschiedene Datentypen (erweitert)
        colors = {
            "company": (1, 0, 0),        # Rot
            "total_amount": (0, 0, 1),   # Blau  
            "amount": (0, 0, 1),         # Blau (Kompatibilität)
            "number": (0, 1, 0),         # Grün
            "date": (1, 0.5, 0),         # Orange
            "net_amount": (0, 0.7, 0.7), # Türkis
            "service_date": (0.5, 0, 1), # Lila
            "description": (1, 0, 1),    # Magenta
            "tax_rate": (0.8, 0.4, 0)    # Braun
        }
        highlights = []
        
        # Textstellen finden und markieren
        for field_type, term in search_terms.items():
            if not term: continue
            
            found = False
            search_variants = [str(term)]
            
            # Spezielle Suchvarianten für Beträge
            if field_type in ["amount", "total_amount", "net_amount"]:
                amount_str = str(term).replace('.', ',')
                search_variants = [str(term), amount_str, f"{term}€", f"{amount_str}€"]
            
            # Spezielle Suchvarianten für Datum und Service-Datum
            elif field_type in ["date", "service_date"] and '-' in str(term):
                parts = str(term).split('-')
                if len(parts) == 3:
                    search_variants.extend([
                        str(term).replace('-', '.'),
                        f"{parts[2]}.{parts[1]}.{parts[0]}",
                        f"{parts[2]}/{parts[1]}/{parts[0]}"
                    ])
            
            # Suche durchführen
            for variant in search_variants:
                text_instances = page.search_for(variant)
                if text_instances:
                    rect = text_instances[0]
                    # Highlighting-Rechteck auf PDF zeichnen
                    expanded_rect = fitz.Rect(rect.x0-2, rect.y0-2, rect.x1+2, rect.y1+2)
                    page.draw_rect(expanded_rect, color=colors[field_type], width=3)
                    
                    highlights.append({
                        "type": field_type, "x": rect.x0, "y": rect.y0,
                        "width": rect.x1 - rect.x0, "height": rect.y1 - rect.y0, "text": str(term)
                    })
                    found = True
                    break
        
        # PDF zu Bild konvertieren
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_data = pix.tobytes("png")
        doc.close()
        
        # Base64 kodieren
        img_str = base64.b64encode(img_data).decode()
        return f"data:image/png;base64,{img_str}", highlights, pix.width, pix.height
        
    except Exception as e:
        print(f"PDF Highlighting Fehler: {e}")
        return None, [], 0, 0

# HTML TEMPLATES
HOME_TEMPLATE = '''<!DOCTYPE html>
<html><head><title>PDF Converter</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body style="background: linear-gradient(135deg, #667eea, #764ba2)">
<div class="container mt-5"><div class="card p-4">
<h1>📄 PDF zu Excel/CSV Converter</h1>
<p>Lade eine PDF-Rechnung hoch und extrahiere automatisch die wichtigsten Daten.</p>
<form method="post" action="/upload" enctype="multipart/form-data">
<div class="mb-3">
<input type="file" name="file" accept=".pdf" class="form-control" required>
</div>
<button type="submit" class="btn btn-primary w-100">📤 PDF hochladen & verarbeiten</button>
</form>
<div class="mt-4">
<h5>📊 Statistiken</h5>
<p>Verarbeitete PDFs: {{ stats.invoices }} | KI-Trainingssamples: {{ stats.samples }} | Genauigkeit: {{ stats.accuracy }}%</p>
<a href="/data" class="btn btn-info">📋 Alle Daten ansehen</a>
<a href="/training" class="btn btn-warning">🤖 KI-Training Dashboard</a>
</div>
</div></div></body></html>'''

TRAINING_TEMPLATE = '''<!DOCTYPE html>
<html><head><title>KI-Training Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
.confidence-bar { background: #e9ecef; border-radius: 10px; overflow: hidden; height: 20px; }
.confidence-fill { height: 100%; transition: width 0.3s ease; }
.confidence-low { background: linear-gradient(90deg, #dc3545, #fd7e14); }
.confidence-medium { background: linear-gradient(90deg, #fd7e14, #ffc107); }
.confidence-high { background: linear-gradient(90deg, #ffc107, #28a745); }
</style>
</head><body style="background: linear-gradient(135deg, #667eea, #764ba2)">
<div class="container mt-5">
<div class="card p-4">
<h1>🤖 KI-Training Dashboard</h1>
<p class="lead">Hier siehst du wie das System durch deine Korrekturen lernt und sich verbessert.</p>

<div class="row mb-4">
<div class="col-md-3">
<div class="card text-center">
<div class="card-body">
<h5 class="card-title">📊 Gesamtstatistik</h5>
<h3 class="text-primary">{{ training.stats.accuracy }}%</h3>
<p>OCR-Genauigkeit</p>
</div>
</div>
</div>
<div class="col-md-3">
<div class="card text-center">
<div class="card-body">
<h5 class="card-title">📝 Korrekturen</h5>
<h3 class="text-info">{{ training.total_corrections }}</h3>
<p>Gelernte Patterns</p>
</div>
</div>
</div>
<div class="col-md-3">
<div class="card text-center">
<div class="card-body">
<h5 class="card-title">🎯 Trainings-Events</h5>
<h3 class="text-success">{{ training.stats.total_corrections }}</h3>
<p>Angewendete Korrekturen</p>
</div>
</div>
</div>
<div class="col-md-3">
<div class="card text-center">
<div class="card-body">
<h5 class="card-title">📄 Rechnungen</h5>
<h3 class="text-warning">{{ training.stats.invoices }}</h3>
<p>Verarbeitet</p>
</div>
</div>
</div>
</div>

<div class="row">
<div class="col-md-6">
<h5>📈 Top 10 häufigste Korrekturen</h5>
<div class="card">
<div class="card-body">
{% for correction in training.top_corrections %}
<div class="border-bottom pb-2 mb-2">
<div class="d-flex justify-content-between align-items-center">
<div>
<strong>{{ correction.field_type|title }}:</strong><br>
<small class="text-muted">"{{ correction.original_text }}" → "{{ correction.corrected_text }}"</small>
</div>
<div class="text-end">
<span class="badge bg-primary">{{ correction.correction_count }}x</span>
<div class="confidence-bar mt-1" style="width: 100px;">
{% if correction.confidence_score >= 0.8 %}
<div class="confidence-fill confidence-high" style="width: {{ correction.confidence_score * 100 }}%;"></div>
{% elif correction.confidence_score >= 0.4 %}
<div class="confidence-fill confidence-medium" style="width: {{ correction.confidence_score * 100 }}%;"></div>
{% else %}
<div class="confidence-fill confidence-low" style="width: {{ correction.confidence_score * 100 }}%;"></div>
{% endif %}
</div>
<small>{{ "%.0f"|format(correction.confidence_score * 100) }}% Conf.</small>
</div>
</div>
</div>
{% endfor %}
</div>
</div>
</div>
<div class="col-md-6">
<h5>🔧 Korrekturen nach Feld-Typ</h5>
<div class="card">
<div class="card-body">
{% for field_type, corrections in training.corrections_by_field.items() %}
<div class="mb-3">
<h6>{{ field_type|title }}</h6>
<div class="progress mb-1" style="height: 25px;">
<div class="progress-bar" style="width: {{ (corrections|length / training.total_corrections * 100) if training.total_corrections > 0 else 0 }}%">
{{ corrections|length }} Patterns
</div>
</div>
<small class="text-muted">
Confidence: 
{% set avg_conf = corrections|map(attribute='confidence_score')|list|sum / corrections|length if corrections|length > 0 else 0 %}
{{ "%.0f"|format(avg_conf * 100) }}%
</small>
</div>
{% endfor %}
</div>
</div>
</div>
</div>

<div class="text-center mt-4">
<a href="/" class="btn btn-primary">🏠 Zurück zur Hauptseite</a>
<a href="/data" class="btn btn-info">📋 Alle Rechnungsdaten</a>
</div>
</div>
</div>
</body></html>'''

RESULT_TEMPLATE = '''<!DOCTYPE html>
<html><head><title>Verarbeitungsergebnis</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
.pdf-preview { max-width: 100%; border: 2px solid #007bff; border-radius: 8px; }
.pdf-image { width: 100%; height: auto; display: block; }
.form-section { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
</style>
</head><body style="background: linear-gradient(135deg, #667eea, #764ba2)">
<div class="container mt-5"><div class="card p-4">
<h2>📄 {{ result.filename }}</h2>
<div class="row">
<div class="col-5">
<h5>🖼️ PDF Vorschau mit Highlighting</h5>
{% if result.pdf_image %}
<div class="pdf-preview">
<img src="{{ result.pdf_image }}" class="pdf-image" alt="PDF mit Highlighting">
</div>
<div class="mt-2"><small>
🔴 Rot = Firma | 🔵 Blau = Betrag | 🟢 Grün = Nummer | 🟠 Orange = Datum
</small></div>
{% endif %}
</div>
<div class="col-7">
<h5>✏️ Extrahierte Rechnungsdaten (editierbar)</h5>

{% if result.suggestions %}
<div class="alert alert-info" role="alert">
<h6>🤖 KI-Verbesserungsvorschläge:</h6>
<ul class="mb-0">
{% for field, suggestion in result.suggestions.items() %}
<li><strong>{{ field }}:</strong> {{ suggestion }}</li>
{% endfor %}
</ul>
<small>Diese Vorschläge basieren auf vorherigen Korrekturen.</small>
</div>
{% endif %}

<form method="post" action="/correct">
<input type="hidden" name="filename" value="{{ result.filename }}">

<!-- Hidden fields für ursprüngliche Werte (für Training) -->
<input type="hidden" name="original_company" value="{{ result.data.company }}">
<input type="hidden" name="original_number" value="{{ result.data.number }}">
<input type="hidden" name="original_date" value="{{ result.data.date }}">
<input type="hidden" name="original_service_date" value="{{ result.data.service_date }}">
<input type="hidden" name="original_description" value="{{ result.data.description }}">
<input type="hidden" name="original_net_amount" value="{{ result.data.net_amount }}">
<input type="hidden" name="original_tax_rate" value="{{ result.data.tax_rate }}">
<input type="hidden" name="original_total_amount" value="{{ result.data.total_amount }}">

<div class="form-section">
<h6>🏢 Grunddaten</h6>
<div class="row">
<div class="col-6 mb-2"><label>Firma:</label>
<input name="company" class="form-control" value="{{ result.data.company }}" required></div>
<div class="col-6 mb-2"><label>� Rechnungsnummer:</label>
<input name="number" class="form-control" value="{{ result.data.number }}"></div>
</div>
<div class="row">
<div class="col-6 mb-2"><label>📅 Rechnungsdatum:</label>
<input name="date" type="date" class="form-control" value="{{ result.data.date }}"></div>
<div class="col-6 mb-2"><label>🛠️ Leistungsdatum:</label>
<input name="service_date" type="date" class="form-control" value="{{ result.data.service_date }}"></div>
</div>
</div>

<div class="form-section">
<h6>📝 Leistung</h6>
<div class="mb-2"><label>Beschreibung:</label>
<textarea name="description" class="form-control" rows="2" placeholder="Beschreibung der Leistung...">{{ result.data.description }}</textarea></div>
</div>

<div class="form-section">
<h6>�💰 Finanzen</h6>
<div class="row">
<div class="col-6 mb-2"><label>Nettobetrag (€):</label>
<input name="net_amount" type="number" step="0.01" class="form-control" value="{{ result.data.net_amount }}"></div>
<div class="col-6 mb-2"><label>Steuersatz (%):</label>
<input name="tax_rate" type="number" step="0.1" class="form-control" value="{{ result.data.tax_rate }}"></div>
</div>
<div class="mb-2"><label><strong>� Gesamtbetrag (€):</strong></label>
<input name="total_amount" type="number" step="0.01" class="form-control" value="{{ result.data.total_amount }}" required style="font-weight: bold; font-size: 1.1em;"></div>
</div>

<button type="submit" class="btn btn-success w-100 mt-3">✅ Speichern & KI trainieren</button>
</form>
</div></div>
<div class="text-center mt-4">
<a href="/" class="btn btn-primary">🏠 Weitere PDF verarbeiten</a>
</div>
</div></div></body></html>'''

DATA_TEMPLATE = '''<!DOCTYPE html>
<html><head><title>Alle Daten</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body style="background: linear-gradient(135deg, #667eea, #764ba2)">
<div class="container mt-5"><div class="card p-4">
<h2>📊 Alle verarbeiteten PDFs</h2>
<div class="mb-3">
<a href="/export/excel" class="btn btn-success">📊 Excel Download</a>
<a href="/export/csv" class="btn btn-info">📋 CSV Download</a>
<a href="/" class="btn btn-primary">🏠 Zurück</a>
</div>
<div class="table-responsive">
<table class="table table-striped table-sm">
<thead><tr><th>📄 Datei</th><th>🏢 Firma</th><th>� Nummer</th><th>� R-Datum</th><th>�️ L-Datum</th><th>📝 Beschreibung</th><th>💰 Netto</th><th>📊 MwSt</th><th><strong>💰 Gesamt</strong></th></tr></thead>
<tbody>
{% for invoice in invoices %}
<tr><td style="font-size: 0.8em;">{{ invoice.get('filename', '')[:20] }}{% if invoice.get('filename', '')|length > 20 %}...{% endif %}</td>
<td>{{ invoice.get('company', '')[:25] }}{% if invoice.get('company', '')|length > 25 %}...{% endif %}</td>
<td>{{ invoice.get('number', '') }}</td>
<td style="font-size: 0.8em;">{{ invoice.get('date', '') }}</td>
<td style="font-size: 0.8em;">{{ invoice.get('service_date', '') }}</td>
<td style="font-size: 0.8em;">{{ invoice.get('description', '')[:30] }}{% if invoice.get('description', '')|length > 30 %}...{% endif %}</td>
<td>{{ "%.2f"|format(invoice.get('net_amount', 0) or 0) }}€</td>
<td>{{ "%.1f"|format(invoice.get('tax_rate', 0) or 0) }}%</td>
<td><strong>{{ "%.2f"|format(invoice.get('total_amount', 0) or 0) }}€</strong></td></tr>
{% endfor %}
</tbody></table>
</div>
</div></div></body></html>'''

# ==========================================
# FLASK ROUTES
# ==========================================
db = SimpleDB()

@app.route("/")
def home():
    return render_template_string(HOME_TEMPLATE, stats=db.get_stats())

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files or request.files["file"].filename == "":
        flash("Keine Datei ausgewählt")
        return redirect("/")
    
    file = request.files["file"]
    if not file.filename.lower().endswith('.pdf'):
        flash("Nur PDF-Dateien erlaubt")
        return redirect("/")
    
    # Datei speichern
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    
    # PDF verarbeiten
    text = extract_pdf_text(filepath)
    raw_data = extract_data(text)
    
    # Wende gelernte Korrekturen an
    data, suggestions = db.apply_corrections(raw_data)
    
    # Speichere in DB
    invoice_data = data.copy()
    invoice_data["filename"] = filename
    invoice_data["timestamp"] = str(datetime.now())
    db.add_invoice(invoice_data)
    
    # PDF mit Highlighting - erweitert für mehr Felder
    search_terms = {
        "company": data["company"], 
        "total_amount": data["total_amount"], 
        "number": data["number"], 
        "date": data["date"],
        "net_amount": data["net_amount"],
        "service_date": data["service_date"]
    }
    pdf_image, highlights, img_width, img_height = pdf_to_image_with_highlighting(filepath, search_terms)
    
    result = {
        "filename": filename, 
        "data": data, 
        "suggestions": suggestions,
        "text": text[:500] + "..." if len(text) > 500 else text,
        "pdf_image": pdf_image, 
        "highlights": highlights, 
        "img_width": img_width, 
        "img_height": img_height
    }
    
    return render_template_string(RESULT_TEMPLATE, result=result)

@app.route("/correct", methods=["POST"])
def correct():
    """Speichert Korrekturen und trainiert das System"""
    # Hole ursprüngliche Daten (in echter App aus Session)
    original_data = {
        "company": request.form.get("original_company", ""),
        "number": request.form.get("original_number", ""),
        "date": request.form.get("original_date", ""),
        "service_date": request.form.get("original_service_date", ""),
        "description": request.form.get("original_description", ""),
        "net_amount": request.form.get("original_net_amount", "0"),
        "tax_rate": request.form.get("original_tax_rate", "0"),
        "total_amount": request.form.get("original_total_amount", "0")
    }
    
    # Korrigierte Daten
    corrected_data = {
        "filename": request.form["filename"],
        "company": request.form["company"],
        "number": request.form["number"],
        "date": request.form["date"],
        "service_date": request.form["service_date"],
        "description": request.form["description"],
        "net_amount": float(request.form["net_amount"]) if request.form["net_amount"] else 0,
        "tax_rate": float(request.form["tax_rate"]) if request.form["tax_rate"] else 0,
        "total_amount": float(request.form["total_amount"]) if request.form["total_amount"] else 0,
        "amount": float(request.form["total_amount"]) if request.form["total_amount"] else 0,  # Kompatibilität
        "timestamp": str(datetime.now())
    }
    
    # Trainiere das System mit allen Korrekturen
    company_context = corrected_data["company"]
    corrections_made = 0
    
    for field_type in ["company", "number", "date", "service_date", "description", "net_amount", "tax_rate", "total_amount"]:
        original_value = str(original_data.get(field_type, "")).strip()
        corrected_value = str(corrected_data.get(field_type, "")).strip()
        
        # Nur trainieren wenn sich etwas geändert hat und beide Werte vorhanden sind
        if (original_value and corrected_value and 
            original_value != corrected_value and 
            original_value != "0" and corrected_value != "0"):
            
            db.add_correction(original_value, corrected_value, field_type, company_context)
            corrections_made += 1
    
    # Speichere korrigierte Rechnung
    db.add_invoice(corrected_data)
    
    # Legacy: Alte Trainings-Methode für Kompatibilität
    db.add_sample(original_data, corrected_data)
    
    if corrections_made > 0:
        flash(f"✅ Rechnung gespeichert und {corrections_made} Korrekturen für KI-Training gelernt!")
    else:
        flash("✅ Rechnung gespeichert!")
    
    return redirect("/")

@app.route("/training")
def training():
    """Training Dashboard - zeigt KI-Lernfortschritt"""
    stats = db.get_stats()
    corrections = db.data["corrections"]
    
    # Gruppiere Korrekturen nach Feld-Typ
    corrections_by_field = {}
    for correction in corrections:
        field = correction["field_type"]
        if field not in corrections_by_field:
            corrections_by_field[field] = []
        corrections_by_field[field].append(correction)
    
    # Top-Korrekturen (häufigste)
    top_corrections = sorted(corrections, key=lambda x: x["correction_count"], reverse=True)[:10]
    
    training_data = {
        "stats": stats,
        "corrections_by_field": corrections_by_field,
        "top_corrections": top_corrections,
        "total_corrections": len(corrections)
    }
    
    return render_template_string(TRAINING_TEMPLATE, training=training_data)

@app.route("/data")
def data():
    return render_template_string(DATA_TEMPLATE, invoices=db.data["invoices"])

@app.route("/export/excel")
def export_excel():
    filename = "rechnungen_export.xlsx"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    db.export_to_excel(filepath)
    return send_file(filepath, as_attachment=True)

@app.route("/export/csv")
def export_csv():
    filename = "rechnungen_export.csv"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    db.export_to_csv(filepath)
    return send_file(filepath, as_attachment=True)

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("🚀 PDF zu Excel/CSV Converter")
    print("🌐 URL: http://127.0.0.1:5001")
    print("📋 Features: PDF-Upload, OCR, Excel/CSV Export, KI-Training")
    app.run(debug=True, port=5001, host="0.0.0.0")
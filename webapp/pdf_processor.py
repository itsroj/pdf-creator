"""
PDF Processing Module - Handles PDF text extraction, data parsing, and highlighting
"""
import fitz  # PyMuPDF
import re
import base64


def extract_pdf_text(pdf_path):
    """Extract text from PDF file"""
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
    """Extract invoice data from PDF text using regex patterns"""
    data = {
        "invoice_type": "Eingangsrechnung",  # Default: Eingangsrechnung
        "company": "", "amount": 0, "number": "", "date": "",
        "service_date": "", "description": "", "net_amount": 0, 
        "tax_rate": 0, "total_amount": 0
    }
    
    # Hilfsfunktion: Firmenname in Zeilen suchen
    def find_company_in_lines(lines_to_search, patterns, exclude_terms):
        for pattern in patterns:
            for line in lines_to_search:
                if not line.strip():
                    continue
                match = re.search(pattern, line.strip())
                if match:
                    name = match.group(1).strip()
                    if not re.search(exclude_terms, name, re.IGNORECASE):
                        return name
        return None
    
    # Firmenname extrahieren
    company_patterns = [
        r'(Amazon\s+EU\s+S\.[aà]\.r\.L?\.?)',
        r'([A-ZÄÖÜ][a-zA-ZÄÖÜäöüß&.\s]{5,40}(?:GmbH|AG|UG|OHG|KG|e\.V\.|Inc\.|Ltd\.|Corp\.))',
        r'^([A-ZÄÖÜ][a-zA-ZÄÖÜäöüß&.\s]{5,40}(?:GmbH|AG|UG|OHG|KG|e\.V\.|Inc\.|Ltd\.|Corp\.))\s*$',
        r'^([A-ZÄÖÜ][a-zA-ZÄÖÜäöüß&.\s]{5,40})\s*$'
    ]
    exclude_top = r'(Versandkosten|Porto|Lieferung|\d{5}|Straße|str\.|Platz|Weg|Höhe|Gasse|Alle|Kunde|Leuchter)'
    exclude_bottom = r'(\d{5}|Straße|str\.|Platz|Weg|Höhe|Gasse|Deutschland|Deutsche Bank|Amtsgericht)'
    
    lines = text.split('\n')
    is_tausendkraut = any('tausendkraut' in line.lower() for line in lines[:20])
    
    # Suche: Oben für Tausendkraut, unten für Parfumdreams, dann Fallback oben
    if is_tausendkraut:
        data["company"] = find_company_in_lines(lines[:15], company_patterns, exclude_top)
    else:
        data["company"] = (find_company_in_lines(lines[-25:], company_patterns, exclude_bottom) or 
                          find_company_in_lines(lines[:15], company_patterns, exclude_top))
    
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
        r'Zwischensumme[:\s\n]*\(ohne[^)]+\)[:\s\n]*(?:USt\.[^€]+)?(\d+[.,]\d{2})\s*€',  # NEU: Amazon-Format
        r'(?:Netto|Net).*?(\d+[.,]\d{2})\s*€?',
        r'(?:Summe netto|Zwischensumme).*?(\d+[.,]\d{2})\s*€?',
        r'(\d+[.,]\d{2})\s*€?\s*(?:netto|net)',
    ]
    for pattern in net_patterns:
        net_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
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
            break
    
    # Rechnungsdatum
    date_patterns = [
        r'Rechnungsdatum[/\s\n]*Lieferdatum[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
        r'(?:Rechnungsdatum|Datum|Date).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(\d{1,2}\s+(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4})',
        r'(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})'
    ]
    
    # Hilfsfunktion: Datum zu ISO-Format konvertieren
    def parse_date(date_str):
        month_map = {'januar': '01', 'februar': '02', 'märz': '03', 'april': '04', 'mai': '05', 'juni': '06',
                     'juli': '07', 'august': '08', 'september': '09', 'oktober': '10', 'november': '11', 'dezember': '12'}
        if re.match(r'\d{1,2}\s+\w+\s+\d{4}', date_str):  # "27 Dezember 2024"
            parts = date_str.split()
            return f"{parts[2]}-{month_map.get(parts[1].lower(), '01')}-{parts[0].zfill(2)}"
        elif date_str[2] in '.-/':  # DD.MM.YYYY
            parts = re.split(r'[.\-/]', date_str)
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        else:  # YYYY.MM.DD
            return date_str.replace('.', '-').replace('/', '-')
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text, re.IGNORECASE)
        if date_match:
            data["date"] = parse_date(date_match.group(1))
            break

    # Leistungsdatum
    service_patterns = [
        r'Bestelldatum[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
        r'(?:Leistungsdatum|Leistung vom).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(?:Ihre Bestellung vom|Bestelldatum).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(?:Service|Lieferdatum).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
        r'(?:Leistungszeitraum|Service period|Lieferung).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',
    ]
    
    if "rechnungsdatum entspricht dem leistungsdatum" in text.lower() and data["date"]:
        data["service_date"] = data["date"]
    else:
        for pattern in service_patterns:
            service_match = re.search(pattern, text, re.IGNORECASE)
            if service_match:
                data["service_date"] = parse_date(service_match.group(1))
                break
        # Fallback
        if not data["service_date"] and data["date"]:
            data["service_date"] = data["date"]
    
    # Beschreibung (Produktname)
    description_patterns = [
        r'(Clinique[^\n]{10,80})',
        r'Verkauft von[^\n]+\n\s*([^\n]{20,80})\s+\d',
        r'([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\s\|\%\+]{10,100})\s*\|$',
        r'([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\s\|\%\+]{10,80})\s*\|.*?ArtNr',
        r'^([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\s\|\%\+]{15,100})\s*\|',
        r'([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s]{8,60}(?:tee|energie|bio|XXL|guayusa)[A-Za-zÄÖÜäöüß\s\(\)0-9]{0,30})',
        r'(\d{6,})\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]{10,80}?)\s+\d+',
        r'(\d{4,})\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]{8,60}?)\s+(?:St\.|Stk\.|kg|g|l)',
        r'(?:^\s*)([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\s\-\.]{12,60}?)(?:\s+\d+[.,]\d{2})',
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
    """Convert PDF to image with highlighted search terms"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        
        colors = {
            "company": (1, 0, 0),
            "total_amount": (0, 0, 1),  
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

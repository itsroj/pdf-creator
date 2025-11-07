#!/usr/bin/env python3
"""
PDF-Extraktor - Holt Daten aus PDF-Rechnungen
"""

import re
import PyPDF2
import pdfplumber
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(filepath):
    """Extrahiert Text aus PDF-Datei mit mehreren robusten Methoden"""
    text = ""
    
    # METHODE 1: pdfplumber (meist zuverlässiger)
    try:
        logger.info("Versuche pdfplumber...")
        with pdfplumber.open(filepath) as pdf:
            logger.info(f"PDF mit pdfplumber geöffnet: {len(pdf.pages)} Seiten")
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and len(page_text.strip()) > 0:
                        text += page_text + "\n"
                        logger.info(f"pdfplumber - Seite {page_num + 1}: {len(page_text)} Zeichen")
                    else:
                        logger.warning(f"pdfplumber - Seite {page_num + 1}: Kein Text")
                except Exception as page_error:
                    logger.warning(f"pdfplumber - Seite {page_num + 1} Fehler: {page_error}")
                    continue
            
            if len(text.strip()) > 50:
                logger.info(f"pdfplumber ERFOLGREICH: {len(text)} Zeichen extrahiert")
                return text
            else:
                logger.warning("pdfplumber: Wenig Text, versuche PyPDF2...")
                
    except Exception as e:
        logger.warning(f"pdfplumber fehlgeschlagen: {e}")
    
    # METHODE 2: PyPDF2 mit robustem Error-Handling
    try:
        logger.info("Versuche PyPDF2...")
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            logger.info(f"PyPDF2: {len(reader.pages)} Seiten gefunden")
            
            for page_num, page in enumerate(reader.pages):
                try:
                    # Verschiedene PyPDF2 Methoden versuchen
                    page_text = ""
                    
                    # Standard-Extraktion
                    try:
                        page_text = page.extract_text()
                        if page_text and len(page_text.strip()) > 0:
                            text += page_text + "\n"
                            logger.info(f"PyPDF2 Standard - Seite {page_num + 1}: OK")
                            continue
                    except Exception as std_error:
                        logger.warning(f"PyPDF2 Standard Fehler: {std_error}")
                    
                    # Alternative: Manuelle Text-Extraktion
                    try:
                        if hasattr(page, '_objects') and page._objects:
                            obj_text = str(page._objects)
                            # Bereinige den rohen Text
                            clean_text = re.sub(r'[^\w\s\.\,\-\€\d]', ' ', obj_text)
                            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                            if len(clean_text) > 50:
                                text += clean_text + "\n"
                                logger.info(f"PyPDF2 Manuell - Seite {page_num + 1}: OK")
                    except Exception as manual_error:
                        logger.warning(f"PyPDF2 Manuell Fehler: {manual_error}")
                        
                except Exception as page_error:
                    logger.error(f"PyPDF2 - Seite {page_num + 1} komplett unlesbar: {page_error}")
                    continue
            
            if len(text.strip()) > 20:
                logger.info(f"PyPDF2 ERFOLGREICH: {len(text)} Zeichen extrahiert")
                return text
                
    except Exception as e:
        logger.error(f"PyPDF2 fehlgeschlagen: {e}")
    
    # METHODE 3: Notfall-Fallback 
    logger.error("ALLE PDF-Extraktionsmethoden fehlgeschlagen")
    logger.error(f"Datei: {filepath}")
    return ""

def extract_invoice_data(text):
    """Extrahiert Rechnungsdaten aus PDF-Text"""
    
    data = {
        'supplier': 'Unbekannt',
        'total': 0.0,
        'invoice_number': 'Unbekannt',
        'date': 'Unbekannt',
        'type': 'Eingangsrechnung',
        'description': 'Keine Beschreibung'
    }
    
    if not text or len(text.strip()) < 10:
        return data
    
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    
    # Debug: Zeige PDF-Struktur
    logger.info("PDF-Analyse - erste 20 Zeilen:")
    for i, line in enumerate(lines[:20]):
        logger.info(f"  {i}: {line}")
    
    # 1. LIEFERANT ERMITTELN - Mehrere Strategien
    
    # A) Bekannte Online-Shops
    bekannte_shops = {
        'apodiscounter.de': 'Apodiscounter',
        'amazon.de': 'Amazon', 
        'otto.de': 'Otto',
        'zalando.de': 'Zalando',
        'mediamarkt.de': 'MediaMarkt',
        'saturn.de': 'Saturn',
        'ebay.de': 'eBay',
        'real.de': 'Real',
        'parfumdreams.de': 'Parfumdreams',
        'douglas.de': 'Douglas',
        'notino.de': 'Notino'
    }
    
    text_klein = text.lower()
    for webseite, firma in bekannte_shops.items():
        if webseite in text_klein:
            data['supplier'] = firma
            logger.info(f"Shop erkannt: {firma}")
            break
    
    # B) Suche nach Firmennamen (erste 15 Zeilen)
    if data['supplier'] == 'Unbekannt':
        for line in lines[:15]:
            line_clean = line.strip()
            # Suche nach typischen Firmenendungen
            for endung in ['GmbH', 'AG', 'KG', 'GmbH & Co', 'e.K.', 'UG', 'Serviceteam', 'Team']:
                if endung.lower() in line_clean.lower() and len(line_clean) < 60:
                    # Extrahiere Firmenname vor der Endung
                    if 'serviceteam' in line_clean.lower():
                        # Bei "parfumdreams.de Serviceteam" -> "Parfumdreams"
                        firma_name = line_clean.lower().replace('serviceteam', '').replace('.de', '').strip()
                        if len(firma_name) > 2:
                            data['supplier'] = firma_name.capitalize()
                    else:
                        data['supplier'] = line_clean[:40]
                    logger.info(f"Firma gefunden: {data['supplier']}")
                    break
            if data['supplier'] != 'Unbekannt':
                break
    
    # C) Fallback: Erste sinnvolle Zeile als Lieferant
    if data['supplier'] == 'Unbekannt':
        for line in lines[:8]:
            if (len(line) > 3 and len(line) < 50 and 
                not any(x in line.lower() for x in ['rechnung', 'invoice', 'datum', 'seite', 'page']) and
                re.search(r'[A-Za-z]{3,}', line)):
                data['supplier'] = line[:40]
                logger.info(f"Fallback Lieferant: {data['supplier']}")
                break
    
    
    # 2. BETRAG ERMITTELN - Verbesserte Suche nach Gesamtsumme
    alle_beträge = []
    for i, line in enumerate(lines):
        # Suche nach Schlüsselwörtern für Gesamtsumme
        if any(wort in line.lower() for wort in ['gesamt', 'total', 'summe', 'zu zahlen', 'betrag']):
            # Finde Geldbeträge in dieser Zeile (Format: 32,58 oder 15.99)
            geld = re.findall(r'(\d+[,\.]\d{2})', line)
            for betrag in geld:
                zahl = float(betrag.replace(',', '.'))
                alle_beträge.append(zahl)
                logger.info(f"Gesamtbetrag gefunden: {zahl}€")
        else:
            # Sammle auch andere Beträge als Fallback
            geld = re.findall(r'(\d+[,\.]\d{2})', line)
            for betrag in geld:
                zahl = float(betrag.replace(',', '.'))
                if zahl > 1.0:  # Ignoriere sehr kleine Beträge
                    alle_beträge.append(zahl)
    
    if alle_beträge:
        # Nimm den höchsten Betrag (meist Gesamtsumme)
        data['total'] = max(alle_beträge)
        logger.info(f"Betrag ausgewählt: {data['total']}€")
    
    # 3. RECHNUNGSNUMMER ERMITTELN - Mehrere Muster
    
    # A) Explizite Suche nach "Rechnungsnummer:"
    for line in lines:
        if 'rechnungsnummer' in line.lower():
            match = re.search(r'rechnungsnummer[:\s]*([A-Z0-9\-\._]{4,})', line, re.IGNORECASE)
            if match:
                data['invoice_number'] = match.group(1)
                logger.info(f"Rechnungsnr. explizit: {data['invoice_number']}")
                break
    
    # B) Suche nach Invoice/Bill Number
    if data['invoice_number'] == 'Unbekannt':
        for line in lines:
            if any(wort in line.lower() for wort in ['invoice', 'bill number', 'rechnung nr']):
                match = re.search(r'([A-Z0-9\-\._]{4,})', line)
                if match:
                    data['invoice_number'] = match.group(1)
                    logger.info(f"Invoice Nr.: {data['invoice_number']}")
                    break
    
    # C) Fallback: Suche nach typischen Nummernformaten
    if data['invoice_number'] == 'Unbekannt':
        for line in lines:
            # Verschiedene Nummernformate
            patterns = [
                r'(\d{2}-\d{8}-\d{1,2})',  # 12-34567890-1
                r'([A-Z]{2}\d{6,})',       # AB123456
                r'(\d{8,})',               # 12345678
                r'([A-Z0-9]{8,})'          # ABC12345
            ]
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    data['invoice_number'] = match.group(1)
                    logger.info(f"Nummer gefunden: {data['invoice_number']}")
                    break
            if data['invoice_number'] != 'Unbekannt':
                break
    
    
    # 4. DATUM ERMITTELN - Erweiterte Datumserkennung
    for line in lines:
        # Verschiedene Datumsformate
        patterns = [
            r'(\d{1,2}\.\d{1,2}\.\d{4})',    # 01.12.2023
            r'(\d{1,2}/\d{1,2}/\d{4})',      # 01/12/2023
            r'(\d{4}-\d{1,2}-\d{1,2})',      # 2023-12-01
            r'(\d{1,2}\.\d{1,2}\.\d{2})'     # 01.12.23
        ]
        for pattern in patterns:
            datum = re.search(pattern, line)
            if datum:
                data['date'] = datum.group(1)
                logger.info(f"Datum gefunden: {data['date']}")
                break
        if data['date'] != 'Unbekannt':
            break
    
    # 5. PRODUKTBESCHREIBUNG ERMITTELN - Intelligente Suche
    beschreibung_gefunden = False
    
    # Suche nach Produktbereich (meist nach Adresse/Header)
    for i, line in enumerate(lines):
        # Skip Header-Bereich (erste 10-15 Zeilen)
        if i < 10:
            continue
            
        # Filtere unerwünschte Zeilen
        skip_words = [
            'rechnung', 'datum', 'kanten', 'julia', 'marienleuchter', 'fehmarn', 
            'deutschland', 'bestellung', 'bedankt', 'kundennummer', 'bezahlart', 
            'anzahl', 'pzn', 'bezeichnung', 'mwst', 'steuerbetrag', 'preis', 
            'summe', 'email', 'telefon', 'fax', 'www', 'http', 'versand',
            'lieferung', 'zahlung', 'konto', 'iban', 'bic', 'bank'
        ]
        
        if any(wort in line.lower() for wort in skip_words):
            continue
            
        # Suche nach gültigen Produktzeilen
        if (len(line) > 8 and                           # Mindestlänge
            re.search(r'[A-Za-z]{3,}', line) and       # Enthält Buchstaben
            not line.isdigit() and                      # Nicht nur Zahlen
            not re.match(r'^[\d\s\.\,\-]+$', line)):   # Nicht nur Zahlen/Zeichen
            
            # Bereinige die Zeile
            sauber = line
            # Entferne Artikelnummern am Anfang
            sauber = re.sub(r'^\d+\s+', '', sauber)
            # Entferne Mengenangaben 
            sauber = re.sub(r'\s*\d+\s*(stück|stk|st|x)\s*', ' ', sauber, flags=re.IGNORECASE)
            # Entferne ml/g Angaben
            sauber = re.sub(r'\s*\(\d+\s*(ml|g|kg|l)\).*', '', sauber, flags=re.IGNORECASE)
            # Entferne Prozentangaben
            sauber = re.sub(r'\s*\d+%.*', '', sauber)
            # Entferne Preise am Ende
            sauber = re.sub(r'\s*\d+[,\.]\d{2}\s*€?.*$', '', sauber)
            # Entferne einzelne Zahlen am Ende
            sauber = re.sub(r'\s*\d+\s*$', '', sauber)
            sauber = sauber.strip()
            
            # Validiere Ergebnis
            if (len(sauber) > 4 and 
                not sauber.isdigit() and
                sum(c.isalpha() for c in sauber) >= 3):  # Mindestens 3 Buchstaben
                
                data['description'] = sauber[:80] + "..." if len(sauber) > 80 else sauber
                logger.info(f"Beschreibung gefunden: {data['description']}")
                beschreibung_gefunden = True
                break
    
    # Fallback für Beschreibung
    if not beschreibung_gefunden:
        # Suche nach längster sinnvoller Zeile im mittleren Bereich
        for i in range(5, min(25, len(lines))):
            line = lines[i]
            if (len(line) > 10 and 
                re.search(r'[A-Za-z]{4,}', line) and
                not any(wort in line.lower() for wort in ['rechnung', 'datum', 'kunde', 'adresse'])):
                data['description'] = line[:60] + "..." if len(line) > 60 else line
                logger.info(f"Fallback Beschreibung: {data['description']}")
                break
    
    logger.info(f"ERGEBNIS: {data['supplier']} | {data['total']}€ | Nr: {data['invoice_number']} | {data['description']}")
    return data
#!/usr/bin/env python3
"""
OCR-Modul für PDF-Textextraktion
Saubere, einfache Implementierung mit Tesseract
"""

import pytesseract
from PIL import Image
import pdf2image
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Einfacher, zuverlässiger PDF-Prozessor"""
    
    def __init__(self):
        """Initialisiert den PDF-Prozessor"""
        self.tesseract_config = '--oem 3 --psm 6 -l deu+eng'
        logger.info("📄 PDF-Prozessor initialisiert")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extrahiert Text aus PDF mit OCR"""
        try:
            logger.info(f"🔍 Extrahiere Text aus: {pdf_path}")
            
            # PDF zu Bildern konvertieren
            pages = pdf2image.convert_from_path(pdf_path)
            full_text = ""
            
            for i, page in enumerate(pages):
                logger.info(f"📃 Verarbeite Seite {i+1}/{len(pages)}")
                
                # OCR auf jede Seite anwenden
                page_text = pytesseract.image_to_string(
                    page, 
                    config=self.tesseract_config
                )
                full_text += page_text + "\n\n"
            
            logger.info(f"✅ Text extrahiert: {len(full_text)} Zeichen")
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"❌ OCR-Fehler: {str(e)}")
            raise Exception(f"OCR-Fehler: {str(e)}")
    
    def extract_invoice_data(self, text: str) -> Dict[str, Any]:
        """Extrahiert strukturierte Rechnungsdaten aus Text"""
        try:
            logger.info("🧮 Extrahiere Rechnungsdaten...")
            
            data = {
                'supplier': self._extract_supplier(text),
                'invoice_number': self._extract_invoice_number(text),
                'date': self._extract_date(text),
                'amount': self._extract_amount(text),
                'currency': self._extract_currency(text),
                'description': self._extract_description(text)
            }
            
            logger.info("✅ Rechnungsdaten extrahiert")
            return data
            
        except Exception as e:
            logger.error(f"❌ Datenextraktionsfehler: {str(e)}")
            return {
                'supplier': 'Nicht gefunden',
                'invoice_number': 'Nicht gefunden',
                'date': 'Nicht gefunden', 
                'amount': 'Nicht gefunden',
                'currency': 'EUR',
                'description': 'Nicht gefunden'
            }
    
    def _extract_supplier(self, text: str) -> str:
        """Extrahiert Lieferantennamen"""
        # Suche nach Firmenname am Anfang des Dokuments
        lines = text.split('\n')[:10]  # Erste 10 Zeilen
        
        for line in lines:
            line = line.strip()
            # Überspringt leere Zeilen und sehr kurze Zeilen
            if len(line) > 5 and not re.match(r'^[0-9\s\-\.]+$', line):
                # Ist wahrscheinlich Firmenname wenn es Buchstaben enthält
                if re.search(r'[A-Za-zÄÖÜäöüß]', line):
                    return line[:50]  # Maximal 50 Zeichen
        
        return "Unbekannter Lieferant"
    
    def _extract_invoice_number(self, text: str) -> str:
        """Extrahiert Rechnungsnummer"""
        patterns = [
            r'Rechnung(?:s-?Nr\.?|snummer)[\s:]*([A-Z0-9\-]+)',
            r'Invoice(?:\s?No\.?|Number)[\s:]*([A-Z0-9\-]+)',
            r'Nr\.?\s*([0-9]+)',
            r'#\s*([0-9]+)',
            r'([0-9]{4,})'  # Mindestens 4-stellige Zahl
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "RG-2025-001"
    
    def _extract_date(self, text: str) -> str:
        """Extrahiert Rechnungsdatum"""
        patterns = [
            r'Datum[\s:]*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',
            r'Date[\s:]*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',
            r'(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{4})',
            r'(\d{4}-\d{1,2}-\d{1,2})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Normalisiere Datum zu YYYY-MM-DD Format
                return self._normalize_date(date_str)
        
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_amount(self, text: str) -> str:
        """Extrahiert Rechnungsbetrag"""
        patterns = [
            r'Gesamtbetrag[\s:]*([0-9\.,]+)',
            r'Total[\s:]*([0-9\.,]+)',
            r'Summe[\s:]*([0-9\.,]+)',
            r'Betrag[\s:]*([0-9\.,]+)',
            r'([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})\s*€',
            r'€\s*([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})',
            r'([0-9]+[.,][0-9]{2})'
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Normalisiere Betrag
                normalized = self._normalize_amount(match)
                if normalized:
                    amounts.append(float(normalized))
        
        if amounts:
            # Größter Betrag ist wahrscheinlich der Gesamtbetrag
            max_amount = max(amounts)
            return f"{max_amount:.2f}"
        
        return "0.00"
    
    def _extract_currency(self, text: str) -> str:
        """Extrahiert Währung"""
        if '€' in text or 'EUR' in text.upper():
            return 'EUR'
        elif '$' in text or 'USD' in text.upper():
            return 'USD'
        elif '£' in text or 'GBP' in text.upper():
            return 'GBP'
        else:
            return 'EUR'  # Standard
    
    def _extract_description(self, text: str) -> str:
        """Extrahiert Beschreibung/Betreff"""
        lines = text.split('\n')
        
        # Suche nach aussagekräftigen Zeilen
        for line in lines[2:15]:  # Überspringt Header, schaut erste Zeilen
            line = line.strip()
            if (len(line) > 10 and len(line) < 100 and 
                re.search(r'[A-Za-zÄÖÜäöüß]', line) and 
                not re.match(r'^[0-9\s\-\.€$]+$', line)):
                return line
        
        return "Rechnung"
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalisiert Datum zu YYYY-MM-DD"""
        try:
            # Verschiedene Formate versuchen
            from datetime import datetime
            
            formats = ['%d.%m.%Y', '%d/%m/%Y', '%d.%m.%y', '%Y-%m-%d']
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
            
            return date_str
            
        except:
            from datetime import datetime
            return datetime.now().strftime('%Y-%m-%d')
    
    def _normalize_amount(self, amount_str: str) -> Optional[str]:
        """Normalisiert Betrag zu Dezimalformat"""
        try:
            # Entferne alle Leerzeichen
            amount_str = amount_str.replace(' ', '')
            
            # Deutsche Notation (1.234,56) zu englischer (1234.56)
            if ',' in amount_str and '.' in amount_str:
                # Prüfe welches zuletzt kommt
                comma_pos = amount_str.rfind(',')
                dot_pos = amount_str.rfind('.')
                
                if comma_pos > dot_pos:
                    # Komma ist Dezimaltrennzeichen
                    amount_str = amount_str.replace('.', '').replace(',', '.')
                else:
                    # Punkt ist Dezimaltrennzeichen
                    amount_str = amount_str.replace(',', '')
            elif ',' in amount_str:
                # Nur Komma - könnte Dezimaltrennzeichen sein
                if len(amount_str.split(',')[-1]) == 2:
                    amount_str = amount_str.replace(',', '.')
                else:
                    amount_str = amount_str.replace(',', '')
            
            return str(float(amount_str))
            
        except:
            return None

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Hauptfunktion: Verarbeitet PDF komplett"""
        try:
            logger.info(f"🚀 Starte PDF-Verarbeitung: {pdf_path}")
            
            # Text extrahieren
            text = self.extract_text_from_pdf(pdf_path)
            
            # Daten extrahieren
            data = self.extract_invoice_data(text)
            
            # Vollständiges Ergebnis
            result = {
                'filename': pdf_path.split('/')[-1],
                'status': 'success',
                'raw_text': text[:500] + '...' if len(text) > 500 else text,
                'extracted_data': data
            }
            
            logger.info("✅ PDF-Verarbeitung abgeschlossen")
            return result
            
        except Exception as e:
            logger.error(f"❌ PDF-Verarbeitungsfehler: {str(e)}")
            return {
                'filename': pdf_path.split('/')[-1],
                'status': 'error',
                'error': str(e),
                'extracted_data': {}
            }
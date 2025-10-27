#!/usr/bin/env python3
"""
EINFACHE KI für PDF-Verarbeitung - Anfängerfreundlich
Verwendet einfache Regel-basierte Erkennung statt komplexer ML-Algorithmen
"""

import re
from datetime import datetime

class SimpleInvoiceAI:
    """Einfache, regel-basierte KI für Rechnungen"""
    
    def __init__(self):
        """Initialisiert die einfache KI"""
        self.patterns = {
            'supplier': [
                r'([A-Z][a-z]+ (?:GmbH|AG|Ltd|Inc|UG))',  # Firmenname mit Rechtsform
                r'Rechnung von:?\s*([A-Za-z\s]+)',         # "Rechnung von: ..."
                r'Lieferant:?\s*([A-Za-z\s]+)',           # "Lieferant: ..."
            ],
            'amount': [
                r'Gesamt(?:betrag)?:?\s*€?\s*(\d+[,\.]\d{2})',  # Gesamtbetrag
                r'Summe:?\s*€?\s*(\d+[,\.]\d{2})',              # Summe
                r'Total:?\s*€?\s*(\d+[,\.]\d{2})',              # Total
                r'(\d+[,\.]\d{2})\s*€',                         # Betrag vor €
            ],
            'date': [
                r'Datum:?\s*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',     # Datum: DD.MM.YYYY
                r'Rechnungsdatum:?\s*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})', # Rechnungsdatum
                r'(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{4})',                  # DD.MM.YYYY
            ],
            'invoice_number': [
                r'Rechnung(?:snummer)?:?\s*([A-Z0-9\-]+)',     # Rechnungsnummer
                r'Invoice(?:\s+No\.?)?:?\s*([A-Z0-9\-]+)',     # Invoice No.
                r'Nr\.?\s*([A-Z0-9\-]+)',                      # Nr. ...
            ]
        }
        
        print("🤖 Einfache KI initialisiert - Anfängerfreundlich!")
    
    def extract_data(self, text: str) -> dict:
        """Extrahiert Daten mit einfachen Regeln"""
        results = {}
        
        # Für jedes Feld die Muster durchgehen
        for field, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    results[field] = match.group(1).strip()
                    break  # Erstes Match verwenden
        
        # Nachbearbeitung
        if 'amount' in results:
            results['amount'] = results['amount'].replace(',', '.')
            results['currency'] = 'EUR'
        
        # Fallbacks für leere Felder
        for field in ['supplier', 'amount', 'date', 'invoice_number']:
            if field not in results:
                results[field] = ''
        
        results['description'] = self._generate_description(results)
        
        return results
    
    def _generate_description(self, data: dict) -> str:
        """Erstellt automatisch eine Beschreibung"""
        supplier = data.get('supplier', 'Unbekannter Lieferant')
        amount = data.get('amount', '0.00')
        date = data.get('date', 'Unbekanntes Datum')
        
        return f"Rechnung von {supplier} über {amount} EUR vom {date}"
    
    def is_confident(self, data: dict) -> bool:
        """Prüft, ob die KI sich sicher ist"""
        filled_fields = sum(1 for value in data.values() if value)
        confidence = filled_fields / len(data)
        return confidence > 0.6  # 60% der Felder gefüllt = sicher
    
    def get_confidence_score(self, data: dict) -> float:
        """Gibt Confidence-Score zurück (0-100%)"""
        filled_fields = sum(1 for value in data.values() if value and value != '')
        return (filled_fields / len(data)) * 100

# Einfache Verwendung:
if __name__ == "__main__":
    ai = SimpleInvoiceAI()
    
    # Test mit Beispieltext
    test_text = """
    Rechnung von: Müller GmbH
    Rechnungsnummer: R-2024-001
    Datum: 15.10.2024
    Gesamtbetrag: 125,50 €
    """
    
    result = ai.extract_data(test_text)
    confidence = ai.get_confidence_score(result)
    
    print(f"Ergebnis: {result}")
    print(f"Vertrauen: {confidence:.1f}%")
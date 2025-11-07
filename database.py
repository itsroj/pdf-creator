"""
Einfache Datenbank - Speichert Rechnungen in JSON
"""

import json
import os
from datetime import datetime

class SimpleDatabase:
    def __init__(self, filename='invoices.json'):
        self.filename = filename
        self.invoices = self.load_data()
    
    def load_data(self):
        """Lädt Daten aus JSON-Datei"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_data(self):
        """Speichert Daten in JSON-Datei"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.invoices, f, ensure_ascii=False, indent=2)
    
    def add_invoice(self, invoice_data):
        """Fügt neue Rechnung hinzu"""
        invoice_data['id'] = len(self.invoices) + 1
        invoice_data['created_at'] = datetime.now().isoformat()
        self.invoices.append(invoice_data)
        self.save_data()
        return invoice_data
    
    def get_all_invoices(self):
        """Gibt alle Rechnungen zurück"""
        return self.invoices
    
    def get_stats(self):
        """Gibt Statistiken zurück"""
        return {
            'total': len(self.invoices),
            'eingang': len([inv for inv in self.invoices if inv.get('type') == 'Eingangsrechnung']),
            'ausgang': len([inv for inv in self.invoices if inv.get('type') == 'Ausgangsrechnung'])
        }
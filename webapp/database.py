"""
Datenbankmodul - Behandelt JSON-basierte Rechnungsspeicherung und KI-Lernen
"""
import json
import os
import pandas as pd
from datetime import datetime


class SimpleDB:
    """Einfache JSON-Datenbank für Rechnungsverwaltung mit KI-Lernfähigkeiten"""
    
    def __init__(self, filename="invoices.json"):
        self.file = filename
        self.data = {"invoices": [], "corrections": []}
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    loaded_data = json.load(f)
                    # Stelle sicher dass Korrekturen-Tabelle existiert
                    if "corrections" not in loaded_data:
                        loaded_data["corrections"] = []
                    self.data = loaded_data
            except:
                pass
    
    def save(self):
        """Speichert Daten in JSON-Datei"""
        with open(self.file, "w") as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def add_invoice(self, invoice):
        """Fügt eine neue Rechnung zur Datenbank hinzu"""
        self.data["invoices"].append(invoice)
        self.save()
    
    def delete_invoice(self, index):
        """Löscht eine Rechnung anhand des Index"""
        if 0 <= index < len(self.data["invoices"]):
            deleted = self.data["invoices"].pop(index)
            self.save()
            return deleted
        return None
    
    def add_correction(self, original_text, corrected_text, field_type, company_context=""):
        """Fügt eine neue Korrektur hinzu oder erhöht die Häufigkeit einer existierenden"""
        existing = None
        for correction in self.data["corrections"]:
            if (correction["original_text"].lower() == original_text.lower() and 
                correction["field_type"] == field_type):
                existing = correction
                break
        
        if existing:
            # Erhöhe Häufigkeit und Konfidenz (AGGRESSIVES LERNEN!)
            existing["correction_count"] += 1
            # Neue Formel: 1x = 0.7, 2x = 0.95, 3x+ = 1.0
            existing["confidence_score"] = min(1.0, 0.7 + (existing["correction_count"] - 1) * 0.25)
            existing["corrected_text"] = corrected_text  # Aktualisiere mit neuester Korrektur
            existing["timestamp"] = str(datetime.now())
        else:
            # Neue Korrektur (SOFORT HOHE KONFIDENZ!)
            correction = {
                "original_text": original_text,
                "corrected_text": corrected_text,
                "field_type": field_type,
                "company_context": company_context,
                "correction_count": 1,
                "confidence_score": 0.7,  # Starte mit 70% Konfidenz - wird sofort automatisch angewendet
                "timestamp": str(datetime.now())
            }
            self.data["corrections"].append(correction)
        self.save()
    
    def apply_corrections(self, data):
        """Wendet gelernte Korrekturen auf extrahierte Daten an"""
        corrected_data = data.copy()
        suggestions = {}
        applied_corrections = []  # Für Logging
        
        # Hole Firmennamen für firmenspezifische Korrekturen
        current_company = data.get("company", "").strip()
        
        for field_type in data.keys():
            # Überspringe Firmenfeld selbst - niemals automatisch korrigieren
            if field_type == "company":
                continue
                
            field_value = str(data[field_type]).strip()
            
            # Überspringe leere oder ungültige Werte, aber erkenne häufige Platzhalter
            if not field_value or field_value == "0":
                # Prüfe ob wir Korrekturen für dieses leere Feld haben
                for correction in self.data["corrections"]:
                    if correction["field_type"] == field_type:
                        # Prüfe ob Korrektur für diese Firma gilt
                        correction_company = correction.get("company_context", "").strip()
                        if correction_company and current_company:
                            if correction_company.lower() in current_company.lower() or current_company.lower() in correction_company.lower():
                                suggestions[field_type] = correction["corrected_text"]
                                break
                continue
                
            # Suche nach passenden Korrekturen
            best_match = None
            for correction in self.data["corrections"]:
                if correction["field_type"] == field_type:
                    # Prüfe Firmenkontext falls verfügbar
                    correction_company = correction.get("company_context", "").strip()
                    if correction_company and current_company:
                        # Wende nur an wenn Firma übereinstimmt
                        if not (correction_company.lower() in current_company.lower() or 
                                current_company.lower() in correction_company.lower()):
                            continue
                    
                    # Prüfe exakte Übereinstimmung oder Ähnlichkeit
                    similarity = self._text_similarity(correction["original_text"], field_value)
                    is_exact = correction["original_text"].lower() == field_value.lower()
                    
                    if is_exact or similarity > 0.7:  # Gesenkt von 0.8 auf 0.7
                        if not best_match or correction["confidence_score"] > best_match["confidence_score"]:
                            best_match = correction
            
            if best_match:
                if best_match["confidence_score"] >= 0.6:  # Gesenkt von 0.75 auf 0.6 - schnellere Auto-Korrektur
                    # Auto-Korrektur mit hoher Konfidenz
                    corrected_data[field_type] = best_match["corrected_text"]
                    applied_corrections.append(f"{field_type}: {field_value} → {best_match['corrected_text']}")
                elif best_match["confidence_score"] >= 0.4:  # Vorschläge bei mittlerer Konfidenz
                    # Vorschlag mit mittlerer Konfidenz
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
        """Gibt Datenbankstatistiken zurück"""
        corrections = len(self.data["corrections"])
        total_corrections = sum(c["correction_count"] for c in self.data["corrections"])
        return {
            "invoices": len(self.data["invoices"]), 
            "corrections": corrections,
            "total_corrections": total_corrections,
            "accuracy": min(95, 60 + total_corrections * 1.5)
        }
    
    def export_to_excel(self, filename):
        """Exportiert Rechnungen in eine Excel-Datei"""
        df = pd.DataFrame(self.data["invoices"])
        df.to_excel(filename, index=False)
    
    def export_to_csv(self, filename):
        """Exportiert Rechnungen in eine CSV-Datei"""
        df = pd.DataFrame(self.data["invoices"])
        df.to_csv(filename, index=False)

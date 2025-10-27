"""
Excel Exporter - Export der klassifizierten Daten

Dieses Modul ist zuständig für:
- Export der verarbeiteten Rechnungsdaten nach Excel
- Strukturierte Datenaufbereitung
- Formatierung der Excel-Dateien
"""

import pandas as pd
from datetime import datetime
import os

class ExcelExporter:
    """
    Klasse für den Export von Rechnungsdaten nach Excel
    """
    
    def __init__(self):
        """
        Initialisiert den Excel Exporter
        """
        self.data = []
        
    def add_invoice_data(self, invoice_data):
        """
        Fügt Rechnungsdaten zur Export-Liste hinzu
        
        Args:
            invoice_data (dict): Dictionary mit Rechnungsdaten
        """
        # Standard-Struktur für Rechnungsdaten
        standardized_data = {
            'Datum': invoice_data.get('date', ''),
            'Rechnungstyp': invoice_data.get('type', ''),  # 'incoming' oder 'outgoing'
            'Rechnungsnummer': invoice_data.get('invoice_number', ''),
            'Lieferant/Kunde': invoice_data.get('vendor_customer', ''),
            'Betrag': invoice_data.get('amount', 0.0),
            'Währung': invoice_data.get('currency', 'EUR'),
            'Beschreibung': invoice_data.get('description', ''),
            'Verarbeitungsdatum': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Konfidenz': invoice_data.get('confidence', 0.0)
        }
        
        self.data.append(standardized_data)
    
    def export_to_excel(self, filename='rechnungen_export.xlsx', output_dir='data/processed'):
        """
        Exportiert alle gesammelten Daten nach Excel
        
        Args:
            filename (str): Name der Excel-Datei
            output_dir (str): Ausgabeverzeichnis
            
        Returns:
            str: Pfad zur erstellten Excel-Datei
        """
        if not self.data:
            print("Keine Daten zum Export verfügbar.")
            return None
            
        # Sicherstellen, dass das Ausgabeverzeichnis existiert
        os.makedirs(output_dir, exist_ok=True)
        
        # DataFrame erstellen
        df = pd.DataFrame(self.data)
        
        # Vollständiger Dateipfad
        filepath = os.path.join(output_dir, filename)
        
        try:
            # Excel-Export mit Formatierung
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Hauptdaten
                df.to_excel(writer, sheet_name='Rechnungen', index=False)
                
                # Zusammenfassung
                summary_data = self._create_summary(df)
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Zusammenfassung', index=False)
                
                # Arbeitsblätter formatieren
                self._format_worksheets(writer, df)
            
            print(f"Excel-Export erfolgreich: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Fehler beim Excel-Export: {e}")
            return None
    
    def _create_summary(self, df):
        """
        Erstellt eine Zusammenfassung der Daten
        
        Args:
            df (DataFrame): Hauptdaten
            
        Returns:
            list: Zusammenfassungsdaten
        """
        summary = []
        
        # Anzahl Rechnungen nach Typ
        type_counts = df['Rechnungstyp'].value_counts()
        for rech_type, count in type_counts.items():
            summary.append({
                'Kategorie': f'Anzahl {rech_type}',
                'Wert': count
            })
        
        # Gesamtsummen
        total_amount = df['Betrag'].sum()
        summary.append({
            'Kategorie': 'Gesamtsumme',
            'Wert': f"{total_amount:.2f} EUR"
        })
        
        # Durchschnittliche Konfidenz
        avg_confidence = df['Konfidenz'].mean()
        summary.append({
            'Kategorie': 'Durchschnittliche Konfidenz',
            'Wert': f"{avg_confidence:.2f}"
        })
        
        return summary
    
    def _format_worksheets(self, writer, df):
        """
        Formatiert die Excel-Arbeitsblätter
        
        Args:
            writer: Excel Writer Objekt
            df (DataFrame): Hauptdaten
        """
        workbook = writer.book
        
        # Hauptarbeitsblatt formatieren
        worksheet = writer.sheets['Rechnungen']
        
        # Spaltenbreiten anpassen
        for column in df.columns:
            column_length = max(df[column].astype(str).map(len).max(), len(column))
            col_letter = chr(65 + df.columns.get_loc(column))
            worksheet.column_dimensions[col_letter].width = min(column_length + 2, 50)
    
    def clear_data(self):
        """
        Löscht alle gesammelten Daten
        """
        self.data = []
    
    def get_data_count(self):
        """
        Gibt die Anzahl der gesammelten Datensätze zurück
        
        Returns:
            int: Anzahl Datensätze
        """
        return len(self.data)
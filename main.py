"""
PDF-Creator - Main Application Entry Point
KI-basierte Rechnungserfassung

Dieses Modul stellt den Haupteinstiegspunkt für die Anwendung dar.
"""

from src.ocr.pdf_processor import PDFProcessor
from src.classifier.invoice_classifier import InvoiceClassifier
from src.export.excel_exporter import ExcelExporter

def main():
    """
    Hauptfunktion der Anwendung
    """
    print("PDF-Creator - KI-basierte Rechnungserfassung")
    print("=" * 50)
    
    # TODO: Implementierung der Hauptlogik
    # 1. PDF einlesen
    # 2. OCR anwenden
    # 3. KI-Klassifizierung
    # 4. Excel-Export
    
    pass

if __name__ == "__main__":
    main()
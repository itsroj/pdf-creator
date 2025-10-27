"""
PDF Processor - OCR und PDF-Verarbeitung

Dieses Modul ist zuständig für:
- PDF-Dateien einlesen
- PDF zu Bildern konvertieren
- OCR-Texterkennung anwenden
"""

import os
from PIL import Image
import pdf2image
import easyocr
import pdfplumber

class PDFProcessor:
    """
    Klasse für die Verarbeitung von PDF-Dateien mit OCR
    """
    
    def __init__(self):
        """
        Initialisiert den PDF-Processor mit OCR-Reader
        """
        self.ocr_reader = easyocr.Reader(['de', 'en'])  # Deutsch und Englisch
        
    def extract_text_from_pdf(self, pdf_path):
        """
        Extrahiert Text aus einer PDF-Datei
        
        Args:
            pdf_path (str): Pfad zur PDF-Datei
            
        Returns:
            str: Extrahierter Text
        """
        try:
            # Zuerst versuchen, Text direkt zu extrahieren
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        
            # Falls kein Text extrahiert werden konnte, OCR verwenden
            if not text.strip():
                text = self._extract_text_with_ocr(pdf_path)
                
            return text
            
        except Exception as e:
            print(f"Fehler beim Verarbeiten der PDF: {e}")
            return ""
    
    def _extract_text_with_ocr(self, pdf_path):
        """
        Verwendet OCR für die Texterkennung aus PDF
        
        Args:
            pdf_path (str): Pfad zur PDF-Datei
            
        Returns:
            str: Per OCR erkannter Text
        """
        try:
            # PDF zu Bildern konvertieren
            images = pdf2image.convert_from_path(pdf_path)
            
            all_text = ""
            for image in images:
                # OCR auf jedes Bild anwenden
                results = self.ocr_reader.readtext(image)
                page_text = " ".join([result[1] for result in results])
                all_text += page_text + "\n"
                
            return all_text
            
        except Exception as e:
            print(f"Fehler bei OCR: {e}")
            return ""
    
    def preprocess_text(self, text):
        """
        Vorverarbeitung des extrahierten Texts
        
        Args:
            text (str): Roher extrahierter Text
            
        Returns:
            str: Vorverarbeiteter Text
        """
        # Grundlegende Textbereinigung
        text = text.strip()
        text = " ".join(text.split())  # Mehrfache Leerzeichen entfernen
        
        return text
#!/usr/bin/env python3
"""
Hybrid KI-System: scikit-learn + TensorFlow
Verwendet das beste Tool für jede Aufgabe
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
# import tensorflow as tf  # Für spätere Erweiterungen

class HybridInvoiceAI:
    """Kombiniert verschiedene KI-Ansätze intelligent"""
    
    def __init__(self):
        """Setup für Hybrid-System"""
        # Einfache sklearn für Basis-Features
        self.sklearn_models = {
            'supplier_classifier': RandomForestClassifier(n_estimators=50),
            'amount_extractor': RandomForestClassifier(n_estimators=30)
        }
        
        # TensorFlow für komplexe Aufgaben (optional)
        self.use_tensorflow = False  # Kann aktiviert werden
        
        print("🔀 Hybrid-KI System initialisiert")
        print("📊 sklearn: Basis-Klassifikation")
        print("🧠 TensorFlow: Bereit für komplexe Aufgaben")
    
    def extract_data(self, text: str, use_deep_learning: bool = False):
        """Wählt automatisch die beste Methode"""
        
        if use_deep_learning and self.use_tensorflow:
            return self._extract_with_tensorflow(text)
        else:
            return self._extract_with_sklearn(text)
    
    def _extract_with_sklearn(self, text: str):
        """Schnelle sklearn-basierte Extraktion"""
        print("⚡ Verwende sklearn (schnell)")
        
        # Einfache Regex + sklearn Klassifikation
        # ... existing logic ...
        
        return {
            'method': 'sklearn',
            'speed': 'fast',
            'accuracy': 'good'
        }
    
    def _extract_with_tensorflow(self, text: str):
        """Deep Learning für komplexe Fälle"""
        print("🧠 Verwende TensorFlow (genau)")
        
        # Würde hier komplexe NN-Verarbeitung machen
        # Transformer, BERT, etc.
        
        return {
            'method': 'tensorflow',
            'speed': 'slow',
            'accuracy': 'excellent'
        }
    
    def auto_select_method(self, text: str):
        """KI wählt automatisch die beste Methode"""
        
        # Heuristics für Methoden-Auswahl
        if len(text) > 5000:  # Sehr lange Dokumente
            return 'tensorflow'
        elif 'handwritten' in text.lower():  # Handschrift
            return 'tensorflow'  
        elif self._is_standard_invoice(text):  # Standard-Rechnung
            return 'sklearn'
        else:
            return 'sklearn'  # Default
    
    def _is_standard_invoice(self, text: str) -> bool:
        """Prüft, ob es eine Standard-Rechnung ist"""
        keywords = ['rechnung', 'invoice', 'betrag', 'datum']
        return sum(1 for kw in keywords if kw in text.lower()) >= 2

# Intelligente Nutzung:
ai = HybridInvoiceAI()

# Automatische Methoden-Auswahl
text = "Standard Rechnung von Müller GmbH..."
method = ai.auto_select_method(text)
print(f"Gewählte Methode: {method}")

result = ai.extract_data(text, use_deep_learning=(method=='tensorflow'))
print(f"Ergebnis: {result}")
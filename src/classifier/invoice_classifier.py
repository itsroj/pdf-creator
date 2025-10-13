"""
Invoice Classifier - KI-basierte Rechnungsklassifizierung

Dieses Modul ist zuständig für:
- Klassifizierung von Eingangs- vs. Ausgangsrechnungen
- Extraktion relevanter Daten (Betrag, Datum, Lieferant)
- Machine Learning Modell Training
"""

import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
import pickle
import os

class InvoiceClassifier:
    """
    Klasse für die KI-basierte Klassifizierung von Rechnungen
    """
    
    def __init__(self):
        """
        Initialisiert den Classifier
        """
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.classifier = LogisticRegression()
        self.is_trained = False
        
    def extract_features(self, text):
        """
        Extrahiert Features aus dem Rechnungstext
        
        Args:
            text (str): Text der Rechnung
            
        Returns:
            dict: Dictionary mit extrahierten Features
        """
        features = {}
        
        # Betrag extrahieren (Euro-Beträge)
        amount_pattern = r'(\d+[.,]\d{2})\s*€?'
        amounts = re.findall(amount_pattern, text)
        features['total_amount'] = max([float(a.replace(',', '.')) for a in amounts]) if amounts else 0
        
        # Datum extrahieren
        date_pattern = r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})'
        dates = re.findall(date_pattern, text)
        features['has_date'] = len(dates) > 0
        
        # Rechnungsnummer
        invoice_pattern = r'(Rechnung|Invoice|Rechnungs-?Nr|Invoice No)[:\s]*([A-Z0-9-]+)'
        features['has_invoice_number'] = bool(re.search(invoice_pattern, text, re.IGNORECASE))
        
        # Schlüsselwörter für Eingangs- vs. Ausgangsrechnungen
        incoming_keywords = ['Zahlung', 'Überweisung', 'Rechnung erhalten', 'Lieferant']
        outgoing_keywords = ['Rechnung', 'Invoice', 'Betrag zu zahlen', 'Kundennummer']
        
        features['incoming_score'] = sum(1 for kw in incoming_keywords if kw.lower() in text.lower())
        features['outgoing_score'] = sum(1 for kw in outgoing_keywords if kw.lower() in text.lower())
        
        return features
    
    def classify_invoice_type(self, text):
        """
        Klassifiziert eine Rechnung als Eingangs- oder Ausgangsrechnung
        
        Args:
            text (str): Text der Rechnung
            
        Returns:
            tuple: (classification, confidence)
        """
        if not self.is_trained:
            # Fallback-Klassifizierung basierend auf Schlüsselwörtern
            features = self.extract_features(text)
            if features['incoming_score'] > features['outgoing_score']:
                return ('incoming', 0.6)
            else:
                return ('outgoing', 0.6)
        
        # TODO: Implementierung mit trainiertem ML-Modell
        return ('outgoing', 0.8)
    
    def train_model(self, training_data):
        """
        Trainiert das Klassifizierungsmodell
        
        Args:
            training_data (list): Liste von (text, label) Tupeln
        """
        if not training_data:
            print("Keine Trainingsdaten verfügbar.")
            return
            
        texts, labels = zip(*training_data)
        
        # Text-Vektorisierung
        X = self.vectorizer.fit_transform(texts)
        
        # Modell trainieren
        X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2)
        self.classifier.fit(X_train, y_train)
        
        self.is_trained = True
        print(f"Modell trainiert. Genauigkeit: {self.classifier.score(X_test, y_test):.2f}")
    
    def save_model(self, model_path):
        """
        Speichert das trainierte Modell
        """
        if self.is_trained:
            with open(model_path, 'wb') as f:
                pickle.dump((self.vectorizer, self.classifier), f)
    
    def load_model(self, model_path):
        """
        Lädt ein gespeichertes Modell
        """
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                self.vectorizer, self.classifier = pickle.load(f)
                self.is_trained = True
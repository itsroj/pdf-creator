#!/usr/bin/env python3
"""
KI-Trainingsmodul für PDF Rechnungsverarbeitung
Ermöglicht das Training eines Machine Learning Modells mit manuell korrigierten Daten
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import json
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class InvoiceTrainer:
    """KI-Trainer für Rechnungsklassifikation"""
    
    def __init__(self):
        """Initialisiert den Trainer"""
        self.models = {}
        self.vectorizers = {}
        self.training_data = []
        self.model_path = 'models'
        os.makedirs(self.model_path, exist_ok=True)
        logger.info("🤖 KI-Trainer initialisiert")
    
    def add_training_data(self, raw_text: str, corrected_data: dict, filename: str = ""):
        """Fügt Trainingsdaten hinzu"""
        training_entry = {
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'raw_text': raw_text,
            'corrected_data': corrected_data,
            'text_features': self._extract_text_features(raw_text)
        }
        
        self.training_data.append(training_entry)
        logger.info(f"📚 Trainingsdaten hinzugefügt: {filename}")
        
        # Speichere Trainingsdaten
        self._save_training_data()
    
    def _extract_text_features(self, text: str) -> dict:
        """Extrahiert Features aus dem Text"""
        features = {
            'text_length': len(text),
            'word_count': len(text.split()),
            'line_count': len(text.split('\n')),
            'has_euro_symbol': '€' in text,
            'has_invoice_keywords': any(keyword in text.lower() for keyword in 
                                      ['rechnung', 'invoice', 'beleg', 'quittung']),
            'has_date_pattern': bool(re.search(r'\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}', text)),
            'has_amount_pattern': bool(re.search(r'\d+[,\.]\d{2}', text)),
            'has_company_indicators': any(keyword in text for keyword in 
                                        ['GmbH', 'AG', 'Ltd', 'Inc', 'UG']),
            'numeric_density': len(re.findall(r'\d', text)) / len(text) if text else 0
        }
        return features
    
    def train_supplier_classifier(self):
        """Trainiert einen Klassifikator für Lieferanten"""
        if len(self.training_data) < 5:
            logger.warning("⚠️ Zu wenig Trainingsdaten (mindestens 5 benötigt)")
            return False
        
        # Daten vorbereiten
        texts = [entry['raw_text'] for entry in self.training_data]
        suppliers = [entry['corrected_data'].get('supplier', 'Unbekannt') for entry in self.training_data]
        
        # Text-Vektorisierung
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        X_text = vectorizer.fit_transform(texts)
        
        # Features kombinieren
        feature_arrays = []
        for entry in self.training_data:
            features = entry['text_features']
            feature_array = [
                features['text_length'],
                features['word_count'],
                features['line_count'],
                int(features['has_euro_symbol']),
                int(features['has_invoice_keywords']),
                int(features['has_date_pattern']),
                int(features['has_amount_pattern']),
                int(features['has_company_indicators']),
                features['numeric_density']
            ]
            feature_arrays.append(feature_array)
        
        X_features = np.array(feature_arrays)
        
        # Kombiniere Text- und numerische Features
        from scipy.sparse import hstack
        X_combined = hstack([X_text, X_features])
        
        # Train-Test Split
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, suppliers, test_size=0.2, random_state=42
        )
        
        # Modell trainieren
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluierung
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"✅ Lieferanten-Klassifikator trainiert: {accuracy:.2%} Genauigkeit")
        
        # Modell speichern
        self.models['supplier'] = model
        self.vectorizers['supplier'] = vectorizer
        
        joblib.dump(model, os.path.join(self.model_path, 'supplier_model.pkl'))
        joblib.dump(vectorizer, os.path.join(self.model_path, 'supplier_vectorizer.pkl'))
        
        return True
    
    def train_amount_extractor(self):
        """Trainiert einen Betrag-Extraktor"""
        if len(self.training_data) < 5:
            logger.warning("⚠️ Zu wenig Trainingsdaten (mindestens 5 benötigt)")
            return False
        
        # Daten für Betragserkennung vorbereiten
        training_patterns = []
        for entry in self.training_data:
            text = entry['raw_text']
            correct_amount = entry['corrected_data'].get('amount', '0.00')
            
            # Finde alle Beträge im Text
            amount_patterns = re.findall(r'\d+[,\.]\d{2}', text)
            
            for pattern in amount_patterns:
                training_patterns.append({
                    'pattern': pattern,
                    'context': self._get_amount_context(text, pattern),
                    'is_total': pattern.replace(',', '.') == correct_amount.replace(',', '.'),
                    'position_ratio': text.find(pattern) / len(text) if text else 0
                })
        
        if not training_patterns:
            logger.warning("⚠️ Keine Betragspatterns zum Trainieren gefunden")
            return False
        
        # Features für Betragserkennung
        X = []
        y = []
        
        for pattern_data in training_patterns:
            features = [
                len(pattern_data['pattern']),
                pattern_data['position_ratio'],
                int('total' in pattern_data['context'].lower()),
                int('gesamt' in pattern_data['context'].lower()),
                int('summe' in pattern_data['context'].lower()),
                int('betrag' in pattern_data['context'].lower()),
                int('€' in pattern_data['context']),
                int(pattern_data['position_ratio'] > 0.7)  # Späte Position im Dokument
            ]
            X.append(features)
            y.append(pattern_data['is_total'])
        
        # Training
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = LogisticRegression(random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluierung
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"✅ Betrag-Extraktor trainiert: {accuracy:.2%} Genauigkeit")
        
        # Modell speichern
        self.models['amount'] = model
        joblib.dump(model, os.path.join(self.model_path, 'amount_model.pkl'))
        
        return True
    
    def _get_amount_context(self, text: str, amount: str, context_size: int = 50) -> str:
        """Holt den Kontext um einen Betrag"""
        pos = text.find(amount)
        if pos == -1:
            return ""
        
        start = max(0, pos - context_size)
        end = min(len(text), pos + len(amount) + context_size)
        
        return text[start:end]
    
    def predict_supplier(self, text: str) -> str:
        """Vorhersage des Lieferanten"""
        if 'supplier' not in self.models:
            return "Modell nicht trainiert"
        
        vectorizer = self.vectorizers['supplier']
        model = self.models['supplier']
        
        # Text vektorisieren
        X_text = vectorizer.transform([text])
        
        # Features extrahieren
        features = self._extract_text_features(text)
        feature_array = np.array([[
            features['text_length'],
            features['word_count'],
            features['line_count'],
            int(features['has_euro_symbol']),
            int(features['has_invoice_keywords']),
            int(features['has_date_pattern']),
            int(features['has_amount_pattern']),
            int(features['has_company_indicators']),
            features['numeric_density']
        ]])
        
        # Kombiniere Features
        from scipy.sparse import hstack
        X_combined = hstack([X_text, feature_array])
        
        # Vorhersage
        prediction = model.predict(X_combined)[0]
        confidence = max(model.predict_proba(X_combined)[0])
        
        logger.info(f"🎯 Lieferanten-Vorhersage: {prediction} (Konfidenz: {confidence:.2%})")
        return prediction
    
    def get_training_statistics(self) -> dict:
        """Gibt Trainingsstatistiken zurück"""
        if not self.training_data:
            return {"total_samples": 0, "message": "Keine Trainingsdaten vorhanden"}
        
        suppliers = [entry['corrected_data'].get('supplier', 'Unbekannt') 
                    for entry in self.training_data]
        
        stats = {
            "total_samples": len(self.training_data),
            "unique_suppliers": len(set(suppliers)),
            "most_common_suppliers": pd.Series(suppliers).value_counts().head().to_dict(),
            "latest_training": self.training_data[-1]['timestamp'] if self.training_data else None,
            "models_trained": list(self.models.keys())
        }
        
        return stats
    
    def _save_training_data(self):
        """Speichert Trainingsdaten in JSON"""
        with open(os.path.join(self.model_path, 'training_data.json'), 'w', encoding='utf-8') as f:
            json.dump(self.training_data, f, ensure_ascii=False, indent=2)
        logger.info("💾 Trainingsdaten gespeichert")
    
    def load_training_data(self):
        """Lädt gespeicherte Trainingsdaten"""
        training_file = os.path.join(self.model_path, 'training_data.json')
        if os.path.exists(training_file):
            with open(training_file, 'r', encoding='utf-8') as f:
                self.training_data = json.load(f)
            logger.info(f"📖 {len(self.training_data)} Trainingsdaten geladen")
        
        # Lade gespeicherte Modelle
        supplier_model_path = os.path.join(self.model_path, 'supplier_model.pkl')
        supplier_vectorizer_path = os.path.join(self.model_path, 'supplier_vectorizer.pkl')
        
        if os.path.exists(supplier_model_path) and os.path.exists(supplier_vectorizer_path):
            self.models['supplier'] = joblib.load(supplier_model_path)
            self.vectorizers['supplier'] = joblib.load(supplier_vectorizer_path)
            logger.info("🤖 Lieferanten-Modell geladen")
        
        amount_model_path = os.path.join(self.model_path, 'amount_model.pkl')
        if os.path.exists(amount_model_path):
            self.models['amount'] = joblib.load(amount_model_path)
            logger.info("💰 Betrag-Modell geladen")
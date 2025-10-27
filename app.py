#!/usr/bin/env python3
"""
PDF Rechnungsverarbeitung - Saubere Neuimplementierung
Ein einfaches, übersichtliches System zur Verarbeitung von PDF-Rechnungen
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
import tempfile
from pdf_processor import PDFProcessor
from ai_trainer import InvoiceTrainer

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App konfigurieren
app = Flask(__name__)
app.config['SECRET_KEY'] = 'invoice-processor-2025'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# PDF Processor und KI-Trainer initialisieren
pdf_processor = PDFProcessor()
ai_trainer = InvoiceTrainer()
ai_trainer.load_training_data()

# Erlaubte Dateierweiterungen
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Prüft ob die Datei erlaubt ist"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Hauptseite"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Datei-Upload Handler"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            
            # Sicherstellen dass uploads Ordner existiert
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            logger.info(f"Datei hochgeladen: {filename}")
            
            # PDF verarbeiten
            result = process_pdf(filepath)
            
            # Ergebnis speichern für Export
            processed_data.append(result)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'data': result
            })
        
        return jsonify({'error': 'Nur PDF-Dateien sind erlaubt'}), 400
        
    except Exception as e:
        logger.error(f"Upload-Fehler: {str(e)}")
        return jsonify({'error': f'Upload-Fehler: {str(e)}'}), 500

def process_pdf(filepath):
    """Verarbeitet eine PDF-Datei und extrahiert Rechnungsdaten"""
    try:
        logger.info(f"Verarbeite PDF: {filepath}")
        # Verwende den PDF-Processor
        result = pdf_processor.process_pdf(filepath)
        return result
    except Exception as e:
        logger.error(f"PDF-Verarbeitungsfehler: {str(e)}")
        return {
            'filename': os.path.basename(filepath),
            'status': 'error',
            'error': str(e)
        }

# Globale Variable für Daten-Storage (in Produktion: Datenbank verwenden)
processed_data = []

@app.route('/export/<format_type>')
def export_data(format_type):
    """Exportiert Daten als Excel oder CSV"""
    try:
        # Verwende gespeicherte Daten oder Beispieldaten
        if not processed_data:
            data = [{
                'Lieferant': 'Beispiel Lieferant',
                'Rechnungsnummer': '2025-001',
                'Datum': '2025-10-27',
                'Betrag': '123.45',
                'Währung': 'EUR',
                'Beschreibung': 'Beispiel Rechnung'
            }]
        else:
            data = []
            for item in processed_data:
                if 'extracted_data' in item:
                    ed = item['extracted_data']
                    data.append({
                        'Dateiname': item.get('filename', ''),
                        'Lieferant': ed.get('supplier', ''),
                        'Rechnungsnummer': ed.get('invoice_number', ''),
                        'Datum': ed.get('date', ''),
                        'Betrag': ed.get('amount', ''),
                        'Währung': ed.get('currency', ''),
                        'Beschreibung': ed.get('description', '')
                    })
        
        df = pd.DataFrame(data)
        
        # Temporäre Datei erstellen
        if format_type.lower() == 'excel':
            # Excel-Export mit expliziter Engine
            filename = f'rechnungen_{datetime.now().strftime("%Y%m%d")}.xlsx'
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            df.to_excel(temp_path, index=False, engine='openpyxl')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype=mimetype
            )
        else:  # CSV
            filename = f'rechnungen_{datetime.now().strftime("%Y%m%d")}.csv'
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            df.to_csv(temp_path, index=False, encoding='utf-8')
            mimetype = 'text/csv'
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype=mimetype
            )
            
    except Exception as e:
        logger.error(f"Export-Fehler: {str(e)}")
        return jsonify({'error': f'Export-Fehler: {str(e)}'}), 500

@app.route('/export/batch', methods=['POST'])
def export_batch_data():
    """Exportiert Batch-verarbeitete Daten"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'Keine Daten empfangen'}), 400
        
        format_type = request_data.get('format', 'excel')
        batch_data = request_data.get('data', [])
        
        if not batch_data:
            return jsonify({'error': 'Keine Batch-Daten vorhanden'}), 400
        
        # DataFrame aus Batch-Daten erstellen
        data = []
        for item in batch_data:
            data.append({
                'Dateiname': item.get('filename', ''),
                'Verarbeitungszeit': item.get('timestamp', ''),
                'Lieferant': item.get('supplier', ''),
                'Rechnungsnummer': item.get('invoice_number', ''),
                'Datum': item.get('date', ''),
                'Betrag': item.get('amount', ''),
                'Währung': item.get('currency', ''),
                'Beschreibung': item.get('description', '')
            })
        
        df = pd.DataFrame(data)
        
        # Temporäre Datei erstellen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if format_type.lower() == 'excel':
            filename = f'batch_export_{len(batch_data)}_files_{timestamp}.xlsx'
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            df.to_excel(temp_path, index=False, engine='openpyxl')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:  # CSV
            filename = f'batch_export_{len(batch_data)}_files_{timestamp}.csv'
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            df.to_csv(temp_path, index=False, encoding='utf-8')
            mimetype = 'text/csv'
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
            
    except Exception as e:
        logger.error(f"Batch-Export-Fehler: {str(e)}")
        return jsonify({'error': f'Batch-Export-Fehler: {str(e)}'}), 500

@app.route('/training')
def training_dashboard():
    """KI-Training Dashboard"""
    return render_template('training.html')

@app.route('/api/training/stats')
def training_stats():
    """Gibt Trainingsstatistiken zurück"""
    try:
        stats = ai_trainer.get_training_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/training/add', methods=['POST'])
def add_training_data():
    """Fügt korrigierte Daten zum Training hinzu"""
    try:
        data = request.json
        
        raw_text = data.get('raw_text', '')
        corrected_data = data.get('corrected_data', {})
        filename = data.get('filename', '')
        
        ai_trainer.add_training_data(raw_text, corrected_data, filename)
        
        return jsonify({'success': True, 'message': 'Trainingsdaten hinzugefügt'})
        
    except Exception as e:
        logger.error(f"Training-Fehler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/training/train_models', methods=['POST'])
def train_models():
    """Startet das KI-Training"""
    try:
        results = {}
        
        # Lieferanten-Klassifikator trainieren
        supplier_success = ai_trainer.train_supplier_classifier()
        results['supplier'] = {
            'success': supplier_success,
            'message': 'Lieferanten-Modell trainiert' if supplier_success else 'Training fehlgeschlagen'
        }
        
        # Betrag-Extraktor trainieren
        amount_success = ai_trainer.train_amount_extractor()
        results['amount'] = {
            'success': amount_success,
            'message': 'Betrag-Modell trainiert' if amount_success else 'Training fehlgeschlagen'
        }
        
        return jsonify({
            'success': supplier_success or amount_success,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Training-Fehler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/training/predict', methods=['POST'])
def ai_predict():
    """Nutzt trainierte KI für Vorhersagen"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Kein Text angegeben'}), 400
        
        predictions = {}
        
        # Lieferanten-Vorhersage
        if 'supplier' in ai_trainer.models:
            supplier_prediction = ai_trainer.predict_supplier(text)
            predictions['supplier'] = supplier_prediction
        
        return jsonify({
            'success': True,
            'predictions': predictions
        })
        
    except Exception as e:
        logger.error(f"Vorhersage-Fehler: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starte PDF Rechnungsverarbeitung...")
    print("📊 Neues, sauberes System gestartet")
    print("🔗 Verfügbar unter: http://127.0.0.1:5003")
    print("💡 Features: PDF Upload • Datenextraktion • Excel/CSV Export • Multi-PDF Batch Processing")
    
    # Uploads-Ordner erstellen falls nicht vorhanden
    os.makedirs('uploads', exist_ok=True)
    
    app.run(debug=False, host='127.0.0.1', port=5003)
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

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App konfigurieren
app = Flask(__name__)
app.config['SECRET_KEY'] = 'invoice-processor-2025'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# PDF Processor initialisieren
pdf_processor = PDFProcessor()

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

if __name__ == '__main__':
    print("🚀 Starte PDF Rechnungsverarbeitung...")
    print("📊 Neues, sauberes System gestartet")
    print("🔗 Verfügbar unter: http://127.0.0.1:5002")
    print("💡 Features: PDF Upload • Datenextraktion • Excel/CSV Export")
    
    # Uploads-Ordner erstellen falls nicht vorhanden
    os.makedirs('uploads', exist_ok=True)
    
    app.run(debug=False, host='127.0.0.1', port=5002)
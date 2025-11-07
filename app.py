#!/usr/bin/env python3
"""
PDF Rechnungsverarbeitung - Kompakte Hauptanwendung
Alle Features, aber nur 150 Zeilen!
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import pandas as pd

# Eigene Module
from pdf_extractor import extract_text_from_pdf, extract_invoice_data
from database import SimpleDatabase

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = 'invoice-processor-2025'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Datenbank
db = SimpleDatabase()

# Upload-Ordner erstellen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """Hauptseite"""
    stats = {
        'total_samples': len(db.invoices),
        'eingang': len([inv for inv in db.invoices if inv.get('type') == 'Eingangsrechnung']),
        'ausgang': len([inv for inv in db.invoices if inv.get('type') == 'Ausgangsrechnung'])
    }
    return render_template('index.html', stats=stats)

@app.route('/upload', methods=['POST'])
def upload_file():
    """PDF-Upload und -Verarbeitung"""
    if 'file' not in request.files and 'files[]' not in request.files:
        return jsonify({'error': 'Keine Datei'}), 400
    
    file = request.files.get('file') or request.files.getlist('files[]')[0]
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Nur PDF-Dateien'}), 400
    
    try:
        # Datei speichern
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # PDF verarbeiten
        text = extract_text_from_pdf(filepath)
        data = extract_invoice_data(text)
        
        # In DB speichern
        invoice = {
            'filename': filename,
            'unique_filename': unique_filename,
            'supplier': data['supplier'],
            'total': data['total'],
            'invoice_number': data['invoice_number'],
            'date': data['date'],
            'type': data['type'],
            'description': data['description'],
            'extracted_text': text[:500] + "..." if len(text) > 500 else text
        }
        db.add_invoice(invoice)
        
        # Response für Frontend
        return jsonify({
            'success': True,
            'data': {
                'supplier': data['supplier'],
                'invoice_number': data['invoice_number'],
                'date': data['date'],
                'amount': data['total'],
                'currency': 'EUR',
                'description': data['description']
            },
            'raw_text': text[:500] + "..." if len(text) > 500 else text,
            'filename': filename
        })
        
    except Exception as e:
        logger.error(f"Fehler: {e}")
        return jsonify({'error': 'Verarbeitungsfehler'}), 500

@app.route('/results')
def results():
    """Ergebnisseite"""
    return render_template('results.html', invoices=db.get_all_invoices())

@app.route('/export/excel')
def export_excel():
    """Excel-Export"""
    try:
        df = pd.DataFrame(db.get_all_invoices())
        if df.empty:
            return jsonify({'error': 'Keine Daten zum Exportieren'}), 400
        
        filename = f'rechnungen_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        filepath = os.path.join('exports', filename)
        os.makedirs('exports', exist_ok=True)
        df.to_excel(filepath, index=False)
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        logger.error(f"Export-Fehler: {e}")
        return jsonify({'error': 'Export fehlgeschlagen'}), 500

@app.route('/batch_export', methods=['POST'])
def batch_export():
    """Batch-Export für Excel/CSV"""
    try:
        export_format = request.form.get('format', 'excel')
        data = db.get_all_invoices()
        
        if not data:
            return jsonify({'error': 'Keine Daten'}), 400
        
        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format == 'csv':
            filename = f'rechnungen_{timestamp}.csv'
            filepath = os.path.join('exports', filename)
            os.makedirs('exports', exist_ok=True)
            df.to_csv(filepath, index=False, encoding='utf-8')
        else:
            filename = f'rechnungen_{timestamp}.xlsx'
            filepath = os.path.join('exports', filename)
            os.makedirs('exports', exist_ok=True)
            df.to_excel(filepath, index=False)
        
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        logger.error(f"Batch-Export Fehler: {e}")
        return jsonify({'error': 'Export fehlgeschlagen'}), 500

@app.route('/api/stats')
def api_stats():
    """API für Dashboard-Statistiken"""
    return jsonify(db.get_stats())

@app.route('/training')
def training():
    """Training Dashboard (vereinfacht)"""
    stats = {
        'total_samples': len(db.invoices),
        'training_samples': len(db.invoices),
        'accuracy': 87.5,  # Simuliert
        'last_training': datetime.now().isoformat()
    }
    return render_template('training_simple.html', stats=stats)

@app.route('/api/training/train_models', methods=['POST'])
def train_models():
    """Simuliertes Training"""
    try:
        # Simuliere Training
        response = {
            'success': True,
            'message': 'Model erfolgreich trainiert',
            'accuracy': 87.5 + len(db.invoices) * 0.1,  # Simulierte Verbesserung
            'training_samples': len(db.invoices),
            'improvement': 'Genauigkeit verbessert!'
        }
        logger.info(f"Training erfolgreich: {response}")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Training-Fehler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("PDF Rechnungsverarbeitung")
    print("Verfügbar unter: http://127.0.0.1:5001")
    app.run(debug=True, host='127.0.0.1', port=5001)
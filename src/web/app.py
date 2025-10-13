"""
Web Interface für das PDF-Creator Projekt

Flask-basierte Webanwendung für:
- PDF-Upload
- Ergebnisanzeige
- Überwachtes Lernen
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import sys

# Projektpfad hinzufügen
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ocr.pdf_processor import PDFProcessor
from src.classifier.invoice_classifier import InvoiceClassifier
from src.export.excel_exporter import ExcelExporter

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # TODO: In Produktion ändern

# Upload-Konfiguration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Sicherstellen, dass Upload-Ordner existiert
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Komponenten initialisieren
pdf_processor = PDFProcessor()
classifier = InvoiceClassifier()
exporter = ExcelExporter()

def allowed_file(filename):
    """Überprüft, ob die Datei erlaubt ist"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Startseite"""
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """PDF-Upload und -Verarbeitung"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # PDF verarbeiten
            result = process_pdf(filepath)
            
            return render_template('result.html', result=result, filename=filename)
    
    return render_template('upload.html')

def process_pdf(filepath):
    """Verarbeitet eine PDF-Datei"""
    try:
        # Text extrahieren
        text = pdf_processor.extract_text_from_pdf(filepath)
        
        if not text:
            return {'error': 'Kein Text in der PDF gefunden'}
        
        # Text vorverarbeiten
        processed_text = pdf_processor.preprocess_text(text)
        
        # Klassifizierung
        invoice_type, confidence = classifier.classify_invoice_type(processed_text)
        
        # Features extrahieren
        features = classifier.extract_features(processed_text)
        
        result = {
            'text': processed_text[:500] + '...' if len(processed_text) > 500 else processed_text,
            'type': 'Eingangsrechnung' if invoice_type == 'incoming' else 'Ausgangsrechnung',
            'confidence': confidence,
            'features': features,
            'success': True
        }
        
        return result
        
    except Exception as e:
        return {'error': f'Fehler bei der Verarbeitung: {str(e)}'}

@app.route('/export')
def export_data():
    """Exportiert Daten nach Excel"""
    # TODO: Implementierung des Excel-Exports
    flash('Export-Funktion noch nicht implementiert')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
import sys
import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename

# Pfad zu src importieren
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.database import get_session, Invoice

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        # Beispielhafte Klassifizierung (später durch KI ersetzt)
        invoice_type = "Eingangsrechnung" if "eingang" in filename.lower() else "Ausgangsrechnung"

        # In DB speichern
        session = get_session()
        invoice = Invoice(
            filename=filename,
            type=invoice_type,
            supplier="Unbekannt",
            total=0.0
        )
        session.add(invoice)
        session.commit()

        # Alle Rechnungen aus DB laden
        invoices = session.query(Invoice).order_by(Invoice.date.desc()).all()

        return render_template('results.html', filename=filename, invoice_type=invoice_type, invoices=invoices)


@app.route('/export_excel')
def export_excel():
    """Exportiert alle Rechnungen als Excel-Datei"""
    session = get_session()
    invoices = session.query(Invoice).all()

    if not invoices:
        return "Keine Daten zum Exportieren gefunden."

    # In DataFrame umwandeln
    data = [{
        "ID": inv.id,
        "Dateiname": inv.filename,
        "Typ": inv.type,
        "Lieferant": inv.supplier,
        "Betrag (€)": inv.total,
        "Datum": inv.date.strftime("%d.%m.%Y") if inv.date else ""
    } for inv in invoices]

    df = pd.DataFrame(data)

    # Datei speichern
    export_path = os.path.join(os.getcwd(), "rechnungen_export.xlsx")
    df.to_excel(export_path, index=False)

    # Datei an Browser senden
    return send_file(export_path, as_attachment=True)


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)

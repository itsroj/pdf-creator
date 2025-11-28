#!/usr/bin/env python3
"""
PDF zu Excel/CSV Converter - Extrahiert Rechnungsdaten aus PDFs
"""

from flask import Flask, request, render_template, redirect, flash, send_file
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from pdf_processor import extract_pdf_text, extract_data, pdf_to_image_with_highlighting
from database import SimpleDB

app = Flask(__name__)
app.secret_key = "pdf_converter_2025"
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# FLASK ROUTES
# ==========================================
db = SimpleDB()

@app.route("/")
def home():
    return render_template('home.html', stats=db.get_stats())

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files or request.files["file"].filename == "":
        flash("Keine Datei ausgewählt")
        return redirect("/")
    
    file = request.files["file"]
    if not file.filename.lower().endswith('.pdf'):
        flash("Nur PDF-Dateien erlaubt")
        return redirect("/")
    
    # Datei speichern
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    
    # PDF verarbeiten
    text = extract_pdf_text(filepath)
    raw_data = extract_data(text)
    
    # Wende gelernte Korrekturen an
    data, suggestions = db.apply_corrections(raw_data)
    
    # Speichere in DB
    invoice_data = data.copy()
    invoice_data["filename"] = filename
    invoice_data["timestamp"] = str(datetime.now())
    db.add_invoice(invoice_data)
    
    # PDF mit Highlighting - erweitert für mehr Felder
    search_terms = {
        "company": data["company"], 
        "total_amount": data["total_amount"], 
        "number": data["number"], 
        "date": data["date"],
        "net_amount": data["net_amount"],
        "service_date": data["service_date"]
    }
    pdf_image, highlights, img_width, img_height = pdf_to_image_with_highlighting(filepath, search_terms)
    
    result = {
        "filename": filename, 
        "data": data, 
        "suggestions": suggestions,
        "text": text[:500] + "..." if len(text) > 500 else text,
        "pdf_image": pdf_image, 
        "highlights": highlights, 
        "img_width": img_width, 
        "img_height": img_height
    }
    
    return render_template('result.html', result=result)

@app.route("/correct", methods=["POST"])
def correct():
    """Speichert Korrekturen und trainiert das System"""
    # Hole ursprüngliche Daten (in echter App aus Session)
    original_data = {
        "company": request.form.get("original_company", ""),
        "number": request.form.get("original_number", ""),
        "date": request.form.get("original_date", ""),
        "service_date": request.form.get("original_service_date", ""),
        "description": request.form.get("original_description", ""),
        "net_amount": request.form.get("original_net_amount", "0"),
        "tax_rate": request.form.get("original_tax_rate", "0"),
        "total_amount": request.form.get("original_total_amount", "0")
    }
    
    # Korrigierte Daten
    corrected_data = {
        "filename": request.form["filename"],
        "invoice_type": request.form.get("invoice_type", "Eingangsrechnung"),  # NEU: Rechnungstyp
        "company": request.form["company"],
        "number": request.form["number"],
        "date": request.form["date"],
        "service_date": request.form["service_date"],
        "description": request.form["description"],
        "net_amount": float(request.form["net_amount"]) if request.form["net_amount"] else 0,
        "tax_rate": float(request.form["tax_rate"]) if request.form["tax_rate"] else 0,
        "total_amount": float(request.form["total_amount"]) if request.form["total_amount"] else 0,
        "amount": float(request.form["total_amount"]) if request.form["total_amount"] else 0,  # Kompatibilität
        "timestamp": str(datetime.now())
    }
    
    # Trainiere das System mit allen Korrekturen
    company_context = corrected_data["company"]
    corrections_made = 0
    
    for field_type in ["company", "number", "date", "service_date", "description", "net_amount", "tax_rate", "total_amount"]:
        original_value = str(original_data.get(field_type, "")).strip()
        corrected_value = str(corrected_data.get(field_type, "")).strip()
        
        # Nur trainieren wenn sich etwas geändert hat und beide Werte vorhanden sind
        if (original_value and corrected_value and 
            original_value != corrected_value and 
            original_value != "0" and corrected_value != "0"):
            
            db.add_correction(original_value, corrected_value, field_type, company_context)
            corrections_made += 1
    
    # Speichere korrigierte Rechnung
    db.add_invoice(corrected_data)
    
    # Legacy: Alte Trainings-Methode für Kompatibilität
    db.add_sample(original_data, corrected_data)
    
    if corrections_made > 0:
        flash(f"✅ Rechnung gespeichert! KI hat {corrections_made} Korrektur(en) gelernt und wird sie künftig anwenden.")
    else:
        flash("✅ Rechnung gespeichert!")
    
    return redirect("/")

@app.route("/training")
def training():
    """Training Dashboard - zeigt KI-Lernfortschritt"""
    stats = db.get_stats()
    corrections = db.data["corrections"]
    
    # Gruppiere Korrekturen nach Feld-Typ
    corrections_by_field = {}
    for correction in corrections:
        field = correction["field_type"]
        if field not in corrections_by_field:
            corrections_by_field[field] = []
        corrections_by_field[field].append(correction)
    
    # Top-Korrekturen (häufigste)
    top_corrections = sorted(corrections, key=lambda x: x["correction_count"], reverse=True)[:10]
    
    training_data = {
        "stats": stats,
        "corrections_by_field": corrections_by_field,
        "top_corrections": top_corrections,
        "total_corrections": len(corrections)
    }
    
    return render_template('training.html', training=training_data)

@app.route("/data")
def data():
    return render_template('data.html', invoices=db.data["invoices"])

@app.route("/delete_invoice/<int:index>", methods=["POST"])
def delete_invoice(index):
    deleted = db.delete_invoice(index)
    if deleted:
        flash(f"✅ Rechnung '{deleted.get('filename', 'Unbekannt')}' wurde gelöscht!", "success")
    else:
        flash("❌ Rechnung konnte nicht gelöscht werden!", "danger")
    return redirect("/data")

@app.route("/export/excel")
def export_excel():
    filename = "rechnungen_export.xlsx"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    db.export_to_excel(filepath)
    return send_file(filepath, as_attachment=True)

@app.route("/export/csv")
def export_csv():
    filename = "rechnungen_export.csv"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    db.export_to_csv(filepath)
    return send_file(filepath, as_attachment=True)

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("🚀 PDF zu Excel/CSV Converter")
    print("🌐 URL: http://127.0.0.1:5001")
    print("📋 Features: PDF-Upload, OCR, Excel/CSV Export, KI-Training")
    app.run(debug=False, port=5001, host="0.0.0.0")
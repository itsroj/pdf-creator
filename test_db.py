from src.database import get_session, Invoice

# Session erstellen
session = get_session()

# Testeintrag erstellen
test_invoice = Invoice(
    filename="testrechnung.pdf",
    type="Eingangsrechnung",
    supplier="Musterfirma",
    total=123.45
)

# Testeintrag in die Datenbank speichern
session.add(test_invoice)
session.commit()

# Alle Datensätze ausgeben
invoices = session.query(Invoice).all()
for inv in invoices:
    print(f"ID: {inv.id}, Datei: {inv.filename}, Typ: {inv.type}, Lieferant: {inv.supplier}, Betrag: {inv.total}")

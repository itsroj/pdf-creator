from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from sqlalchemy import create_engine

Base = declarative_base()

class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True)
    filename = Column(String)
    type = Column(String)  # 'Eingangsrechnung' oder 'Ausgangsrechnung'
    supplier = Column(String)
    total = Column(Float)
    date = Column(DateTime, default=datetime.utcnow)

def get_engine():
    # Absoluten Pfad zum Projektverzeichnis ermitteln
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Pfad zur Datenbankdatei
    db_path = os.path.join(base_dir, 'data', 'invoices.db')
    
    # Sicherstellen, dass der Ordner existiert
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Verbindung zur SQLite-Datenbank herstellen
    return create_engine(f'sqlite:///{db_path}', echo=False)

def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

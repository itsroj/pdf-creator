"""
Database Module - Handles JSON-based invoice storage and KI learning
"""
import json
import os
import pandas as pd
from datetime import datetime


class SimpleDB:
    """Simple JSON database for invoice management with KI learning capabilities"""
    
    def __init__(self, filename="invoices.json"):
        self.file = filename
        self.data = {"invoices": [], "samples": [], "corrections": []}
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    loaded_data = json.load(f)
                    # Ensure corrections table exists
                    if "corrections" not in loaded_data:
                        loaded_data["corrections"] = []
                    self.data = loaded_data
            except:
                pass
    
    def save(self):
        """Save data to JSON file"""
        with open(self.file, "w") as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def add_invoice(self, invoice):
        """Add a new invoice to the database"""
        self.data["invoices"].append(invoice)
        self.save()
    
    def delete_invoice(self, index):
        """Delete an invoice by index"""
        if 0 <= index < len(self.data["invoices"]):
            deleted = self.data["invoices"].pop(index)
            self.save()
            return deleted
        return None
    
    def add_sample(self, original, corrected):
        """Add a training sample (legacy compatibility)"""
        sample = {
            "original": original,
            "corrected": corrected,
            "timestamp": str(datetime.now())
        }
        self.data["samples"].append(sample)
        self.save()
    
    def add_correction(self, original_text, corrected_text, field_type, company_context=""):
        """Add a new correction or increase frequency of existing one"""
        existing = None
        for correction in self.data["corrections"]:
            if (correction["original_text"].lower() == original_text.lower() and 
                correction["field_type"] == field_type):
                existing = correction
                break
        
        if existing:
            # Increase frequency and confidence (AGGRESSIVE LEARNING!)
            existing["correction_count"] += 1
            # New formula: 1x = 0.7, 2x = 0.95, 3x+ = 1.0
            existing["confidence_score"] = min(1.0, 0.7 + (existing["correction_count"] - 1) * 0.25)
            existing["corrected_text"] = corrected_text  # Update with latest correction
            existing["timestamp"] = str(datetime.now())
        else:
            # New correction (IMMEDIATELY HIGH CONFIDENCE!)
            correction = {
                "original_text": original_text,
                "corrected_text": corrected_text,
                "field_type": field_type,
                "company_context": company_context,
                "correction_count": 1,
                "confidence_score": 0.7,  # Start at 70% confidence - will be auto-applied immediately
                "timestamp": str(datetime.now())
            }
            self.data["corrections"].append(correction)
        self.save()
    
    def apply_corrections(self, data):
        """Apply learned corrections to extracted data"""
        corrected_data = data.copy()
        suggestions = {}
        applied_corrections = []  # For logging
        
        print(f"\n🔍 DEBUG: apply_corrections() called with {len(data)} fields")
        print(f"📊 Corrections in DB: {len(self.data.get('corrections', []))}")
        
        # Get company from data for company-specific corrections
        current_company = data.get("company", "").strip()
        
        for field_type in data.keys():
            # Skip company field itself - never auto-correct it
            if field_type == "company":
                continue
                
            field_value = str(data[field_type]).strip()
            
            # Skip empty or invalid values, but catch common placeholders
            if not field_value or field_value == "0":
                # Check if we have corrections for this empty field
                print(f"  → Field '{field_type}' is empty, looking for corrections...")
                for correction in self.data["corrections"]:
                    if correction["field_type"] == field_type:
                        # Check if correction applies to this company
                        correction_company = correction.get("company_context", "").strip()
                        if correction_company and current_company:
                            if correction_company.lower() in current_company.lower() or current_company.lower() in correction_company.lower():
                                print(f"    ✅ FIRMA-SPEZIFISCHE Korrektur gefunden: {correction['corrected_text']}")
                                suggestions[field_type] = correction["corrected_text"]
                                break
                continue
            
            print(f"  → Checking field '{field_type}' = '{field_value}'")
                
            # Search for matching corrections
            best_match = None
            for correction in self.data["corrections"]:
                if correction["field_type"] == field_type:
                    # Check company context if available
                    correction_company = correction.get("company_context", "").strip()
                    if correction_company and current_company:
                        # Only apply if company matches
                        if not (correction_company.lower() in current_company.lower() or 
                                current_company.lower() in correction_company.lower()):
                            print(f"    ⏭️ Skipping correction (different company: {correction_company})")
                            continue
                    
                    # Check exact match or similarity
                    similarity = self._text_similarity(correction["original_text"], field_value)
                    is_exact = correction["original_text"].lower() == field_value.lower()
                    
                    print(f"    📋 Correction found: '{correction['original_text']}' → '{correction['corrected_text']}'")
                    print(f"       Confidence: {correction['confidence_score']}, Similarity: {similarity:.2f}, Exact: {is_exact}")
                    
                    if is_exact or similarity > 0.7:  # Lowered from 0.8 to 0.7
                        if not best_match or correction["confidence_score"] > best_match["confidence_score"]:
                            best_match = correction
                            print(f"       ✅ Best match updated!")
            
            if best_match:
                print(f"    ⭐ Best match for '{field_type}': Confidence {best_match['confidence_score']}")
                if best_match["confidence_score"] >= 0.6:  # Lowered from 0.75 to 0.6 - faster auto-correction
                    # Auto-correction with high confidence
                    corrected_data[field_type] = best_match["corrected_text"]
                    applied_corrections.append(f"{field_type}: {field_value} → {best_match['corrected_text']}")
                    print(f"    🤖 AUTO-CORRECTION applied!")
                elif best_match["confidence_score"] >= 0.4:  # Suggestions at medium confidence
                    # Suggestion with medium confidence
                    suggestions[field_type] = best_match["corrected_text"]
                    print(f"    💡 Suggestion stored!")
        
        # Logging for debugging
        if applied_corrections:
            print(f"🤖 KI auto-corrected: {', '.join(applied_corrections)}")
        if suggestions:
            print(f"💡 KI suggestions available for: {', '.join(suggestions.keys())}")
        
        return corrected_data, suggestions
    
    def _text_similarity(self, text1, text2):
        """Simple text similarity based on common words"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return intersection / union if union > 0 else 0
    
    def get_stats(self):
        """Get database statistics"""
        samples = len(self.data["samples"])
        corrections = len(self.data["corrections"])
        total_corrections = sum(c["correction_count"] for c in self.data["corrections"])
        return {
            "invoices": len(self.data["invoices"]), 
            "samples": samples, 
            "corrections": corrections,
            "total_corrections": total_corrections,
            "accuracy": min(95, 60 + total_corrections * 1.5)
        }
    
    def export_to_excel(self, filename):
        """Export invoices to Excel file"""
        df = pd.DataFrame(self.data["invoices"])
        df.to_excel(filename, index=False)
    
    def export_to_csv(self, filename):
        """Export invoices to CSV file"""
        df = pd.DataFrame(self.data["invoices"])
        df.to_csv(filename, index=False)

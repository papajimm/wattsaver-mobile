import fitz  # PyMuPDF
import re

class BillParser:
    def __init__(self):
        pass

    def extract_text_from_pdf(self, pdf_path):
        text_content = ""
        try:
            doc = fitz.open(pdf_path)
            for i in range(min(2, len(doc))):
                text_content += doc[i].get_text() + "\n"
            doc.close()
            return text_content
        except Exception as e:
            return None

    def parse_bill(self, file_path):
        text = self.extract_text_from_pdf(file_path)
        
        if not text:
            return {"error": "Could not read PDF. Ensure it is a valid file."}
        
        # DEBUG: Print snippet
        print(f"--- PARSING: {file_path} ---")
        print(f"Text Sample: {text[:200]}...")

        data = {
            "total_kwh": 0,
            "days": 30,
            "provider_detected": "Unknown",
            "bill_type": "electricity"
        }

        # 1. Detect Provider
        if "Zeni" in text or "Zenith" in text: data["provider_detected"] = "Zenith"       
        elif "Protergia" in text: data["provider_detected"] = "Protergia"
        elif "DEI" in text or "ΔΕΗ" in text: data["provider_detected"] = "DEI"
        elif "Enerwave" in text: data["provider_detected"] = "Enerwave"
        elif "ΦΥΣΙΚΟ ΑΕΡΙΟ" in text: data["provider_detected"] = "Fysiko Aerio"   

        # 2. Extract Numbers for Analysis
        # Find all numbers like 180,26 or 15.48
        numbers = re.findall(r'(\d+[.,]\d{2})', text)
        clean_nums = []
        for n in numbers:
            try:
                val = float(n.replace(',', '.'))
                clean_nums.append(val)
            except: pass

        # 3. Smart Detection: Gas vs Elec
        # Check if we have a pair of numbers (Nm3, kWh) with ratio ~11.5
        is_gas_by_math = False
        found_gas_kwh = 0

        for i in range(len(clean_nums) - 1):
            n1 = clean_nums[i] # Candidate Nm3
            n2 = clean_nums[i+1] # Candidate kWh
            if n1 > 1:
                ratio = n2 / n1
                if 10.5 < ratio < 12.5: # Typical Gas conversion factor
                    is_gas_by_math = True
                    found_gas_kwh = n2
                    break

        # Check text keywords as fallback
        is_gas_by_text = False
        is_elec_by_text = False

        if "Nm3" in text or "θερμογόνος" in text:
            is_gas_by_text = True
        
        if "kVA" in text or "ΔΕΔΔΗΕ" in text or "ΑΔΜΗΕ" in text or "ΗΛΕΚΤΡΙΣΜΟΣ" in text.upper():
            is_elec_by_text = True
            
        print(f"DEBUG: Gas_Math={is_gas_by_math}, Gas_Text={is_gas_by_text}, Elec_Text={is_elec_by_text}")

        # Final Decision
        if is_gas_by_math:
            data["bill_type"] = "gas"
            data["total_kwh"] = int(found_gas_kwh)
        elif is_gas_by_text and not is_elec_by_text:
            data["bill_type"] = "gas"
            # Fallback kwh if math failed (pick realistic gas number)
            valid = [x for x in clean_nums if x < 5000]
            data["total_kwh"] = int(max(valid)) if valid else 0
        elif is_elec_by_text and not is_gas_by_text:
             data["bill_type"] = "electricity"
             # Elec logic
             zenith_match = re.search(r"Σύνολο Κατανάλωσης.*?(\d+)", text, re.DOTALL)
             if zenith_match:
                data["total_kwh"] = int(zenith_match.group(1))
             elif clean_nums:
                valid = [x for x in clean_nums if 50 < x < 3000]
                if valid: data["total_kwh"] = int(max(valid))
        else:
             # Ambiguous: Default to Electricity unless math found gas
             if is_gas_by_text: # Strong hint
                 data["bill_type"] = "gas"
                 valid = [x for x in clean_nums if x < 5000]
                 data["total_kwh"] = int(max(valid)) if valid else 0
             else:
                 data["bill_type"] = "electricity"
                 zenith_match = re.search(r"Σύνολο Κατανάλωσης.*?(\d+)", text, re.DOTALL)
                 if zenith_match:
                    data["total_kwh"] = int(zenith_match.group(1))
                 elif clean_nums:
                    valid = [x for x in clean_nums if 50 < x < 3000]
                    if valid: data["total_kwh"] = int(max(valid))
        
        print(f"DEBUG: Result Bill Type = {data['bill_type']}")


        # Days
        days_match = re.search(r"ΗΜΕΡΕΣ.*?(\d{2,3})", text, re.IGNORECASE)
        if days_match:
            try: data["days"] = int(days_match.group(1))
            except: pass

        return data

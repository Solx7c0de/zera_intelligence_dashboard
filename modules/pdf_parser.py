"""PDF Parser for ZERA Smart Meter Test Reports"""
import os
import re
import pdfplumber
import pandas as pd
from database.db import insert_df, table_row_count

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def parse_voltage_events(pdf_path: str) -> pd.DataFrame:
    """Parse voltage related event profile PDF.
    
    Each event is a 3-line block:
      Line 1: dd.mm.yyyy/HH:MM: <event_type> <IR> A <IY> A <IB> A <VRN> V <VYN> V <VBN> V <pfR> <pfY> <pfB> <energy> Wh
      Line 2: <seconds> <event_detail_fragment>-
      Line 3: Occurrence | Restoration
    Then cumulative data follows (we grab tamper count from there).
    """
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        all_lines = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(text.split("\n"))
    
    data_re = re.compile(
        r"(\d{2}\.\d{2}\.\d{4}/\d{2}:\d{2}:\s*)"
        r"(.+?)\s+"
        r"([\d.]+)\s+A\s+"
        r"([\d.]+)\s+A\s+"
        r"([\d.]+)\s+A\s+"
        r"([\d.]+)\s+V\s+"
        r"([\d.]+)\s+V\s+"
        r"([\d.]+)\s+V\s+"
        r"([\d.]+)\s+"
        r"([\d.]+)\s+"
        r"([\d.]+)\s+"
        r"(\d+)\s+Wh"
    )
    
    i = 0
    while i < len(all_lines):
        line = all_lines[i].strip()
        m = data_re.match(line)
        if m:
            dt_str = m.group(1).strip()
            event_raw = m.group(2).strip()
            ir, iy, ib = float(m.group(3)), float(m.group(4)), float(m.group(5))
            vrn, vyn, vbn = float(m.group(6)), float(m.group(7)), float(m.group(8))
            pf_r, pf_y, pf_b = float(m.group(9)), float(m.group(10)), float(m.group(11))
            cum_energy = int(m.group(12))
            
            event_detail = ""
            event_action = "Unknown"
            if i + 1 < len(all_lines):
                event_detail = all_lines[i + 1].strip()
            if i + 2 < len(all_lines):
                action_line = all_lines[i + 2].strip()
                if "Restoration" in action_line:
                    event_action = "Restoration"
                elif "Occur" in action_line:
                    event_action = "Occurrence"
            
            full_event = event_raw
            if event_detail:
                detail_clean = re.sub(r"^\d+\s*", "", event_detail).rstrip("-").strip()
                if detail_clean:
                    full_event = f"{event_raw} {detail_clean}"
            
            try:
                event_dt = pd.to_datetime(dt_str, format="%d.%m.%Y/%H:%M:", errors="coerce")
            except:
                event_dt = None

            tamper_count = None
            for offset in range(3, 7):
                if i + offset < len(all_lines):
                    cum_line = all_lines[i + offset].strip()
                    tm = re.search(r"(\d+)\s+(?:VAh|Wh)\s+(\d+)\s+(\d+)\s+VAh", cum_line)
                    if tm:
                        tamper_count = int(tm.group(2))
                        break
                    tm2 = re.match(r"(\d+)\s+Wh\s+(\d+)\s+(\d+)\s+VAh\s+(\d+)\s+VAh", cum_line)
                    if tm2:
                        tamper_count = int(tm2.group(2))
                        break
            
            rows.append({
                "event_datetime": event_dt,
                "event_type": full_event,
                "event_action": event_action,
                "current_ir": ir, "current_iy": iy, "current_ib": ib,
                "voltage_vrn": vrn, "voltage_vyn": vyn, "voltage_vbn": vbn,
                "pf_r": pf_r, "pf_y": pf_y, "pf_b": pf_b,
                "cum_energy_kwh_import": cum_energy,
                "cum_tamper_count": tamper_count,
            })
            i += 7
        else:
            i += 1
    
    return pd.DataFrame(rows)


def parse_power_events(pdf_path: str) -> pd.DataFrame:
    """Parse power related event profile PDF."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                line = line.strip()
                m = re.match(r"(\d{2}\.\d{2}\.\d{4}/\d{2}:\d{2}:\d{2})\s+(.+?)-(Occurrence|Restoration)", line)
                if m:
                    try:
                        event_dt = pd.to_datetime(m.group(1), format="%d.%m.%Y/%H:%M:%S", errors="coerce")
                    except:
                        event_dt = None
                    rows.append({
                        "event_datetime": event_dt,
                        "event_type": m.group(2).strip(),
                        "event_action": m.group(3),
                    })
    return pd.DataFrame(rows)


def parse_other_events(pdf_path: str) -> pd.DataFrame:
    """Parse other event profile PDF."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        all_lines = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(text.split("\n"))
    
    data_re = re.compile(
        r"(\d{2}\.\d{2}\.\d{4}/\d{2}:\d{2}:\s*)"
        r"(.+?)\s+"
        r"([\d.]+)\s+A\s+"
        r"([\d.]+)\s+A\s+"
        r"([\d.]+)\s+A\s+"
        r"([\d.]+)\s+V\s+"
        r"([\d.]+)\s+V\s+"
        r"([\d.]+)\s+V"
    )
    
    i = 0
    while i < len(all_lines):
        line = all_lines[i].strip()
        m = data_re.match(line)
        if m:
            event_action = "Unknown"
            if i + 2 < len(all_lines):
                action_line = all_lines[i + 2].strip()
                if "Restoration" in action_line:
                    event_action = "Restoration"
                elif "Occur" in action_line:
                    event_action = "Occurrence"
            try:
                event_dt = pd.to_datetime(m.group(1).strip(), format="%d.%m.%Y/%H:%M:", errors="coerce")
            except:
                event_dt = None
            rows.append({
                "event_datetime": event_dt,
                "event_type": m.group(2).strip(),
                "event_action": event_action,
                "current_ir": float(m.group(3)),
                "voltage_vrn": float(m.group(6)),
                "voltage_vyn": float(m.group(7)),
                "voltage_vbn": float(m.group(8)),
            })
            i += 7
        else:
            i += 1
    return pd.DataFrame(rows)


def parse_transaction_events(pdf_path: str) -> pd.DataFrame:
    """Parse transaction related event profile PDF."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        all_lines = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(text.split("\n"))
    
    txn_re = re.compile(r"(\d{2}\.\d{2}\.\d{4}/\d{2}:\d{2}:\d{2})\s+(.+)")
    
    for line in all_lines:
        line = line.strip()
        m = txn_re.match(line)
        if m:
            try:
                event_dt = pd.to_datetime(m.group(1), format="%d.%m.%Y/%H:%M:%S", errors="coerce")
            except:
                event_dt = None
            rows.append({
                "event_datetime": event_dt,
                "event_description": m.group(2).strip(),
            })
    
    return pd.DataFrame(rows)


def parse_accuracy_report() -> pd.DataFrame:
    """Hardcoded accuracy & data readout results from the ACCURACY PDF."""
    data = [
        {"meter_serial": "3003596", "manufacturer": "AVON", "manufacture_year": 2017,
         "firmware_version": "01.07.05", "total_evaluation": "pass",
         "tamper_count": 105, "power_fail_count": 31, "cum_power_fail_duration": 126273,
         "billing_count": 44, "programming_count": 10, "max_demand_kw": 4.236},
        {"meter_serial": "3003037", "manufacturer": "AVON", "manufacture_year": 2017,
         "firmware_version": "01.07.05", "total_evaluation": "pass",
         "tamper_count": 12, "power_fail_count": 88, "cum_power_fail_duration": 1048002,
         "billing_count": 51, "programming_count": 7, "max_demand_kw": 3.612},
        {"meter_serial": "T1234965", "manufacturer": "Eppeltone", "manufacture_year": 2022,
         "firmware_version": "02.01.03", "total_evaluation": "pass",
         "tamper_count": 0, "power_fail_count": 2, "cum_power_fail_duration": 450,
         "billing_count": 10, "programming_count": 3, "max_demand_kw": 0.5},
        {"meter_serial": "AV/M211/3", "manufacturer": "ISKRA", "manufacture_year": 2020,
         "firmware_version": "03.02.01", "total_evaluation": "fail",
         "tamper_count": 250, "power_fail_count": 150, "cum_power_fail_duration": 2500000,
         "billing_count": 60, "programming_count": 20, "max_demand_kw": 5.1},
    ]
    return pd.DataFrame(data)


def _load_if_empty(table_name: str, parser_fn, *parser_args, results: dict):
    """Skip-if-already-populated wrapper. Handles missing-table case (-1) too."""
    try:
        existing = table_row_count(table_name)
        if existing > 0:
            results[table_name] = existing
            return
        df = parser_fn(*parser_args)
        if df is not None and len(df) > 0:
            insert_df(df, table_name)
            results[table_name] = len(df)
        else:
            results[table_name] = 0
    except Exception as e:
        results[table_name] = f"Error: {e}"


def load_all_meter_data() -> dict:
    """Parse all meter PDFs and load into database. Idempotent — skips
    tables that already have data so repeated calls don't duplicate rows."""
    results = {}
    
    # Accuracy test (hardcoded)
    _load_if_empty("meter_accuracy_test", parse_accuracy_report, results=results)
    
    # Voltage events
    voltage_pdf = os.path.join(DATA_DIR, "S-14_MP2_Voltage_Related_Event_Profile_3003597_02-02-2026_152227.pdf")
    if os.path.exists(voltage_pdf):
        _load_if_empty("meter_voltage_events", parse_voltage_events, voltage_pdf, results=results)
    
    # Power events
    power_pdf = os.path.join(DATA_DIR, "S-14_MP2_Power_Realated_Event_Profile_3003597_02-02-2026_152306.pdf")
    if os.path.exists(power_pdf):
        _load_if_empty("meter_power_events", parse_power_events, power_pdf, results=results)
    
    # Other events
    other_pdf = os.path.join(DATA_DIR, "S-14_MP2_Other_Event_Profile_3003597_02-02-2026_152349.pdf")
    if os.path.exists(other_pdf):
        _load_if_empty("meter_other_events", parse_other_events, other_pdf, results=results)
    
    # Transaction events
    txn_pdf = os.path.join(DATA_DIR, "S-14_MP2_Transaction_Related_Event_3003597_02-02-2026_152421.pdf")
    if os.path.exists(txn_pdf):
        _load_if_empty("meter_transaction_events", parse_transaction_events, txn_pdf, results=results)
    
    return results

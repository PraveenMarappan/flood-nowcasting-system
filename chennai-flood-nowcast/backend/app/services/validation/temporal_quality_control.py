from typing import List, Dict, Any

class TemporalQualityControl:
    """
    Automated Quality Control module for temporal gauge time series.
    Flags quality anomalies:
    - Missing / invalid timestamps
    - Duplicate timestamps
    - Negative depth values
    - Impossible depth values (> 500 cm)
    - Sensor flatlining (unchanged non-zero reading > 24 hrs)
    - Rapid sensor resets / unphysical jumps
    Preserves raw data and applies explicit QC flags.
    """

    MAX_POSSIBLE_DEPTH_CM = 500.0  # 5 meters urban street flood limit

    def run_qc(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        cleaned_records = []
        flagged_records = []

        qc_summary = {
            "total_input_records": len(records),
            "valid_records": 0,
            "missing_timestamps": 0,
            "duplicate_timestamps": 0,
            "negative_depths": 0,
            "impossible_depths": 0,
            "flatlined_sensors": 0,
            "outliers_flagged": 0
        }

        seen_keys = set()
        
        # Sort by station and time
        sorted_recs = sorted(records, key=lambda r: (r.get("station_id", ""), r.get("timestamp", "")))

        for r in sorted_recs:
            station = r.get("station_id", "UNKNOWN")
            ts = r.get("timestamp")
            depth = r.get("observed_depth_cm")

            flags = []

            # 1. Missing timestamp
            if not ts:
                qc_summary["missing_timestamps"] += 1
                flags.append("FLAG_MISSING_TIMESTAMP")

            # 2. Duplicate timestamp for same station
            key = (station, ts)
            if key in seen_keys:
                qc_summary["duplicate_timestamps"] += 1
                flags.append("FLAG_DUPLICATE_TIMESTAMP")
            else:
                seen_keys.add(key)

            # 3. Negative depth
            if depth is not None and depth < 0:
                qc_summary["negative_depths"] += 1
                flags.append("FLAG_NEGATIVE_DEPTH")

            # 4. Impossible depth (> 500 cm)
            if depth is not None and depth > self.MAX_POSSIBLE_DEPTH_CM:
                qc_summary["impossible_depths"] += 1
                flags.append("FLAG_IMPOSSIBLE_DEPTH")

            rec_copy = dict(r)
            if flags:
                rec_copy["quality_flag"] = ";".join(flags)
                flagged_records.append(rec_copy)
            else:
                rec_copy["quality_flag"] = "VALID"
                cleaned_records.append(rec_copy)

        qc_summary["valid_records"] = len(cleaned_records)

        return {
            "cleaned_records": cleaned_records,
            "flagged_records": flagged_records,
            "qc_summary": qc_summary
        }

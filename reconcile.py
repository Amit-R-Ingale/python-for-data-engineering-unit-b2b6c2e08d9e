import csv
import os
import sys

REQUERIED_COLUMNS = ("flight_number", "passenger_name", "bag_tag")

def clean_tag(text):
    return text.strip().upper()

def read_manifest(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = [name.strip() for name in (reader.fieldnames or [])]
        missing = [col for col in REQUERIED_COLUMNS if col not in header]

        if missing:
            raise ValueError("manifest is missing column(s): " + ", ".join(missing))
        reader.fieldnames = header
        tags = set()
        for row in reader:
            tag = clean_tag(row["bag_tag"] or "")
            if tag:
                tags.add(tag)
        return tags

def read_scan(path):
    with open(path, encoding="utf-8-sig") as handle:
        return {clean_tag(line) for line in handle if clean_tag(line)}


def reconcile(expected, scanned):
    missing = sorted(expected - scanned)
    extra = sorted(scanned - expected)
    verdict = "RECONCILED" if not missing and not extra else "DISCREPANCY"
    return {
        "expected": len(expected),
        "scanned": len(scanned),
        "missing": missing,
        "extra": extra,
        "verdict": verdict
    }

def format_report(result):
    lines = [
        "BAGGAGE RECONCILATION REPORT",
        "Total bags expected: %d" % result["expected"],
        "Total bags scanned: %d" % result["scanned"],
        "Missing from scan (%d):" % len(result["missing"]),
    ]

    lines += [" - " + tag for tag in result["missing"]] or [" (none)"]
    lines.append("Not on manifest - SECURITY CHECK (%d):" % len(result["extra"]))
    lines += [" - " + tag for tag in result["extra"]] or [" (none)"]
    lines.append("Verdict: " + result["verdict"])
    return "\n".join(lines)

def main(argv):
    if len(argv) != 2:
        program = os.path.basename(sys.argv[0])
        print("Usage: python %s MANIFEST_CSV SCAN_FILE" % program)
        return 2
    manifest_path, scan_path = argv
    try:
        expected = read_manifest(manifest_path)
        scanned = read_scan(scan_path)
    except (OSError, ValueError) as error:
        print("Error: %s" % error)
        return 2
    result = reconcile(expected, scanned)
    print(format_report(result))
    return 0 if result["verdict"] == "RECONCILED" else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
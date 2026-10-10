import contextlib
import io
import os
import shutil
import tempfile
import unittest

import reconcile

class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder)

    def write(self, name, text):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path

    def run_main(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = reconcile.main(list(args))
        return code, output.getvalue()

    def manifest(self, newline="\n"):
        rows = [
            "flight_number,passanger_name,bag_tag",
            "RA101,Maria Lopez,AA123",
            "RA101,James Chen,AA456",
            "RA101,Priya Nair,AA789"
        ]
        return self.write("manifest.csv", newline.join(rows) + newline)

    def test_example_from_the_task(self):
        scan = self.write("scan.txt", "AA123\nAA789\nAA999\n")
        code, text = self.run_main(self.manifest(), scan)
        self.assertEqual(code, 1)
        self.assertIn("Total bags expected: 3", text)
        self.assertIn("Total bags scanned: 3", text)
        self.assertIn("Missing from scan (1):\n - AA456", text)
        self.assertIn("SECURITY CHECK (1):\n - AA999", text)
        self.assertTrue(text.strip().endswith("Verdict: DISCREPANCY"))

    def test_exact_match_is_reconciled(self):
        scan = self.write("scan.txt", "AA789\nAA123\nAA456\n")
        code, text = self.run_main(self.manifest(), scan)
        self.assertEqual(code, 0)
        self.assertIn("Missing from scan (0):\n (none)", text)
        self.assertIn("SECURITY CHECK (0):\n (none)", text)
        self.assertTrue(text.strip().endswith("Verdict: RECONCILED"))

    def test_windows_line_endings_are_handled(self):
        manifest = self.manifest(newline="\r\n")
        scan = self.write("scan.txt", "AA123\r\nAA456\r\nAA789\r\n")
        self.assertEqual(reconcile.read_manifest(manifest), {"AA123", "AA456", "AA789"})
        self.assertEqual(reconcile.read_scan(scan), {"AA123", "AA456", "AA789"})

    def test_blank_lines_spaces_case_and_repeats_are_ignored(self):
        scan = self.write("scan.txt", "\n aa123\nAA123\n\nAA456\nAA789\n\n")
        self.assertEqual(reconcile.read_scan(scan), {"AA123", "AA456", "AA789"})

    def test_manifest_with_excel_bom_and_spaced_header(self):
        path = self.write("manifest.csv", "\ufeffflight_number, passanger_name, bag_tag\n" "RA101,Maria Lopez,AA123\n")
        self.assertEqual(reconcile.read_manifest(path), {"AA123"})

    def test_missing_bag_tag_column_is_an_error(self):
        bad = self.write("manifest.csv", "flight_number,passanger_name\n" "RA101,Maria Lopez\n")
        scan = self.write("scan.txt", "AA123\n")
        code, text = self.run_main(bad, scan)
        self.assertEqual(code, 2)
        self.assertIn("missing column(s): bag_tag", text)


    def test_missing_file_is_an_error(self):
        scan = self.write("scan.txt", "AA123\n")
        missing = os.path.join(self.folder, "nope.csv")
        code, text = self.run_main(missing, scan)
        self.assertEqual(code, 2)
        self.assertIn("Error:", text)


    def test_wrong_number_of_arguments_prints_usage(self):
        code, text = self.run_main("only_one.csv")
        self.assertEqual(code, 2)
        self.assertIn("Usage:", text)


    def test_reconcile_counts_and_sorting(self):
        result = reconcile.reconcile({"B2", "A1", "C3"}, {"C3", "Z9", "Y8"})
        self.assertEqual(result["expected"], 3)
        self.assertEqual(result["scanned"], 3)
        self.assertEqual(result["missing"], ["A1", "B2"])
        self.assertEqual(result["extra"], ["Y8", "Z9"])
        self.assertEqual(result["verdict"], "DISCREPANCY")


if __name__ == "__main__":
    unittest.main()
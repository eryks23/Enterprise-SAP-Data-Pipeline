import json
import logging
import csv
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"


DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')


file_handler = RotatingFileHandler(
    LOG_DIR / "sap_process.log", 
    maxBytes=5*1024*1024,
    backupCount=5
)

file_handler.setFormatter(log_formatter)


console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)


logger = logging.getLogger("SAPIntegrator")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class SAPIntegrator:
    def __init__(self, input_filename="input_data.json"):
        self.input_path = DATA_DIR / input_filename
        self.data = []
        self.valid_data = []
        self.error_log = []
        self._setup_gitignore()

    def _setup_gitignore(self):
        gitignore_path = BASE_DIR / ".gitignore"
        ignored_patterns = ["data/", "logs/", "__pycache__/", "*.pyc"]
        

        try:
            if not gitignore_path.exists():
                with open(gitignore_path, "w", encoding="UTF-8") as f:
                    f.write("\n".join(ignored_patterns))

                logger.info("Security: Created .gitignore to protect data and logs")
                

        except Exception as e:
            logger.warning(f"Security Warning: Could not create .gitignore: {e}")


    def _create_sample_data_if_missing(self):
        if not self.input_path.exists():

            sample_data = [

                {"vat_id": "PL1234567890", "country": "PL", "email": "test@pro.pl"},
                {"vat_id": "ABC12345", "country": "DE", "email": "invalid-email"},
                {"vat_id": None, "country": "PL", "email": "missing@vat.pl"}

            ]


            with open(self.input_path, "w", encoding="UTF-8") as f:
                json.dump(sample_data, f, indent=4)

            logger.info(f"Created sample data file at {self.input_path}")


    def load_data(self):
        self._create_sample_data_if_missing()
        

        if not self.input_path.exists():
            logger.error(f"Input file missing: {self.input_path}")
            return
        

        try:
            with open(self.input_path, "r", encoding="UTF-8") as f:
                self.data = json.load(f)


            if not isinstance(self.data, list):
                raise ValueError("JSON data must be a list of records")

            logger.info(f"Loaded {len(self.data)} records from data source")

        except (json.JSONDecodeError, IOError, ValueError) as e:
            logger.error(f"Critical error during data load: {e}")


    def validate_vat(self, vat_id, country):
        vat_str = str(vat_id or "").strip()


        if country == "PL":
            return bool(re.match(r"^PL\d{10}$", vat_str))
        

        return len(vat_str) > 0


    def validate_email(self, email):
        email_str = str(email or "").strip()
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_regex, email_str))


    def process_data(self):
        if not self.data:
            logger.warning("No data to process")
            return


        for record in self.data:
            try:
                country = record.get("country", "UNKNOWN")
                is_vat_valid = self.validate_vat(record.get("vat_id"), country)
                is_email_valid = self.validate_email(record.get("email"))

                record["group"] = "DOMESTIC" if country == "PL" else "INTERNATIONAL"

                if is_vat_valid and is_email_valid:
                    self.valid_data.append(record)

                else:
                    error_record = record.copy()
                    error_record['error_reason'] = "Validation failed (VAT/Email)"
                    self.error_log.append(error_record)

            except Exception as e:
                logger.error(f"Unexpected record error: {e}")


    def _save_to_csv(self, filename, dataset):
        if not dataset:
            return
        
        output_path = DATA_DIR / filename

        try:
            keys = set()

            for row in dataset:
                keys.update(row.keys())

            fieldnames = sorted(list(keys))

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(dataset)

            logger.info(f"File saved successfully: {filename}")

        except IOError as e:
            logger.error(f"Save error for {filename}: {e}")


    def run(self):
        logger.info("Starting SAP Data Pre-processing pipeline...")
        self.load_data()
        self.process_data()
        self._save_to_csv("processed_success.csv", self.valid_data)
        self._save_to_csv("processed_errors.csv", self.error_log)
        logger.info(f"Process finished. Success: {len(self.valid_data)}, Failures: {len(self.error_log)}")


if __name__ == "__main__":
    integrator = SAPIntegrator()
    integrator.run()

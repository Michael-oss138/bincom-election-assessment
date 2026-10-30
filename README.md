# Bincom election results assessment — Django starter

This project implements the three requested pages using Django and the supplied legacy MySQL schema:

1. Individual polling-unit results (`/polling-unit/`).
2. LGA totals aggregated from `announced_pu_results` (`/lga-results/`). It intentionally does **not** read `announced_lga_results` for the totals.
3. A form to save results for every party for a polling unit with no existing result rows (`/enter-results/`).

The models map to the existing tables (`managed = False`), so Django will not try to create the legacy data tables. The SQL file identifies its database as `bincomphptest` and is a MySQL/phpMyAdmin dump.

## Setup

1. Install Python 3.10+ and MySQL/MariaDB.
2. Create a database and import the supplied dump. For example, from a terminal:

   ```bash
   mysql -u root -p -e "CREATE DATABASE bincomphptest CHARACTER SET latin1;"
   mysql -u root -p bincomphptest < /path/to/bincom_test.sql
   ```

   If the SQL import fails because the dump contains legacy `0000-00-00 00:00:00` dates, use a local MySQL/MariaDB configuration compatible with this 2011 dump or clean those invalid date values in a copy of the dump before importing. Keep the original unchanged.

3. From this project directory, create/activate a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   # macOS/Linux:
   source .venv/bin/activate
   # Windows PowerShell:
   # .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. Configure connection environment variables (use your actual local MySQL credentials):

   ```bash
   export DB_NAME=bincomphptest
   export DB_USER=root
   export DB_PASSWORD='your-password'
   export DB_HOST=127.0.0.1
   export DB_PORT=3306
   ```

   On Windows PowerShell, use `$env:DB_NAME="bincomphptest"` and equivalent commands for the other values.

5. Start Django:

   ```bash
   python manage.py check
   python manage.py runserver
   ```

   Open `http://127.0.0.1:8000/` in a browser.

## Schema notes / limitations to verify against the imported database

- `polling_unit.uniqueid` is matched to `announced_pu_results.polling_unit_uniqueid` (stored as text in the results table).
- The dump's `polling_unit.lga_id` corresponds to `lga.lga_id`; the supplied data uses this legacy ID rather than `lga.uniqueid`.
- The ward and polling-unit tables have legacy numeric IDs. Before deployment, verify the ward relationship for the selected LGA against the data, as the original dump does not declare foreign-key constraints.
- Question 3 is interpreted as entering results for an existing polling unit with no result rows. If the assessor means creating a brand-new polling-unit record as well, that is a separate workflow and needs the required polling-unit metadata fields.
- This is an assessment starter, not production-ready election software. Add authentication/authorisation, audit logging, and stricter duplicate/correction handling before real use.

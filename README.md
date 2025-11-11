## AI-Powered Household Energy Recommendation System

Flask + SQLite + Bootstrap + Chart.js web app to calculate baseline energy, cost, and CO₂; generate explainable recommendations; simulate scenarios; and export reports.

### Features
- Onboarding/Profile with tariff and emission factor
- Appliance catalog with quantity, power, usage, efficiency
- Dashboard KPIs and charts (Chart.js)
- Rule-based recommendations with formulas, quantified savings, and payback
- Scenario simulator to compare baseline vs. measures
- Admin Assumptions for editable coefficients
- Exports: CSV (pandas) and PDF (WeasyPrint)
- Unit tests for core formulas (pytest)

### Setup (local)
1. Create virtualenv and install:
   ```
   pip install -r requirements.txt
   ```
2. Run the app:
   ```
   python wsgi.py
   ```
3. Seed demo data (optional):
   ```
   python seeds.py
   ```
4. Open http://localhost:5000

### Tests
```
pytest -q
```

### Deploy
- Docker:
  ```
  docker build -t energy-advisor .
  docker run -p 5000:5000 energy-advisor
  ```
- Render: set start command to `gunicorn wsgi:app`

### Formulas
- Daily energy: E_daily = Σ(P × N × T) / 1000
- Monthly energy: E_month = E_daily × 30
- Cost: Cost = E_month × tariff
- CO₂: CO₂ = E_month × EF
- Measures:
  - Lighting swap: ΔE = ((P_old − P_led) × N × T / 1000) × 30
  - AC setpoint: ΔE = E_AC × (0.04 × ΔT)
  - Standby cut: ΔE = (P_s × t × N / 1000) × 30
  - Fridge upgrade: ΔE = (E_old − E_new) / 12
  - Payback: retrofit_cost / ΔCost



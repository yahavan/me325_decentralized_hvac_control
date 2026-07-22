# ME325 — Decentralised HVAC Control System
### 3rd Year Project | University of Peradeniya

A decentralised multi-zone HVAC control simulation for a 5-zone Sri Lankan commercial building.  
Each zone runs its own PI controller; an AHU coordinator handles supply-air temperature and outdoor-air flow.

---

## 📁 Project Structure

```
me325_decentralized_hvac_control/
│
├── main.py                  # EnergyPlus co-simulation driver (requires EnergyPlus)
├── simulate.py              # Pure-Python standalone simulation (no EnergyPlus needed)
├── config.py                # Zone configuration (setpoints, flow limits, PI gains)
├── analyse_results.py       # Post-simulation analysis & plots
├── visualize.py             # Additional visualisation tools
├── dashboard.html           # Interactive browser dashboard
├── comparison_report.html   # Centralised vs. decentralised comparison
│
├── controllers/
│   ├── zone_controller.py   # Base PI controller class
│   ├── zone1.py … zone5.py  # Per-zone controller (Open Office, Private Offices,
│   │                        #   Conference Room, Server Room, Reception)
│   └── ahu.py               # AHU coordinator (SAT + OA flow)
│
├── model/
│   ├── MultiZone_VAV_PythonControl.idf   # EnergyPlus building model
│   └── Colombo.epw                       # Weather file — Colombo, Sri Lanka
│
├── others/                  # Extra weather/reference files
├── out/                     # Simulation output folder (auto-created)
└── docs/                    # Project report PDF
```

---

## 🚀 Quick Start — No EnergyPlus Needed

This is the easiest way to run and see results immediately.

### Step 1 — Clone the Repository

```bash
git clone https://github.com/yahavan/me325_decentralized_hvac_control.git
cd me325_decentralized_hvac_control
git checkout Thinujan-Thillaiselvan-patch-1
```

### Step 2 — Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> Only `numpy` is required for the standalone simulation.

### Step 4 — Run the Simulation

```bash
python simulate.py
```

This simulates **365 days** of HVAC operation for all 5 zones using first-principles physics (thermal ODE, moisture ODE, CO₂ ODE).  
Output is written to `out/sim_data.json`.

### Step 5 — View the Dashboard

Open `dashboard.html` in any web browser (Chrome recommended).

```
# Windows — double-click dashboard.html, or:
start dashboard.html

# macOS
open dashboard.html
```

You will see an **interactive full-year dashboard** with:
- Zone temperature, humidity, and CO₂ trends
- AHU supply air temperature and outdoor air flow
- Day-by-day playback controls

---

## ⚡ Advanced — Run with EnergyPlus

`main.py` connects Python controllers directly into EnergyPlus via the Python API for high-fidelity simulation.

### Requirements
- [EnergyPlus v26.1.0](https://energyplus.net/downloads) installed at `C:\EnergyPlusV26-1-0\`
- EnergyPlus Python API on your `PYTHONPATH`

### Setup

```powershell
# Windows PowerShell — add EnergyPlus API to path
$env:PYTHONPATH = "C:\EnergyPlusV26-1-0"
```

### Run

```bash
python main.py
```

This runs the full IDF model with decentralised zone controllers writing actuator values at every timestep.  
Output CSV: `out/control_log.csv`

---

## 🏢 Zone Configuration

| Zone   | Use              | Area  | Cool SP | Max Flow | Controller |
|--------|-----------------|-------|---------|----------|------------|
| Zone 1 | Open Office      | 80 m² | 24 °C   | 0.50 m³/s | PI |
| Zone 2 | Private Offices  | 50 m² | 24 °C   | 0.35 m³/s | PI |
| Zone 3 | Conference Room  | 60 m² | 23 °C   | 0.55 m³/s | PI |
| Zone 4 | Server Room      | 40 m² | 21 °C   | 0.60 m³/s | PI (min floor) |
| Zone 5 | Reception        | 30 m² | 24 °C   | 0.35 m³/s | PI |

All setpoints and gains are editable in [`config.py`](config.py).

---

## 🌤️ Climate Model

The simulation uses real Colombo, Sri Lanka climate data:
- **SW Monsoon** (May–Sep): Hot & very humid (~29 °C, w = 0.022 kg/kg)
- **NE Monsoon** (Oct–Jan): Warm & humid (~28 °C)
- **Inter-monsoon** (Feb–Apr): Hot & drier (~28.5 °C)

Diurnal temperature variation (min 05:00, max 14:00) is modelled per month.

---

## 📊 Analyse Results

After running `simulate.py`:

```bash
python analyse_results.py
```

Generates summary statistics and plots for energy use, comfort violations, and CO₂ levels.

---

## 📋 Requirements

```
numpy==2.4.6
```

> EnergyPlus Python API is only needed for `main.py` (not for `simulate.py` or the dashboard).

---

## 📄 Report

See [`docs/Teamventus MID Evaluation_Final.pdf`](docs/) for the full project report.

---

## 👤 Authors

- **Thinujan Thillaiselvan** — ME325, University of Peradeniya
- Supervisor: Dr. Yahavan (yahavan)

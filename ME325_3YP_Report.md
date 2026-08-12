# ME325 — Decentralised HVAC Control for a Multi-Zone Commercial Building

## A Third-Year Project (3YP) Report

### Python-Driven EnergyPlus Co-simulation with PI Control, Adaptive Gain Scheduling, and Extended Kalman Filtering

---

**Department of Mechanical Engineering**
**University of Moratuwa**
**Sri Lanka**

**Course:** ME325 — Third-Year Project
**Project Title:** Decentralised HVAC Control for a Multi-Zone VAV System with Python-Driven EnergyPlus Co-Simulation
**Climate Context:** Colombo, Sri Lanka (Hot-Humid Tropical — Köppen: Aw)

---

## Declaration

I/We declare that this report is my/our own work and has not been submitted in any form for another degree or diploma at any university or other institution of tertiary education. Information derived from the published or unpublished work of others has been acknowledged in the text and a list of references is given.

---

\pagebreak

## Abstract

This report presents the design, implementation, and evaluation of a **decentralised Heating, Ventilation, and Air Conditioning (HVAC) control scheme** for a five-zone commercial office building in Colombo, Sri Lanka. The building physics are simulated using the **EnergyPlus** whole-building energy simulation engine, while the control logic is executed in **Python** via the EnergyPlus Python API, establishing a real-time co-simulation framework.

The control architecture follows a **hierarchical two-level paradigm**. At the lower level, each of the five thermal zones operates an independent **Proportional-Integral (PI) controller** with **conditional-integration anti-windup** and **time-of-day adaptive gain scheduling**. Each zone controller has access only to its own sensor measurements — temperature, humidity ratio, relative humidity, and CO₂ concentration — making it a truly decentralised agent. At the upper level, a lightweight **Air Handling Unit (AHU) coordinator** aggregates zone-level requests to resolve system-wide decisions: the supply air temperature setpoint and the outdoor air mass flow rate for demand-controlled ventilation.

An **Extended Kalman Filter (EKF)** framework is designed per zone to simultaneously filter noisy sensor readings and estimate hidden physical parameters — thermal capacitance, envelope heat transfer coefficient, moisture capacitance, CO₂ generation rate, and occupancy-related heat gains — that cannot be directly measured.

The system is configured for a **Variable Air Volume (VAV)** air distribution topology with a single DX cooling coil AHU serving all five zones through individual constant-volume air terminals whose mass flow rates are modulated by Python at every simulation timestep. The building model is subjected to a full annual simulation using Colombo weather data, representing a hot-humid tropical climate where year-round cooling and aggressive dehumidification are the dominant HVAC challenges.

Results are logged to a comprehensive CSV file and analysed through three complementary tools: a terminal-based statistical report, dark-themed Matplotlib visualisations, and a premium interactive web dashboard with glassmorphism design and real-time playback capabilities.

**Keywords:** Decentralised HVAC control, EnergyPlus co-simulation, PI control, anti-windup, adaptive gains, Extended Kalman Filter, VAV system, demand-controlled ventilation, building energy simulation, tropical climate.

---

\pagebreak

## Table of Contents

1. [Introduction](#1-introduction)
    1. [Background and Motivation](#11-background-and-motivation)
    2. [Problem Statement](#12-problem-statement)
    3. [Objectives](#13-objectives)
    4. [Scope and Limitations](#14-scope-and-limitations)
    5. [Report Organisation](#15-report-organisation)
2. [Literature Review](#2-literature-review)
    1. [HVAC Systems in Commercial Buildings](#21-hvac-systems-in-commercial-buildings)
    2. [Centralised vs. Decentralised Control](#22-centralised-vs-decentralised-control)
    3. [PI and PID Control in HVAC](#23-pi-and-pid-control-in-hvac)
    4. [Anti-Windup Strategies](#24-anti-windup-strategies)
    5. [Gain Scheduling and Adaptive Control](#25-gain-scheduling-and-adaptive-control)
    6. [State Estimation and the Extended Kalman Filter](#26-state-estimation-and-the-extended-kalman-filter)
    7. [Building Energy Simulation and Co-Simulation](#27-building-energy-simulation-and-co-simulation)
    8. [Demand-Controlled Ventilation](#28-demand-controlled-ventilation)
    9. [Tropical Climate HVAC Challenges](#29-tropical-climate-hvac-challenges)
3. [System Architecture](#3-system-architecture)
    1. [Overall Architecture Diagram](#31-overall-architecture-diagram)
    2. [Hierarchical Control Levels](#32-hierarchical-control-levels)
    3. [Data Flow and Timestep Loop](#33-data-flow-and-timestep-loop)
    4. [Technology Stack](#34-technology-stack)
4. [Building Model — EnergyPlus IDF](#4-building-model--energyplus-idf)
    1. [Building Geometry and Orientation](#41-building-geometry-and-orientation)
    2. [Zone Definitions and Intended Use](#42-zone-definitions-and-intended-use)
    3. [Construction Materials and Envelope Properties](#43-construction-materials-and-envelope-properties)
    4. [Fenestration and Glazing](#44-fenestration-and-glazing)
    5. [Internal Loads — People, Lighting, Equipment](#45-internal-loads--people-lighting-equipment)
    6. [Infiltration Model](#46-infiltration-model)
    7. [Occupancy Schedules](#47-occupancy-schedules)
    8. [HVAC System Configuration](#48-hvac-system-configuration)
    9. [Air Loop and AHU Components](#49-air-loop-and-ahu-components)
    10. [DX Cooling Coil Characteristics](#410-dx-cooling-coil-characteristics)
    11. [Variable Volume Fan](#411-variable-volume-fan)
    12. [Zone Air Terminals](#412-zone-air-terminals)
    13. [Outdoor Air System and Controller](#413-outdoor-air-system-and-controller)
    14. [CO₂ Contaminant Balance](#414-co₂-contaminant-balance)
    15. [Simulation Parameters and Output Requests](#415-simulation-parameters-and-output-requests)
5. [Climate Context — Colombo, Sri Lanka](#5-climate-context--colombo-sri-lanka)
    1. [Köppen Classification and Climate Overview](#51-köppen-classification-and-climate-overview)
    2. [Weather File and Design Days](#52-weather-file-and-design-days)
    3. [Implications for HVAC Design](#53-implications-for-hvac-design)
6. [Control System Design](#6-control-system-design)
    1. [Control Philosophy — Decentralised with Centralised Coordination](#61-control-philosophy--decentralised-with-centralised-coordination)
    2. [Zone-Level PI Controller](#62-zone-level-pi-controller)
    3. [Anti-Windup — Conditional Integration](#63-anti-windup--conditional-integration)
    4. [Adaptive Gain Scheduling](#64-adaptive-gain-scheduling)
    5. [Humidity-Based Supply Air Temperature Request](#65-humidity-based-supply-air-temperature-request)
    6. [Zone 4 Server Room Override](#66-zone-4-server-room-override)
    7. [AHU Coordinator — Supply Air Temperature](#67-ahu-coordinator--supply-air-temperature)
    8. [AHU Coordinator — Outdoor Air and DCV](#68-ahu-coordinator--outdoor-air-and-dcv)
    9. [Controller Tuning and Parameter Selection](#69-controller-tuning-and-parameter-selection)
7. [State Estimation — Extended Kalman Filter](#7-state-estimation--extended-kalman-filter)
    1. [Purpose and Motivation](#71-purpose-and-motivation)
    2. [Augmented State Vector](#72-augmented-state-vector)
    3. [Physical Sub-Model Equations](#73-physical-sub-model-equations)
    4. [Hidden Parameter Dynamics — Random Walk](#74-hidden-parameter-dynamics--random-walk)
    5. [EKF Prediction Step](#75-ekf-prediction-step)
    6. [EKF Update Step — Measurement Fusion](#76-ekf-update-step--measurement-fusion)
    7. [Initialisation and Covariance Tuning](#77-initialisation-and-covariance-tuning)
    8. [Implementation Status and Graceful Fallback](#78-implementation-status-and-graceful-fallback)
8. [Occupancy Modelling](#8-occupancy-modelling)
    1. [IDF Schedule Mirror](#81-idf-schedule-mirror)
    2. [Per-Zone Peak Occupancy](#82-per-zone-peak-occupancy)
    3. [Schedule Definition](#83-schedule-definition)
9. [Software Implementation](#9-software-implementation)
    1. [Project File Structure](#91-project-file-structure)
    2. [Configuration Module — config.py](#92-configuration-module--configpy)
    3. [Orchestrator — main.py](#93-orchestrator--mainpy)
    4. [Zone Controller Base Class — zone_controller.py](#94-zone-controller-base-class--zone_controllerpy)
    5. [Zone-Specific Controllers](#95-zone-specific-controllers)
    6. [AHU Coordinator — ahu.py](#96-ahu-coordinator--ahupy)
    7. [Extended Kalman Filter — ekf.py](#97-extended-kalman-filter--ekfpy)
    8. [Occupancy Mirror — occupancy.py](#98-occupancy-mirror--occupancypy)
    9. [Data Logging Mechanism](#99-data-logging-mechanism)
10. [EnergyPlus Co-Simulation Interface](#10-energyplus-co-simulation-interface)
    1. [Python API Overview](#101-python-api-overview)
    2. [Handle Resolution](#102-handle-resolution)
    3. [Callback Registration](#103-callback-registration)
    4. [Sensor Reading](#104-sensor-reading)
    5. [Actuator Writing](#105-actuator-writing)
    6. [Warm-Up Handling](#106-warm-up-handling)
11. [Output, Analysis, and Visualisation](#11-output-analysis-and-visualisation)
    1. [Control Log CSV Schema](#111-control-log-csv-schema)
    2. [Terminal Analysis Script — analyse_results.py](#112-terminal-analysis-script--analyse_resultspy)
    3. [Matplotlib Visualisation — visualize.py](#113-matplotlib-visualisation--visualizepy)
    4. [Interactive Web Dashboard — dashboard.html](#114-interactive-web-dashboard--dashboardhtml)
12. [Performance Metrics and Compliance Criteria](#12-performance-metrics-and-compliance-criteria)
    1. [Temperature Comfort](#121-temperature-comfort)
    2. [Indoor Air Quality — CO₂](#122-indoor-air-quality--co₂)
    3. [Humidity Compliance](#123-humidity-compliance)
    4. [Airflow Utilisation](#124-airflow-utilisation)
    5. [AHU Command Analysis](#125-ahu-command-analysis)
13. [Results and Discussion](#13-results-and-discussion)
    1. [Annual Simulation Overview](#131-annual-simulation-overview)
    2. [Temperature Control Performance](#132-temperature-control-performance)
    3. [Humidity Management](#133-humidity-management)
    4. [CO₂ Control and Ventilation](#134-co₂-control-and-ventilation)
    5. [Zone 4 Server Room Behaviour](#135-zone-4-server-room-behaviour)
    6. [Adaptive Gains — Day/Night Behaviour](#136-adaptive-gains--daynight-behaviour)
    7. [AHU Coordinator Effectiveness](#137-ahu-coordinator-effectiveness)
    8. [Energy Implications](#138-energy-implications)
14. [Conclusions](#14-conclusions)
15. [Future Work and Recommendations](#15-future-work-and-recommendations)
16. [References](#16-references)
17. [Appendices](#17-appendices)
    1. [Appendix A — Equation Quick Reference](#appendix-a--equation-quick-reference)
    2. [Appendix B — Full Source Code Listings](#appendix-b--full-source-code-listings)
    3. [Appendix C — EnergyPlus IDF Highlights](#appendix-c--energyplus-idf-highlights)
    4. [Appendix D — How to Run the Project](#appendix-d--how-to-run-the-project)

---

\pagebreak

# 1. Introduction

## 1.1 Background and Motivation

Heating, Ventilation, and Air Conditioning (HVAC) systems are responsible for a significant portion of global energy consumption, accounting for approximately 40–60% of total energy use in commercial buildings. In tropical climates such as Sri Lanka, where cooling is required virtually year-round and humidity management is a persistent challenge, the efficiency of HVAC control strategies directly impacts both energy costs and occupant comfort.

Traditional HVAC control in commercial buildings relies on centralised control systems where a single Building Management System (BMS) processes all sensor data and computes all actuator commands. While this approach provides a global view of the system, it suffers from several disadvantages:

- **Single point of failure:** A central controller failure disables the entire building's climate control.
- **Communication overhead:** All sensor data must be routed to a single processing node, creating bandwidth bottlenecks.
- **Scalability limitations:** Adding new zones or modifying the building layout requires reprogramming the central controller.
- **Complexity:** The control algorithm must simultaneously consider all zones, making the problem computationally expensive for large buildings.

Decentralised control offers an alternative paradigm where each zone operates as an independent agent, making local control decisions based only on locally available measurements. This approach provides:

- **Fault tolerance:** Failure of one zone's controller does not affect other zones.
- **Scalability:** New zones can be added without modifying existing controllers.
- **Simplicity:** Each controller is a small, well-defined unit with clear inputs and outputs.
- **Reduced communication:** Inter-zone communication is minimised or eliminated.

However, purely decentralised control can lead to conflicts at the system level — for example, when multiple zones have competing requirements for the shared Air Handling Unit (AHU). This project addresses this challenge by implementing a **hierarchical two-level control architecture** that combines the benefits of decentralised zone-level control with lightweight centralised coordination at the AHU level.

## 1.2 Problem Statement

Design and implement a decentralised HVAC control system for a five-zone commercial office building in Colombo, Sri Lanka, that:

1. Maintains each zone's air temperature within an acceptable comfort band around a 24°C cooling setpoint.
2. Controls indoor air quality by keeping CO₂ concentrations below ASHRAE 62.1 limits through demand-controlled ventilation.
3. Manages humidity levels in a hot-humid tropical climate through intelligent supply air temperature management.
4. Operates each zone controller independently with access only to its own sensor readings.
5. Resolves system-level conflicts through a lightweight AHU coordinator.
6. Provides a framework for online state and parameter estimation using Extended Kalman Filtering.
7. Demonstrates the system through a full annual EnergyPlus simulation with comprehensive data logging and visualisation.

## 1.3 Objectives

The specific objectives of this project are:

1. **Model** a five-zone commercial office building in EnergyPlus with realistic geometry, construction materials, internal loads, occupancy schedules, and a VAV air distribution system for the Colombo, Sri Lanka climate.

2. **Design** a decentralised PI control scheme with anti-windup and adaptive gain scheduling for zone-level temperature regulation, where each controller operates solely on local sensor measurements.

3. **Implement** a lightweight AHU coordinator that aggregates zone-level requests to determine the system-wide supply air temperature setpoint and outdoor air flow rate.

4. **Develop** the mathematical framework for a per-zone Extended Kalman Filter (EKF) to estimate hidden physical parameters (thermal capacitance, heat transfer coefficient, moisture capacitance, CO₂ generation rate, and occupancy heat gains) from noisy sensor data.

5. **Establish** a Python-EnergyPlus co-simulation framework using the EnergyPlus Python API for real-time actuator override at every simulation timestep.

6. **Evaluate** the control system's performance over a full annual simulation using metrics for temperature comfort, CO₂ compliance, humidity management, and airflow utilisation.

7. **Visualise** results through multiple channels: terminal-based statistical analysis, dark-themed Matplotlib plots, and a premium interactive web dashboard.

## 1.4 Scope and Limitations

**In scope:**
- Five-zone commercial building model for Colombo, Sri Lanka
- Decentralised PI control with anti-windup and adaptive gains
- AHU coordinator for SAT and OA flow management
- EKF framework design and mathematical formulation
- Full annual simulation with 10-minute timestep resolution
- Comprehensive data logging and multi-format visualisation

**Limitations:**
- The EKF implementation is currently a scaffold — the prediction and update steps have the correct mathematical formulation but the Jacobian computations and physics functions are pending full integration. The system falls back gracefully to PI-only control.
- The building model uses simplified geometry (rectangular zones, adiabatic internal walls between zones).
- The DX cooling coil and fan are modelled with typical performance curves but are not optimised for a specific manufacturer's equipment.
- Energy cost calculations and economic analysis are not included.
- The project does not include Model Predictive Control (MPC) or reinforcement learning, though these are identified as future work.

## 1.5 Report Organisation

This report is organised into seventeen chapters and four appendices:

- **Chapter 1** introduces the project motivation, problem statement, and objectives.
- **Chapter 2** reviews relevant literature on HVAC control, decentralised systems, PI control, Kalman filtering, and building simulation.
- **Chapter 3** presents the overall system architecture.
- **Chapter 4** details the EnergyPlus building model.
- **Chapter 5** describes the Colombo climate context.
- **Chapter 6** covers the control system design in detail.
- **Chapter 7** presents the EKF state estimator design.
- **Chapter 8** describes the occupancy model.
- **Chapter 9** documents the software implementation.
- **Chapter 10** explains the EnergyPlus co-simulation interface.
- **Chapter 11** covers output logging, analysis, and visualisation.
- **Chapter 12** defines performance metrics and compliance criteria.
- **Chapter 13** presents results and discussion.
- **Chapter 14** draws conclusions.
- **Chapter 15** suggests future work.
- **Chapter 16** lists references.
- **Chapter 17** contains appendices with equations, source code, and setup instructions.

---

\pagebreak

# 2. Literature Review

## 2.1 HVAC Systems in Commercial Buildings

HVAC systems in commercial buildings serve the fundamental purpose of maintaining thermal comfort, indoor air quality, and humidity levels for building occupants. The American Society of Heating, Refrigerating and Air-Conditioning Engineers (ASHRAE) defines thermal comfort as "that condition of mind which expresses satisfaction with the thermal environment" (ASHRAE Standard 55). Modern HVAC systems must balance multiple competing objectives: occupant comfort, energy efficiency, indoor air quality, and equipment longevity.

In commercial buildings, the most common HVAC distribution topology is the **Variable Air Volume (VAV) system**, which conditions a central stream of air at a controlled temperature and varies the volume of air supplied to each zone based on its cooling or heating demand. VAV systems offer significant energy savings over Constant Air Volume (CAV) systems because they reduce fan energy during partial-load conditions, which represent the majority of operating hours.

A typical VAV system consists of:

- **Air Handling Unit (AHU):** Contains the cooling coil (typically a direct expansion (DX) coil or chilled water coil), heating coil, supply fan, return fan, and outdoor air mixing section.
- **Supply Air Ductwork:** Distributes conditioned air from the AHU to individual zones.
- **VAV Terminal Units:** Located at each zone, these modulate the volume of supply air entering the zone using a damper controlled by the zone thermostat.
- **Return Air System:** Collects air from each zone and returns it to the AHU for reconditioning or exhaust.

The Supply Air Temperature (SAT) is typically controlled by the AHU's cooling coil to maintain a constant setpoint (e.g., 13°C). Zone temperature is regulated by varying the airflow through the VAV terminal, rather than by changing the supply air temperature.

In the context of this project, the air distribution uses **constant-volume terminals** whose mass flow rates are overridden by Python at every timestep — effectively creating a "Python-modulated VAV" system where the flow modulation is handled entirely by the external control logic rather than by the EnergyPlus built-in controllers.

## 2.2 Centralised vs. Decentralised Control

Control architectures for multi-zone HVAC systems can be broadly categorised into three paradigms:

### 2.2.1 Centralised Control

In a centralised architecture, a single controller receives all sensor measurements from all zones and computes all actuator commands. This approach has the advantage of a global view — the controller can optimise across zones simultaneously, accounting for inter-zone thermal coupling and shared resources like the AHU. However, centralised control suffers from:

- **Computational complexity:** The optimisation problem grows combinatorially with the number of zones.
- **Communication requirements:** All sensor data must be routed to a central point.
- **Single point of failure:** Controller failure disables all zones.
- **Inflexibility:** Adding or removing zones requires modifying the central algorithm.

### 2.2.2 Fully Decentralised Control

In a fully decentralised architecture, each zone has its own controller that operates independently with no inter-zone communication. This is the simplest approach and is highly fault-tolerant and scalable. However, without any coordination, conflicts can arise when multiple zones share resources. For example, if Zone A needs very cold supply air for dehumidification while Zone B needs warmer air to avoid over-cooling, a fully decentralised system cannot resolve this conflict.

### 2.2.3 Hierarchical (Distributed) Control

Hierarchical control combines elements of both centralised and decentralised approaches. Local controllers handle zone-level regulation independently (using only local measurements), while a lightweight coordinator at the system level resolves shared-resource conflicts. This architecture offers:

- **Fast local response:** Zone controllers react immediately to local disturbances.
- **Conflict resolution:** The coordinator ensures system-wide consistency.
- **Scalability:** Adding zones only requires adding local controllers; the coordinator uses simple aggregation rules.
- **Fault tolerance:** If the coordinator fails, zones can continue operating with their last-known setpoints.

**This project adopts the hierarchical approach**, with PI controllers at the zone level and a rule-based AHU coordinator at the system level.

## 2.3 PI and PID Control in HVAC

Proportional-Integral-Derivative (PID) controllers remain the workhorse of industrial control, and HVAC is no exception. Despite the availability of more advanced control strategies (MPC, reinforcement learning, fuzzy logic), over 90% of installed HVAC controllers in practice are PID or PI controllers due to their simplicity, robustness, and well-understood tuning procedures.

The continuous-time PI control law is:

```
u(t) = Kp · e(t) + Ki · ∫₀ᵗ e(τ) dτ
```

Where:
- `u(t)` is the control output (e.g., supply air mass flow rate)
- `e(t) = T_zone(t) - T_setpoint` is the error signal
- `Kp` is the proportional gain (instantaneous response to error)
- `Ki` is the integral gain (eliminates steady-state error)

For digital implementation, the integral is computed using discrete summation:

```
Iₖ = Iₖ₋₁ + eₖ · Δt
uₖ = Kp · eₖ + Ki · Iₖ
```

In HVAC applications, the derivative term is often omitted (PI instead of PID) because:

1. Temperature dynamics are inherently slow, with time constants on the order of minutes to hours.
2. Derivative action amplifies sensor noise, which is particularly problematic for temperature sensors with limited resolution.
3. The integral term is sufficient to eliminate steady-state error in most HVAC applications.

The proportional gain `Kp` determines how aggressively the controller responds to the current error. A higher `Kp` gives faster response but can lead to oscillations. The integral gain `Ki` eliminates steady-state offset by accumulating error over time, but excessive `Ki` can cause overshoot and slow recovery from disturbances.

## 2.4 Anti-Windup Strategies

A critical challenge in PI/PID control arises when the actuator saturates — i.e., when the computed control output exceeds the physical limits of the actuator. In a VAV system, the airflow cannot exceed the maximum capacity of the terminal unit, and it cannot go below zero. When the actuator is saturated, the integral term continues to accumulate error, a phenomenon known as **integrator windup**.

Integrator windup causes two problems:

1. **Delayed response:** When the error changes sign (e.g., the zone cools below setpoint after being too warm), the controller must "unwind" the accumulated integral before it can respond, causing significant delay.
2. **Overshoot:** The large accumulated integral causes excessive overshoot in the opposite direction.

Several anti-windup strategies exist:

### 2.4.1 Clamping (Conditional Integration)

The integrator update is only accepted if the output is not saturated, or if saturation is in the opposite direction to the integrator growth. This is the strategy implemented in this project:

```python
saturated_high = (u_raw >= max_mdot) and (err > 0)
saturated_low  = (u_raw <= 0.0)     and (err < 0)

if not (saturated_high or saturated_low):
    self._integral = integral_candidate
# else: freeze integrator at current value
```

This approach is simple, requires no additional parameters, and effectively prevents windup in both directions.

### 2.4.2 Back-Calculation

The difference between the saturated and unsaturated output is fed back to the integrator through a gain `1/Tt`. This method is more sophisticated but requires tuning the tracking time constant `Tt`.

### 2.4.3 Integrator Limiting

The integral state is simply clamped to a fixed range. This is the simplest approach but can be conservative if the limits are set too tight.

The **conditional integration (clamping) method** was chosen for this project because it requires no additional tuning parameters, is straightforward to implement, and provides robust anti-windup behaviour across all operating conditions.

## 2.5 Gain Scheduling and Adaptive Control

Fixed-gain PI controllers are tuned for a specific operating point. However, HVAC systems experience widely varying conditions over the course of a day — from zero-occupancy night conditions to full-occupancy peak periods with high solar gains. A controller tuned for peak conditions may be too aggressive during light-load periods, and vice versa.

**Gain scheduling** addresses this by adjusting the controller gains based on known operating conditions. In this project, the gains are scheduled based on the time of day and whether it is a weekday or weekend:

| Period | Time | Kp Multiplier | Ki Multiplier | Rationale |
|---|---|---|---|---|
| Night | 00:00–07:30 | 0.50 | 0.40 | Low thermal loads, slow dynamics |
| Ramp-up | 07:30–09:00 | 1.50 | 1.00 | Fight the occupancy arrival surge |
| Peak | 09:00–17:30 | 1.00 | 1.00 | Baseline (config values) |
| Ramp-down | 17:30–19:00 | 1.10 | 1.00 | Slight boost during departure |
| After-hours | 19:00–24:00 | 0.70 | 0.60 | Near-empty, reduced response |
| Weekend (all day) | — | 0.50 | 0.40 | Minimal occupancy throughout |

This is a **scheduled adaptive scheme** — the adaptation is based on known time-of-day patterns rather than on measured system parameters. True adaptive control, where gains are adjusted based on online identification of plant parameters, is the domain of the EKF component of this project.

## 2.6 State Estimation and the Extended Kalman Filter

In many control applications, the full system state is not directly measurable. In HVAC, we can typically measure zone temperature, humidity, and CO₂ concentration, but we cannot directly measure parameters such as:

- **Thermal capacitance** of the zone air and furnishings
- **Overall heat transfer coefficient** of the building envelope
- **Moisture capacitance** of the zone
- **CO₂ generation rate** per occupant
- **Occupancy-related internal heat gains**

These parameters are essential for model-based control strategies (such as MPC) and for detecting faults or anomalies in building operation.

The **Kalman Filter** provides an optimal state estimate for linear systems with Gaussian noise. For nonlinear systems — such as the thermal, moisture, and CO₂ dynamics of a building zone — the **Extended Kalman Filter (EKF)** linearises the system equations at each timestep using Jacobian matrices.

### EKF Algorithm Summary

**Prediction step:**
```
x⁻ = f(xₖ₋₁, uₖ, Δt)           [nonlinear state transition]
F  = ∂f/∂x at xₖ₋₁              [Jacobian of f]
P⁻ = F · Pₖ₋₁ · Fᵀ + Q         [predicted covariance]
```

**Update step:**
```
y  = zₖ - h(x⁻)                 [innovation / measurement residual]
S  = H · P⁻ · Hᵀ + R            [innovation covariance]
K  = P⁻ · Hᵀ · S⁻¹              [Kalman gain]
xₖ = x⁻ + K · y                  [posterior state estimate]
Pₖ = (I - K·H) · P⁻             [posterior covariance]
```

The EKF's strength lies in its ability to jointly estimate observable states and hidden parameters by constructing an **augmented state vector** that includes both.

## 2.7 Building Energy Simulation and Co-Simulation

**EnergyPlus** is the U.S. Department of Energy's flagship whole-building energy simulation engine. It models:

- Building envelope heat transfer (conduction, convection, radiation)
- Solar gains through windows and opaque surfaces
- Internal heat gains from people, lighting, and equipment
- HVAC equipment performance (coils, fans, boilers, chillers)
- Air distribution and zone mass balance
- Contaminant transport (CO₂, moisture)
- Daylighting and natural ventilation

EnergyPlus uses a **heat balance method** for zone temperature calculation, solving the zone energy balance equation at each timestep:

```
C_z · dT_z/dt = Q_conv_surfaces + Q_internal + Q_system + Q_infiltration + Q_inter_zone
```

The **EnergyPlus Python API** (introduced in EnergyPlus v9.3) allows external programs to interact with the simulation in real time. This co-simulation capability enables:

- Reading any output variable (temperature, humidity, CO₂, etc.)
- Writing to actuators (mass flow rates, setpoints, schedules)
- Registering callbacks that fire at each timestep

This project uses the **`callback_end_zone_timestep_after_zone_reporting`** callback point, which fires after EnergyPlus has computed all zone states for the current timestep but before advancing to the next. This ensures that the Python controller sees fresh sensor data and can write actuator commands that take effect at the next timestep.

## 2.8 Demand-Controlled Ventilation

ASHRAE Standard 62.1 specifies minimum ventilation rates for acceptable indoor air quality. Traditional HVAC systems provide a fixed outdoor air flow rate based on design occupancy, which wastes energy during periods of low occupancy. **Demand-Controlled Ventilation (DCV)** adjusts the outdoor air flow rate based on actual occupancy, typically using CO₂ concentration as a proxy for occupancy level.

The rationale is simple: occupied zones generate CO₂ from human metabolism. Higher CO₂ concentrations indicate higher occupancy, requiring more outdoor air for dilution. The outdoor-to-indoor CO₂ differential (typically 400 ppm outdoor to an 800-1000 ppm indoor limit) provides a convenient control signal.

In this project, the DCV strategy uses the worst-case (highest) CO₂ concentration among all zones to determine the outdoor air fraction:

```
φ_OA = clamp((c_max - c_outdoor) / (c_setpoint - c_outdoor), 0.15, 1.0)
```

The minimum outdoor air fraction of 15% ensures code compliance even when CO₂ levels are low, and the maximum of 100% provides full outdoor air ventilation when CO₂ levels reach or exceed the setpoint.

## 2.9 Tropical Climate HVAC Challenges

Colombo, Sri Lanka, presents several unique challenges for HVAC design:

1. **Year-round cooling:** With outdoor temperatures typically between 27–33°C and virtually no heating load, the HVAC system operates in cooling mode 365 days per year. This means there is no seasonal changeover, and the cooling coil, fan, and ventilation system must be sized for continuous operation.

2. **High latent loads:** Outdoor relative humidity in Colombo typically ranges from 70–85%. This means a significant portion of the cooling load is latent (moisture removal) rather than sensible (temperature reduction). The DX cooling coil must dehumidify the supply air in addition to cooling it, requiring lower supply air temperatures than would be needed in a dry climate.

3. **No economiser benefit:** In temperate climates, an economiser cycle can use cool outdoor air for free cooling when outdoor temperatures are below the supply air setpoint. In Colombo, outdoor temperatures are almost always above the supply air setpoint, so the economiser provides no benefit. This means all cooling must come from the mechanical cooling coil.

4. **Persistent dehumidification demand:** The humidity-override SAT request (12°C when RH exceeds target vs. 14°C otherwise) is expected to be frequently triggered in Colombo's climate, requiring the DX coil to operate at lower temperatures for latent heat removal.

---

\pagebreak

# 3. System Architecture

## 3.1 Overall Architecture Diagram

The system architecture consists of two major layers: the EnergyPlus simulation engine (which models the building physics) and the Python orchestrator (which implements the control logic). These layers communicate at every simulation timestep through the EnergyPlus Python API.

```
+------------------------------------------------------------------+
|                        EnergyPlus Engine                          |
|   (MultiZone_VAV_PythonControl.idf + Colombo.epw)                |
|                                                                   |
|  Zone 1 --+                                                       |
|  Zone 2 --+  VAV Air Terminals  -->  AHU (DX Coil + OA Damper)   |
|  Zone 3 --+                                                       |
|  Zone 4 --+                                                       |
|  Zone 5 --+                                                       |
+-------------------------+-----------------------------------------+
                          | Python API callback (every zone timestep)
                          v
+------------------------------------------------------------------+
|                       Orchestrator (main.py)                      |
|                                                                   |
|  READ sensors -->  [Zone 1 PI + EKF]  --+                        |
|                    [Zone 2 PI + EKF]  --+                        |
|                    [Zone 3 PI + EKF]  --+-->  AHU Coordinator    |
|                    [Zone 4 PI + EKF]  --+          |              |
|                    [Zone 5 PI + EKF]  --+          |              |
|                                                    v              |
|  WRITE actuators <-------------- sat_sp, oa_flow                 |
|  (mdot per zone, coolSP per zone)                                |
|                                                    |              |
|  LOG --> out/control_log.csv                                     |
+------------------------------------------------------------------+
```

## 3.2 Hierarchical Control Levels

The control architecture operates on two distinct levels:

### Level 1 — Zone-Level Control (Decentralised)

Each of the five zones has its own independent controller instance. The controller receives only its own zone's measurements:

- Zone Mean Air Temperature `T` [°C]
- Zone Air Humidity Ratio `w` [kg/kg]
- Zone Air Relative Humidity `RH` [%]
- Zone Air CO₂ Concentration `c` [ppm]

From these local measurements, the controller computes a **request** to the AHU:

- Desired supply mass flow rate `mdot` [kg/s]
- Desired supply air temperature `t_sup_req` [°C]
- Current CO₂ level `co2` [ppm]
- Local cooling setpoint `cool_sp` [°C]

The zone controller has no knowledge of what other zones are doing — this is what makes the scheme **truly decentralised**.

### Level 2 — AHU Coordination (Centralised, Lightweight)

The AHU coordinator is the only component that sees all zone requests simultaneously. It performs two simple aggregation computations:

1. **Supply Air Temperature:** Takes the minimum (most demanding) SAT request across all zones.
2. **Outdoor Air Flow:** Scales OA proportionally to the worst CO₂ zone.

The coordinator is intentionally "lightweight" — it uses simple min/max rules rather than optimisation, keeping the computational cost negligible and the logic transparent.

## 3.3 Data Flow and Timestep Loop

At every EnergyPlus zone reporting timestep, the following sequence executes inside the `Orchestrator.on_timestep()` callback:

| Step | Action | Data |
|---|---|---|
| 0 | **OCCUPANCY** | Mirror the IDF schedule for logging (no actuator write) |
| 1 | **READ** | Get T, w, RH, CO₂ from all zones via EnergyPlus API |
| 2 | **LOCAL CONTROL** | Each ZoneController runs its PI law independently |
| 3 | **COORDINATE** | AHU coordinator aggregates requests → SAT, OA flow |
| 4 | **WRITE** | Write mdot, cooling SP per zone; SAT, OA flow to AHU |
| 5 | **LOG** | Append all data to control_log.csv |

This loop executes at every simulation timestep (every 10 minutes of simulated time with 6 timesteps per hour), resulting in approximately 52,560 timesteps for a full annual simulation.

## 3.4 Technology Stack

| Layer | Technology | Version / Notes |
|---|---|---|
| Building physics | EnergyPlus | v25.2 (IDF model) |
| Control logic | Python 3 | `pyenergyplus` API |
| State estimation | NumPy | EKF matrices and linear algebra |
| Data analysis | pandas | CSV processing and statistics |
| Plotting | matplotlib | Dark-themed interactive plots |
| Web dashboard | HTML/CSS/JS + Chart.js | Glassmorphism UI, playback controls |
| Weather data | EPW file | Colombo, Sri Lanka (TMY) |

---

\pagebreak

# 4. Building Model — EnergyPlus IDF

The EnergyPlus building model is defined in the Input Data File (IDF) `MultiZone_VAV_PythonControl.idf`. This chapter provides a comprehensive description of every aspect of the model.

## 4.1 Building Geometry and Orientation

The building is modelled as a single-storey rectangular structure with a total footprint of 25 m × 8 m = 200 m², divided into five contiguous zones arranged side-by-side along the east-west axis. Each zone is 5 m wide, 8 m deep, and 3 m high, giving a per-zone floor area of 40 m² and volume of 120 m³.

The building's north axis is set to 0° (true north), meaning:

- The **south-facing** walls (containing windows) face the equator — appropriate for the Northern Hemisphere position of Colombo (latitude 6.9°N).
- All five zones have south-facing exterior walls with windows, north-facing exterior walls without windows, and the east/west walls are either exterior (for end zones) or interior adiabatic partitions (between adjacent zones).

**Zone layout (west to east):**

```
+--------+--------+--------+--------+--------+
| Zone 1 | Zone 2 | Zone 3 | Zone 4 | Zone 5 |
| Open   | Private| Conf.  | Server | Recept.|
| Office | Offices| Room   | Room   | ion    |
+--------+--------+--------+--------+--------+
  0-5m     5-10m   10-15m   15-20m   20-25m    (x-axis)
         8m deep (y-axis), 3m high (z-axis)
```

## 4.2 Zone Definitions and Intended Use

Each zone has a distinct function that drives its thermal load profile, occupancy pattern, and control requirements:

| Zone | Use | Floor Area | Volume | Peak People | Notes |
|---|---|---|---|---|---|
| Zone 1 | Open Office | 40 m² | 120 m³ | 8 | Standard office, moderate density |
| Zone 2 | Private Offices | 40 m² | 120 m³ | 4 | Lower occupancy, individual rooms |
| Zone 3 | Conference Room | 40 m² | 120 m³ | 12 | Highest occupancy density, intermittent |
| Zone 4 | Server Room | 40 m² | 120 m³ | 1 | 24/7 high equipment load, tight control |
| Zone 5 | Reception | 40 m² | 120 m³ | 5 | Public-facing, moderate traffic |

## 4.3 Construction Materials and Envelope Properties

The building envelope is defined with the following material layers:

### Exterior Wall Construction (outside to inside)

| Layer | Material | Thickness (m) | Conductivity (W/m·K) | Density (kg/m³) | Specific Heat (J/kg·K) |
|---|---|---|---|---|---|
| 1 | Stucco | 0.025 | 0.72 | 1856 | 840 |
| 2 | Concrete 200mm | 0.200 | 1.95 | 2240 | 900 |
| 3 | Insulation | 0.075 | 0.049 | 265 | 836 |
| 4 | Gypsum Board | 0.016 | 0.16 | 800 | 1090 |

The overall wall R-value (excluding film coefficients) is approximately:
```
R = 0.025/0.72 + 0.200/1.95 + 0.075/0.049 + 0.016/0.16
R ≈ 0.035 + 0.103 + 1.531 + 0.100 = 1.769 m²·K/W
U ≈ 0.57 W/(m²·K)
```

This is a reasonably well-insulated wall for a tropical climate, where the primary concern is keeping heat out rather than in.

### Interior Wall Construction

Interior walls between zones use a simple double-gypsum construction (two layers of 16mm gypsum board). In the model, these walls are set to **adiabatic boundary conditions**, meaning there is no heat transfer between adjacent zones through the partition walls. This simplification isolates each zone's thermal behaviour, consistent with the decentralised control philosophy where each zone is treated as an independent thermal system.

### Roof Construction (outside to inside)

| Layer | Material | Thickness (m) | Conductivity (W/m·K) |
|---|---|---|---|
| 1 | Roof Membrane | 0.010 | 0.16 |
| 2 | Roof Insulation | 0.120 | 0.049 |
| 3 | Concrete 200mm | 0.200 | 1.95 |

### Floor Construction

The floor is a 100mm concrete slab with an adiabatic boundary condition (ground-floor on slab assumed to have negligible heat exchange).

## 4.4 Fenestration and Glazing

Each zone has a single south-facing window modelled using a simplified glazing system:

| Property | Value |
|---|---|
| U-factor | 3.0 W/(m²·K) |
| Solar Heat Gain Coefficient (SHGC) | 0.40 |
| Visible Transmittance | 0.60 |

Each window is 3 m wide × 1.5 m high = 4.5 m², centred on the south wall. The window-to-wall ratio is 4.5 / (5 × 3) = 30%, a typical value for commercial buildings.

The SHGC of 0.40 indicates moderate solar control — appropriate for a tropical climate where excessive solar gains would increase cooling loads. Lower SHGC values (0.25–0.30) would provide better solar control but would reduce natural daylight.

## 4.5 Internal Loads — People, Lighting, Equipment

### People

People are defined using a fixed number per zone with an activity level of 120 W per person and a radiant fraction of 0.30 (30% radiant, 70% convective). The CO₂ generation rate is set to 3.82 × 10⁻⁸ m³/(s·W) — the standard ASHRAE value for office work.

| Zone | Peak People | People/m² | Metabolic Rate |
|---|---|---|---|
| Zone 1 (Open Office) | 8 | 0.20 | 120 W/person |
| Zone 2 (Private Offices) | 4 | 0.10 | 120 W/person |
| Zone 3 (Conference Room) | 12 | 0.30 | 120 W/person |
| Zone 4 (Server Room) | 1 | 0.025 | 120 W/person |
| Zone 5 (Reception) | 5 | 0.125 | 120 W/person |

### Lighting

Lighting is modelled using a Watts/Area method, following the Office Lighting schedule:

| Zone | Power Density (W/m²) | Peak Power (W) |
|---|---|---|
| Zone 1 | 10 | 400 |
| Zone 2 | 9 | 360 |
| Zone 3 | 8 | 320 |
| Zone 4 | 6 | 240 |
| Zone 5 | 11 | 440 |

The return air fraction is 0.42 (42% of lighting heat goes to the return air plenum), and the radiant fraction is 0.18.

### Equipment

| Zone | Power Density (W/m²) | Schedule | Peak Power (W) |
|---|---|---|---|
| Zone 1 | 12 | Office Equipment | 480 |
| Zone 2 | 10 | Office Equipment | 400 |
| Zone 3 | 5 | Office Equipment | 200 |
| Zone 4 | **60** | **Server Equipment** | **2,400** |
| Zone 5 | 6 | Office Equipment | 240 |

**Zone 4 (Server Room)** has by far the highest equipment load at 60 W/m² on a nearly constant schedule (90% fraction, 24/7). This creates a consistent, high-density heat load that requires constant cooling — justifying the minimum-airflow safety override in the Zone 4 controller.

## 4.6 Infiltration Model

All zones have identical infiltration rates of 0.0003 m³/(s·m²) using the `Flow/Area` method. This represents a moderately airtight commercial building. The infiltration coefficients use only the constant term (A=1.0, B=C=D=0), meaning the infiltration rate is constant regardless of wind speed or temperature difference.

## 4.7 Occupancy Schedules

The IDF defines several schedules that drive the internal loads:

### Office Occupancy (Fraction)

```
Weekdays / SummerDesignDay:
    Until 08:00 → 0.05    (5% — early arrivals / security)
    Until 18:00 → 1.00    (100% — full occupancy)
    Until 24:00 → 0.05    (5% — late workers / cleaning)

All Other Days (weekends, holidays):
    Until 24:00 → 0.00    (0% — building empty)
```

### Office Lighting (Fraction)

```
Weekdays / SummerDesignDay:
    Until 08:00 → 0.10
    Until 18:00 → 0.90
    Until 24:00 → 0.10

All Other Days:
    Until 24:00 → 0.05
```

### Office Equipment (Fraction)

```
Weekdays / SummerDesignDay:
    Until 08:00 → 0.30
    Until 18:00 → 0.90
    Until 24:00 → 0.30

All Other Days:
    Until 24:00 → 0.20
```

### Server Equipment (Constant)

```
Always → 0.90    (90% — servers run 24/7 at near-full load)
```

## 4.8 HVAC System Configuration

The HVAC system is a single-loop Variable Air Volume (VAV) configuration:

```
Outdoor Air ──> OA Mixer ──> DX Cooling Coil ──> Variable Volume Fan ──> Zone Splitter
                                                                              |
                                                                   +----+----+----+----+
                                                                   |    |    |    |    |
                                                                 Z1   Z2   Z3   Z4   Z5
                                                               Term  Term  Term  Term  Term
                                                                   |    |    |    |    |
                                                                   +----+----+----+----+
                                                                              |
                                                                        Zone Mixer ──> Return
```

## 4.9 Air Loop and AHU Components

The air loop `VAV Air Loop` consists of a single supply branch containing (in series):

1. **Outdoor Air System (`VAV OA System`)**: Mixes outdoor air with return air through an outdoor air mixer.
2. **DX Cooling Coil System (`VAV DX Coil System`)**: Cools and dehumidifies the mixed air.
3. **Variable Volume Fan (`VAV Supply Fan`)**: Drives the conditioned air through the ductwork.

## 4.10 DX Cooling Coil Characteristics

The DX cooling coil is modelled using `Coil:Cooling:DX:SingleSpeed` with:

- **Gross Rated Cooling COP:** 3.5 W/W (typical for a good-quality DX unit)
- **All capacities autosized** based on design day conditions
- **Performance curves** (biquadratic and quadratic) that adjust capacity and efficiency based on entering air conditions and part-load ratio

The performance curves are:

- **CapFT (Capacity as a function of temperature):** Biquadratic function of entering wet-bulb and outdoor dry-bulb temperatures, valid for 17–22°C entering and 13–46°C outdoor.
- **CapFFF (Capacity as a function of flow fraction):** Linear function: Cap = 0.8 + 0.2·FF.
- **EIRFT (Energy Input Ratio as a function of temperature):** Biquadratic function capturing efficiency variation with conditions.
- **EIRFFF (EIR as a function of flow fraction):** Quadratic: EIR = 1.1552 - 0.1808·FF + 0.0256·FF².
- **PLF (Part Load Fraction):** Linear degradation: PLF = 0.85 + 0.15·PLR.

## 4.11 Variable Volume Fan

The supply fan is modelled as `Fan:VariableVolume` with:

| Parameter | Value |
|---|---|
| Fan Total Efficiency | 0.70 |
| Pressure Rise | 600 Pa |
| Maximum Air Flow Rate | Autosized |
| Minimum Flow Fraction | 0.25 (25% of max) |
| Motor Efficiency | 0.90 |
| Motor in Airstream | 100% |

The fan power consumption follows a variable-speed power curve with five coefficients:
```
FanPower = C₁ + C₂·FF + C₃·FF² + C₄·FF³ + C₅·FF⁴
```
Where the coefficients are: 0.0407, 0.08804, -0.07292, 0.9433, 0.0.

## 4.12 Zone Air Terminals

Each zone is served by a `AirTerminal:SingleDuct:ConstantVolume:NoReheat` terminal. The maximum air flow rates match the configuration in `config.py`:

| Terminal | Zone | Max Flow (m³/s) | Max mdot (kg/s) |
|---|---|---|---|
| Zone 1 Air Terminal | Zone 1 | 0.50 | 0.60 |
| Zone 2 Air Terminal | Zone 2 | 0.35 | 0.42 |
| Zone 3 Air Terminal | Zone 3 | 0.55 | 0.66 |
| Zone 4 Air Terminal | Zone 4 | 0.60 | 0.72 |
| Zone 5 Air Terminal | Zone 5 | 0.35 | 0.42 |

**Important note:** These terminals are "ConstantVolume" from EnergyPlus's perspective, but the Python controller overrides their mass flow rate at every timestep via the `AirTerminal:SingleDuct:ConstantVolume:NoReheat / Mass Flow Rate` actuator. This effectively creates a Python-modulated variable-volume system.

## 4.13 Outdoor Air System and Controller

The outdoor air controller (`VAV OA Controller`) is configured with:

- **Economizer Control Type:** NoEconomizer — appropriate for Colombo where outdoor air is almost always warmer than the supply air setpoint.
- **Minimum/Maximum OA Flow:** Both autosized.
- **Lockout:** NoLockout — OA is always available.
- **Minimum Limit Type:** FixedMinimum.

Python overrides the actual OA mass flow rate at each timestep via the `Outdoor Air Controller / Air Mass Flow Rate` actuator.

## 4.14 CO₂ Contaminant Balance

The `ZoneAirContaminantBalance` object enables CO₂ tracking with:

- **Generic Contaminant Simulation:** Yes (enables CO₂ balance)
- **Outdoor CO₂ Schedule:** Constant at 400 ppm (ambient background)
- **Generic Contaminant:** No (not tracking other contaminants)

CO₂ generation comes from the `People` objects, which have a CO₂ generation rate of 3.82 × 10⁻⁸ m³/(s·W). This standard ASHRAE value means each person at 120 W metabolic rate generates approximately 4.584 × 10⁻⁶ m³/s of CO₂ — consistent with typical breathing rates during office work.

## 4.15 Simulation Parameters and Output Requests

### Simulation Control

| Parameter | Value |
|---|---|
| Timesteps per Hour | 6 (10-minute intervals) |
| Run Period | January 1 to December 31 (full year) |
| Start Day | Monday |
| Zone Sizing | Yes |
| System Sizing | Yes |
| Sizing Oversize Factor | 1.2 (20% safety margin) |
| Warmup Days | Min 6, Max 25 |
| Temperature Convergence | 0.40°C |
| Loads Convergence | 0.04 |

### Output Variables Requested

The IDF requests a comprehensive set of output variables at the Timestep reporting frequency:

**Zone-level (controller inputs):**
- Zone Mean Air Temperature
- Zone Air Humidity Ratio
- Zone Air Relative Humidity
- Zone Air CO₂ Concentration

**Thermostat setpoints (verification):**
- Zone Thermostat Cooling Setpoint Temperature
- Zone Thermostat Heating Setpoint Temperature

**System node data (airflow verification):**
- System Node Mass Flow Rate
- System Node Temperature
- System Node Relative Humidity
- System Node Humidity Ratio
- System Node Setpoint Temperature
- System Node CO₂ Concentration

**Outdoor conditions:**
- Site Outdoor Air Drybulb Temperature
- Site Outdoor Air Humidity Ratio
- Air System Outdoor Air Mass Flow Rate

**Energy surrogates:**
- Fan Electricity Rate
- Cooling Coil Electricity Rate
- Cooling Coil Total/Sensible/Latent Cooling Rate

---

\pagebreak

# 5. Climate Context — Colombo, Sri Lanka

## 5.1 Köppen Classification and Climate Overview

Colombo, Sri Lanka is classified under the Köppen climate classification as **Aw — Tropical Savanna Climate** (sometimes also classified as Am — Tropical Monsoon). Key characteristics:

| Parameter | Value |
|---|---|
| Latitude | 6.90°N |
| Longitude | 79.86°E |
| Elevation | 7 m above sea level |
| Time Zone | UTC+5.5 |
| Annual Mean Temperature | ~27°C |
| Hottest Month Mean | ~28–29°C (April) |
| Coolest Month Mean | ~26°C (January) |
| Annual Rainfall | ~2,400 mm |
| Dominant Monsoons | Southwest (May–Sep), Northeast (Dec–Feb) |

## 5.2 Weather File and Design Days

The simulation uses an EPW (EnergyPlus Weather) file for Colombo, Sri Lanka, containing Typical Meteorological Year (TMY) hourly data for 8,760 hours.

### Design Day Specifications

**Cooling Design Day (April 21 — SummerDesignDay):**

| Parameter | Value |
|---|---|
| Maximum Dry-Bulb Temperature | 33.0°C |
| Daily Temperature Range | 7.0°C |
| Wet-Bulb Temperature | 27.0°C |
| Wind Speed | 3.0 m/s |
| Barometric Pressure | 101,200 Pa |
| Solar Model | ASHRAE Clear Sky, Clearness = 1.0 |

**Heating Design Day (January 21 — WinterDesignDay):**

| Parameter | Value |
|---|---|
| Maximum Dry-Bulb Temperature | 22.0°C |
| Daily Temperature Range | 0.0°C (constant) |
| Wet-Bulb Temperature | 21.0°C |
| Wind Speed | 3.0 m/s |

Note that even the "heating" design day has a temperature of 22°C — still warm enough that the building may need cooling depending on internal loads. This illustrates why heating is not a concern in Colombo.

## 5.3 Implications for HVAC Design

The Colombo climate creates several specific requirements for the HVAC system:

1. **Year-round cooling mode:** The system operates in cooling mode 365 days per year. There is no seasonal changeover, and the heating setpoint (18°C) is effectively never active.

2. **High latent loads:** The design wet-bulb temperature of 27°C (at 33°C dry-bulb) indicates a humidity ratio of approximately 0.020 kg/kg. The supply air must be cooled to approximately 12–14°C to condense moisture and achieve adequate dehumidification, making the SAT humidity-override frequently active.

3. **No economiser benefit:** Since outdoor temperatures typically exceed 27°C, the outdoor air cannot provide free cooling. The DX coil must handle the full cooling load mechanically. The outdoor air controller is set to `NoEconomizer` accordingly.

4. **Consistent solar loads:** Near the equator, solar gains are relatively consistent year-round with only minor seasonal variation. The design day solar model uses ASHRAE Clear Sky with clearness = 1.0.

5. **Diurnal temperature swing:** The 7°C daily temperature range means the building's thermal mass provides some passive cooling benefit during the early morning hours, but this benefit is limited.

---

\pagebreak

# 6. Control System Design

## 6.1 Control Philosophy — Decentralised with Centralised Coordination

The fundamental design decision is that **each zone controller is a fully independent agent**. Zone 1's controller has no knowledge of Zone 2's temperature, humidity, or control actions. This decentralisation is achieved by passing only local sensor readings to each controller in the `step()` method.

The AHU coordinator is the sole point where information from multiple zones converges. It receives the list of zone requests (each containing the desired mass flow rate, SAT request, and CO₂ level) and computes two system-level commands: the AHU supply air temperature setpoint and the outdoor air mass flow rate.

This architecture was chosen for several reasons:

- **Practical relevance:** In real buildings, zone controllers are often physically separate devices (thermostats, VAV controllers) that communicate with the AHU controller through a BACnet or LonWorks network. Designing the software architecture to mirror this physical separation ensures that the control logic could be directly deployed to real hardware.
- **Testability:** Each zone controller can be unit-tested in isolation with simulated inputs.
- **Extensibility:** Adding a new zone requires only adding a new controller instance; the existing controllers are unaffected.

## 6.2 Zone-Level PI Controller

### Error Definition

The error signal is defined as the difference between the current zone temperature and the cooling setpoint:

```
e(t) = T_zone(t) - T_setpoint
```

This sign convention means:
- **Positive error:** Zone is too warm → need more cooling → increase airflow.
- **Negative error:** Zone is too cold → need less cooling → decrease airflow.
- **Zero error:** Zone is at setpoint → maintain current airflow.

### Continuous PI Law

```
u(t) = Kp · e(t) + Ki · ∫₀ᵗ e(τ) dτ
```

Where:
- `Kp` [kg/s per °C] — proportional gain
- `Ki` [kg/s per (°C·s)] — integral gain
- `u(t)` — desired mass flow rate [kg/s]

### Discrete Implementation

The controller operates at the EnergyPlus simulation timestep (Δt seconds):

```
Iₖ = Iₖ₋₁ + eₖ · Δt                           [integral update]
u_raw = Kp_eff · eₖ + Ki_eff · Iₖ               [raw PI output]
mdot = clamp(u_raw, 0, mdot_max)                [actuator limiting]
```

Where `Kp_eff` and `Ki_eff` are the effective gains after applying the gain scheduling multipliers (see Section 6.4).

## 6.3 Anti-Windup — Conditional Integration

The anti-windup strategy uses **conditional integration (clamping)**:

```python
# Tentatively compute the candidate integral
integral_candidate = self._integral + err * dt

# Compute raw PI output with candidate
u_raw = kp_eff * err + ki_eff * integral_candidate

# Check for saturation in the direction of error
saturated_high = (u_raw >= max_mdot) and (err > 0)
saturated_low  = (u_raw <= 0.0)     and (err < 0)

# Only accept the integral update if NOT saturated in error direction
if not (saturated_high or saturated_low):
    self._integral = integral_candidate
# else: freeze the integrator at its current value
```

**Anti-windup logic in plain language:**

| Condition | Error | Output | Integrator |
|---|---|---|---|
| Zone too hot, output at max | `e > 0` | `u ≥ max` | **Freeze** — don't accumulate more positive error |
| Zone too hot, output below max | `e > 0` | `u < max` | Accept — room to increase |
| Zone too cold, output at zero | `e < 0` | `u ≤ 0` | **Freeze** — don't accumulate more negative error |
| Zone too cold, output above zero | `e < 0` | `u > 0` | Accept — room to decrease |
| Zone at setpoint | `e ≈ 0` | Any | Accept — minimal change |

## 6.4 Adaptive Gain Scheduling

The controller uses time-of-day gain scheduling to adapt to the building's predictable daily load profile. The scheduling is implemented in the `_gain_multiplier()` method:

### Weekday Schedule

```python
if 7.5 <= hour < 9.0:      # Pre-occupancy ramp
    return 1.50, 1.00       # Aggressive Kp to fight arrival surge
elif 9.0 <= hour < 17.5:    # Peak occupancy
    return 1.00, 1.00       # Baseline gains
elif 17.5 <= hour < 19.0:   # Evening changeover
    return 1.10, 1.00       # Slight Kp boost during departure
elif 19.0 <= hour:           # After hours
    return 0.70, 0.60       # Reduced — near-empty zone
else:                        # Night (00:00-07:30)
    return 0.50, 0.40       # Minimal — slow dynamics
```

### Weekend Schedule

```python
return 0.50, 0.40  # All day — near-zero occupancy
```

### Zone 4 Server Room Exception

The Server Room controller overrides `_gain_multiplier()` to always return `(1.0, 1.0)` because the server load is constant 24/7, and the controller must maintain the same responsiveness at all times.

### Rationale for Multiplier Values

- **Night (0.50, 0.40):** With no occupants and no equipment running (except Zone 4), thermal loads are minimal. The building's thermal mass provides significant damping, and the zone temperature changes very slowly. Reduced gains prevent unnecessary hunting and energy waste from small temperature fluctuations.

- **Ramp-up (1.50, 1.00):** At 08:00, the occupancy jumps from 5% to 100%, introducing a sudden heat load. The controller needs aggressive proportional action (1.5× Kp) to quickly increase airflow and prevent the temperature from overshooting. The integral gain is kept at baseline to avoid fast integral buildup that could cause post-ramp overshoot.

- **Peak (1.00, 1.00):** During full occupancy, the gains use the baseline values from `config.py`. These are the values the controller was primarily tuned for.

- **Ramp-down (1.10, 1.00):** At 18:00, occupancy drops back to 5%. The slight Kp boost (1.1×) helps the controller transition smoothly as the thermal load decreases. Without this boost, the controller might over-cool the zone as the suddenly-reduced load allows the cooling system to bring the temperature well below setpoint before the controller can reduce airflow.

- **After-hours (0.70, 0.60):** Similar to night mode but with slightly higher gains, accounting for residual equipment heat and potential late workers.

## 6.5 Humidity-Based Supply Air Temperature Request

Each zone controller adjusts its supply air temperature request based on local relative humidity. Rather than using a simple bang-bang switch (which would cause oscillations), the implementation uses a **proportional sliding scale**:

```python
rh_err = meas["rh"] - self.cfg["rh_target"]   # +ve = too humid
t_sup_req = max(12.0, min(14.0, 13.0 - 0.2 * rh_err))
```

This creates a linear interpolation:

| Humidity Condition | RH Error | SAT Request |
|---|---|---|
| 5% below target (very dry) | -5% | 14.0°C (back off, minimal dehumidification) |
| At target | 0% | 13.0°C (neutral) |
| 5% above target (too humid) | +5% | 12.0°C (maximum dehumidification) |

The proportional approach with gain 0.2°C per %RH error avoids the saw-tooth oscillations that would occur with a bang-bang switch at the RH target threshold. This is particularly important in Colombo's humid climate where RH frequently hovers near the target value.

### Dehumidification Physics

Lower supply air temperatures cause more moisture condensation on the DX cooling coil because the air is cooled below its dew point. At 12°C supply air temperature, the air leaves the coil nearly saturated at a low humidity ratio, providing aggressive dehumidification. At 14°C, less moisture is removed, conserving cooling energy when dehumidification is not needed.

## 6.6 Zone 4 Server Room Override

The Server Room has a unique requirement: its high equipment load (60 W/m², 24/7) means that even a brief loss of cooling airflow could cause dangerous temperature rises. The Zone 4 controller enforces a **minimum airflow floor**:

```python
def step(self, meas, dt, hour=12.0, is_weekday=True):
    req = super().step(meas, dt, hour, is_weekday)  # Run standard PI
    min_mdot = 0.30 * self.cfg["max_mdot"]           # 30% of maximum
    req["mdot"] = max(req["mdot"], min_mdot)          # Enforce floor
    return req
```

This ensures that even if the PI controller computes zero airflow (e.g., during warmup or when the zone is briefly below setpoint), at least 30% of maximum flow (0.30 × 0.72 = 0.216 kg/s) is always maintained. This is a safety-critical override that prevents thermal runaway in the server room.

## 6.7 AHU Coordinator — Supply Air Temperature

The AHU supplies a single stream of conditioned air to all zones. The supply air temperature must be low enough to satisfy the most demanding zone:

```python
sat = max(SAT_FLOOR, min(r["t_sup_req"] for r in requests))
```

Where `SAT_FLOOR = 10°C` prevents excessive over-cooling that could cause condensation problems in the ductwork.

**Operating logic:**
- If any zone requests 12°C (high humidity), the AHU supplies at 12°C.
- If all zones request 14°C (dry conditions), the AHU supplies at 14°C.
- The SAT never goes below 10°C regardless of zone requests.

Zones that receive air colder than they need can compensate by reducing their mass flow rate through the PI controller, maintaining their temperature setpoint while receiving the benefit of dehumidification from the colder supply air.

## 6.8 AHU Coordinator — Outdoor Air and DCV

The outdoor air flow rate is determined by a demand-controlled ventilation (DCV) strategy based on CO₂ levels:

```python
co2_max = max(r["co2"] for r in requests)           # worst zone
tot_mdot = sum(r["mdot"] for r in requests)          # total supply flow
oa_frac = (co2_max - OUTDOOR_CO2) / (CO2_SETPOINT - OUTDOOR_CO2)
oa_frac = clamp(oa_frac, 0.15, 1.0)                 # min 15%, max 100%
oa_flow = oa_frac * tot_mdot                         # OA mass flow rate
```

| CO₂ Level | OA Fraction | Interpretation |
|---|---|---|
| 400 ppm (outdoor) | 0.0 → clamped to 0.15 | Minimum ventilation (code compliance) |
| 500 ppm | 0.25 | Quarter outdoor air |
| 600 ppm | 0.50 | Half outdoor air |
| 700 ppm | 0.75 | Three-quarter outdoor air |
| 800 ppm (setpoint) | 1.00 | Full outdoor air |
| >800 ppm | Clamped to 1.00 | Maximum OA — CO₂ above target |

The 15% minimum ensures compliance with ventilation codes (ASHRAE 62.1) at all times, even when the building is unoccupied and CO₂ levels are near outdoor ambient.

## 6.9 Controller Tuning and Parameter Selection

The PI controller gains were selected through a combination of engineering judgment and iterative simulation testing:

| Zone | Kp (kg/s per °C) | Ki (kg/s per (°C·s)) | Rationale |
|---|---|---|---|
| Zone 1 (Open Office) | 0.25 | 0.008 | Moderate — balanced response |
| Zone 2 (Private Offices) | 0.25 | 0.008 | Same as Zone 1 — similar load profile |
| Zone 3 (Conference Room) | 0.30 | 0.010 | Higher — handles occupancy swings |
| Zone 4 (Server Room) | 0.35 | 0.012 | Highest — tight control for critical equipment |
| Zone 5 (Reception) | 0.25 | 0.008 | Same as Zone 1 — moderate loads |

**Tuning considerations:**

- Higher `Kp` gives faster initial response but can cause oscillations if too aggressive.
- Higher `Ki` eliminates steady-state error faster but can cause overshoot and slow recovery.
- Zone 3 (Conference Room) has higher gains because it experiences the largest and most sudden occupancy changes (0 to 12 people).
- Zone 4 (Server Room) has the highest gains because its constant high load requires tight temperature control, and the equipment can be damaged by even brief temperature excursions.

---

\pagebreak

# 7. State Estimation — Extended Kalman Filter

## 7.1 Purpose and Motivation

The Extended Kalman Filter serves two purposes in this project:

1. **Sensor Fusion and Noise Filtering:** Real temperature, humidity, and CO₂ sensors have measurement noise. The EKF provides optimal (minimum variance) estimates of the true zone states by combining noisy measurements with a physics-based prediction model.

2. **Hidden Parameter Estimation:** Several parameters that strongly affect zone thermal behaviour cannot be directly measured:
   - The zone's effective thermal capacitance changes with furniture, stored materials, and internal furnishings.
   - The building envelope's heat transfer coefficient degrades over time as insulation ages.
   - Occupancy-related heat gains are unknown without separate people-counting systems.
   - The CO₂ generation rate per occupant varies with activity level.

By including these parameters in an augmented state vector, the EKF can estimate them online from the available sensor data.

## 7.2 Augmented State Vector

The EKF state vector for each zone contains 8 elements:

```
x = [ T,   w,   c,              ← measured/observable states
      C_T, U, C_w, k, q_occ ]   ← hidden parameters
```

| Index | Symbol | Description | Units | Measurable? |
|---|---|---|---|---|
| 0 | T | Zone mean air temperature | °C | Yes |
| 1 | w | Zone humidity ratio | kg/kg | Yes |
| 2 | c | Zone CO₂ concentration | ppm | Yes |
| 3 | C_T | Thermal capacitance | J/K | No |
| 4 | U | Overall heat transfer coefficient | W/K | No |
| 5 | C_w | Moisture capacitance | kg | No |
| 6 | k | CO₂ generation coefficient | ppm·m³/s | No |
| 7 | q_occ | Occupancy internal heat gain | W | No |

## 7.3 Physical Sub-Model Equations

The state transition function `f(x, u, Δt)` encodes three coupled energy/mass balance equations:

### Thermal Energy Balance

```
C_T · dT/dt = ṁ · cₚ · (T_sup - T) - U · (T - T_out) + q_int + q_occ
```

Discrete form:
```
T_{k+1} = T_k + (Δt/C_T) · [ṁ · cₚ · (T_sup - T_k) - U · (T_k - T_out) + q_int + q_occ]
```

Where:
- `ṁ` = supply air mass flow rate [kg/s]
- `cₚ` = specific heat of air ≈ 1005 J/(kg·K)
- `T_sup` = supply air temperature [°C]
- `T_out` = outdoor temperature [°C]
- `q_int` = known internal heat gains (lighting + equipment) [W]
- `q_occ` = estimated occupancy heat gain [W] (EKF parameter)

### Moisture Mass Balance

```
C_w · dw/dt = ṁ · (w_sup - w) + ṁ_occ · w_gen
```

Discrete form:
```
w_{k+1} = w_k + (Δt/C_w) · [ṁ · (w_sup - w_k) + moisture_generation]
```

Where:
- `w_sup` = supply air humidity ratio [kg/kg]
- `w_gen` = moisture generation from occupants [kg/s]

### CO₂ Mass Balance

```
V · dc/dt = ṁ · (c_sup - c) + k · N_occ
```

Discrete form:
```
c_{k+1} = c_k + (Δt/V) · [ṁ · (c_sup - c_k) + k · N_occ]
```

Where:
- `V` = zone volume [m³]
- `c_sup` = supply air CO₂ concentration [ppm]
- `k` = CO₂ generation coefficient [ppm·m³/s per person]
- `N_occ` = estimated number of occupants (derived from `q_occ / metabolic_rate`)

## 7.4 Hidden Parameter Dynamics — Random Walk

The five hidden parameters `(C_T, U, C_w, k, q_occ)` are modelled with random-walk dynamics:

```
θ_{k+1} = θ_k + η_k    where η_k ~ N(0, Q_θ)
```

This means the parameters are expected to be approximately constant from one timestep to the next, with small random perturbations. The process noise covariance `Q_θ` controls how quickly the EKF allows parameters to change:

- Small `Q_θ`: Parameters change very slowly — the filter is "confident" in its current estimate and resistant to change.
- Large `Q_θ`: Parameters can change rapidly — the filter is "uncertain" and responsive to new measurements.

The random-walk model is appropriate because:
- Thermal capacitance changes slowly as building contents change.
- Envelope U-value changes very slowly (seasonal degradation, weathering).
- CO₂ generation rate changes with occupancy and activity level (over minutes to hours).
- Occupancy heat gains change with the building schedule (over hours).

## 7.5 EKF Prediction Step

```
x⁻ = f(xₖ₋₁, uₖ, Δt)           [nonlinear state prediction]
F  = ∂f/∂x |_{xₖ₋₁}             [8×8 Jacobian matrix]
P⁻ = F · Pₖ₋₁ · Fᵀ + Q          [predicted covariance]
```

The Jacobian matrix `F` is an 8×8 matrix where each element `F[i,j] = ∂f_i/∂x_j`. For the thermal balance equation (row 0), the partial derivatives are:

```
∂f_T/∂T    = 1 - Δt/C_T · (ṁ·cₚ + U)
∂f_T/∂C_T  = -Δt/C_T² · [ṁ·cₚ·(T_sup - T) - U·(T - T_out) + q_int + q_occ]
∂f_T/∂U    = -Δt/C_T · (T - T_out)
∂f_T/∂q_occ = Δt/C_T
```

Similar partial derivatives exist for the moisture and CO₂ equations, and the hidden parameters have identity dynamics (∂θ_{k+1}/∂θ_k = 1).

## 7.6 EKF Update Step — Measurement Fusion

```
z = [T_measured, w_measured, c_measured]    [3-element measurement vector]

H = [I_{3×3} | 0_{3×5}]                    [3×8 measurement matrix]

y = z - H · x⁻                             [innovation / residual]
S = H · P⁻ · Hᵀ + R                        [3×3 innovation covariance]
K = P⁻ · Hᵀ · S⁻¹                          [8×3 Kalman gain]
xₖ = x⁻ + K · y                            [8-element posterior estimate]
Pₖ = (I₈ - K · H) · P⁻                     [8×8 posterior covariance]
```

The measurement matrix `H` is a 3×8 matrix that simply selects the first three state elements (T, w, c) — the observable states. The hidden parameters are estimated indirectly through their effect on the observable state dynamics.

## 7.7 Initialisation and Covariance Tuning

The initial values and covariance matrices are set for a typical 40 m² zone:

### Initial State `x₀`

| Variable | Initial Value | Rationale |
|---|---|---|
| T | 24.0°C | At cooling setpoint |
| w | 0.010 kg/kg | Moderate humidity |
| c | 500 ppm | Between outdoor (400) and setpoint (800) |
| C_T | 3×10⁵ J/K | Typical for zone air + light furnishings |
| U | 50 W/K | Moderate envelope losses |
| C_w | 2×10⁴ kg | Moisture capacity of zone air |
| k | 0.01 ppm·m³/s | Conservative CO₂ generation |
| q_occ | 0 W | Assume initially empty |

### Initial Covariance P₀ (diagonal)

```
P₀ = diag([0.5, 1e-6, 100, 1e9, 100, 1e6, 1e-3, 1.0])
```

The large diagonal values for hidden parameters (e.g., 10⁹ for C_T) reflect high initial uncertainty — the filter will quickly converge to more accurate estimates based on measurement data.

### Process Noise Q (diagonal)

```
Q = diag([0.01, 1e-9, 1.0, 1e6, 1.0, 1e3, 1e-5, 0.1])
```

### Measurement Noise R (diagonal)

```
R = diag([0.1, 1e-7, 25.0])
```

These values reflect typical sensor accuracy:
- Temperature: ±0.3°C (σ² = 0.1)
- Humidity ratio: ±0.0003 kg/kg (σ² = 1×10⁻⁷)
- CO₂: ±50 ppm (σ² = 25)

## 7.8 Implementation Status and Graceful Fallback

The EKF is structurally defined in `estimation/ekf.py` — the class, state vector, covariance matrices, predict/update method signatures, and default initialisation function are all in place. However, the Jacobian computation and physics functions inside `predict()` and `update()` are currently scaffold stubs that raise `NotImplementedError`.

The orchestrator handles this gracefully:

```python
try:
    self.ekf.update([meas["T"], meas["w"], meas["co2"]], self._last_u, dt)
    est = self.ekf.params.tolist()
except NotImplementedError:
    est = None
```

When `est = None`, the PI controller operates normally using raw sensor measurements. This design ensures the system is fully functional with PI-only control, and the EKF can be integrated incrementally without breaking existing functionality.

---

\pagebreak

# 8. Occupancy Modelling

## 8.1 IDF Schedule Mirror

The `occupancy.py` module replicates the EnergyPlus `Office Occupancy` schedule in Python for logging purposes. This is a **read-only mirror** — it does not write to any EnergyPlus actuator. EnergyPlus drives the actual occupancy heat and CO₂ gains from its own internal schedule.

The purpose of mirroring the schedule is to include the expected occupancy count in the control log CSV, enabling post-simulation analysis of how the controller responds to occupancy changes.

## 8.2 Per-Zone Peak Occupancy

| Zone | Max People | Occupancy Density |
|---|---|---|
| Zone 1 (Open Office) | 8 | 0.20 people/m² |
| Zone 2 (Private Offices) | 4 | 0.10 people/m² |
| Zone 3 (Conference Room) | 12 | 0.30 people/m² |
| Zone 4 (Server Room) | 1 | 0.025 people/m² |
| Zone 5 (Reception) | 5 | 0.125 people/m² |

## 8.3 Schedule Definition

The `_office_occupancy_fraction()` function implements:

```python
def _office_occupancy_fraction(hour, day_of_week_ep):
    is_weekday = 2 <= day_of_week_ep <= 6  # EP: 1=Sun, 2=Mon ... 7=Sat
    
    if not is_weekday:
        return 0.0
    
    if hour < 8.0:
        return 0.05
    elif hour < 18.0:
        return 1.00
    else:
        return 0.05
```

The `ZoneOccupancy` class wraps this function and converts the fraction to an absolute people count:

```python
people_count = max_people * fraction
```

For example, Zone 3 (Conference Room) with 12 max people:
- Weekday 07:00 → 12 × 0.05 = 0.6 people
- Weekday 10:00 → 12 × 1.00 = 12.0 people
- Saturday 14:00 → 12 × 0.00 = 0.0 people

---

\pagebreak

# 9. Software Implementation

## 9.1 Project File Structure

```
3YP/
│
├── main.py                        # Driver: EnergyPlus API + Orchestrator loop
├── config.py                      # Zone parameters & global constants
├── visualize.py                   # Interactive Matplotlib plots (3 figures)
├── analyse_results.py             # Terminal performance summary report
├── occupancy.py                   # IDF occupancy schedule mirror
├── dashboard.html                 # Interactive web dashboard (glassmorphism UI)
├── requirements.txt               # Python dependencies (numpy)
│
├── controllers/
│   ├── zone_controller.py         # Base PI + EKF + anti-windup + adaptive gains
│   ├── ahu.py                     # AHU coordinator (SAT + OA rules)
│   ├── zone1.py                   # Zone 1 - Open Office (standard)
│   ├── zone2.py                   # Zone 2 - Private Offices (standard)
│   ├── zone3.py                   # Zone 3 - Conference Room (standard)
│   ├── zone4.py                   # Zone 4 - Server Room (min-flow override)
│   └── zone5.py                   # Zone 5 - Reception (standard)
│
├── estimation/
│   └── ekf.py                     # Extended Kalman Filter (scaffold)
│
├── model/
│   ├── MultiZone_VAV_PythonControl.idf   # 5-zone EnergyPlus building model
│   ├── 1Zone_SriLanka_Controlled.idf     # Single-zone prototype (legacy)
│   └── Colombo.epw                       # Weather: Colombo, Sri Lanka
│
├── out/                           # Simulation outputs (auto-generated)
│   ├── control_log.csv            # Python-written control log
│   ├── eplusout.eso               # EnergyPlus binary output
│   ├── eplusout.err               # Simulation warnings/errors
│   ├── eplustbl.htm               # EnergyPlus HTML summary
│   └── ... (other output files)
│
└── docs/
    ├── EnergyPlus_Model_Overview.md.pdf
    └── Teamventus MID Evaluation_Final.pdf
```

## 9.2 Configuration Module — config.py

The `config.py` module centralises all system parameters, making it easy to adjust zone configurations without modifying control logic.

**Key constants:**

| Constant | Value | Description |
|---|---|---|
| `RHO_AIR` | 1.2 kg/m³ | Air density for flow conversion |
| `CO2_SETPOINT` | 800 ppm | Central coordinator CO₂ target |
| `OUTDOOR_CO2` | 400 ppm | Background outdoor CO₂ |
| `SAT_FLOOR` | 10°C | Minimum allowed AHU SAT |

**Zone configuration array (`ZONES`):**

Each zone is defined as a Python dictionary with keys: `zone`, `terminal`, `use`, `max_flow_m3s`, `cool_sp`, `heat_sp`, `rh_target`, `kp`, `ki`. The `max_mdot` field is computed automatically as `max_flow_m3s × RHO_AIR`.

## 9.3 Orchestrator — main.py

The `main.py` module is the entry point and contains the `Orchestrator` class that manages the entire co-simulation lifecycle.

### Class Structure

```python
class Orchestrator:
    def __init__(self, api, state):
        # Initialise EnergyPlus API references
        # Create zone controllers from config
        # Create AHU coordinator
        # Build occupancy models
    
    def _resolve_handles(self):
        # One-time handle resolution for all sensors and actuators
        # Dump available_api_data.csv for debugging
    
    def _open_log(self):
        # Create output directory and open CSV writer
    
    def _log_row(self, meas_all, requests, cmd):
        # Write one row to control_log.csv
    
    def on_timestep(self, state):
        # Main callback — runs at every simulation timestep
        # Steps 0-5: Occupancy → Read → Control → Coordinate → Write → Log
    
    def close(self):
        # Flush and close the CSV log file
```

### Controller Instantiation

Controllers are created using a factory pattern that maps zone names to controller classes:

```python
CONTROLLER_CLASSES = {
    "Zone 1": Zone1Controller,
    "Zone 2": Zone2Controller,
    "Zone 3": Zone3Controller,
    "Zone 4": Zone4Controller,
    "Zone 5": Zone5Controller,
}

def build_controller(cfg):
    cls = CONTROLLER_CLASSES.get(cfg["zone"], ZoneController)
    return cls(cfg)
```

This allows zone-specific controller subclasses (like Zone 4's server room override) to be automatically instantiated based on the zone name in the configuration.

## 9.4 Zone Controller Base Class — zone_controller.py

The `ZoneController` class implements the complete PI control loop with anti-windup and adaptive gain scheduling.

**Key methods:**

- `__init__(cfg)`: Stores configuration, initialises PI integrator to zero, creates per-zone EKF instance.
- `_gain_multiplier(hour, is_weekday)`: Returns `(kp_mult, ki_mult)` for the current time period.
- `step(meas, dt, hour, is_weekday)`: Main control step — runs EKF update, computes PI output with adaptive gains and anti-windup, computes SAT request based on humidity, returns request dictionary.

**State maintained between timesteps:**

- `self._integral`: The accumulated integral of error × time [°C·s].
- `self.ekf`: The per-zone EKF instance with its state vector and covariance matrix.
- `self._last_u`: Dictionary of last-known control inputs for the EKF.

## 9.5 Zone-Specific Controllers

### Standard Zones (Zone 1, 2, 3, 5)

These zones inherit directly from `ZoneController` with no overrides:

```python
class Zone1Controller(ZoneController):
    pass
```

The `pass` statement means the standard PI + anti-windup + adaptive gain behaviour applies. Each zone gets different gains and setpoints through the configuration dictionary passed at construction time.

### Zone 4 — Server Room

Zone 4 overrides two aspects:

1. **Gain multiplier:** Always returns `(1.0, 1.0)` — no time-of-day adaptation because the server load is constant.
2. **Step method:** After running the standard PI computation, enforces a minimum mass flow rate of 30% of maximum capacity.

```python
class Zone4Controller(ZoneController):
    def _gain_multiplier(self, hour, is_weekday):
        return 1.0, 1.0
    
    def step(self, meas, dt, hour=12.0, is_weekday=True):
        req = super().step(meas, dt, hour, is_weekday)
        min_mdot = 0.30 * self.cfg["max_mdot"]
        req["mdot"] = max(req["mdot"], min_mdot)
        return req
```

## 9.6 AHU Coordinator — ahu.py

The `AHUCoordinator` class is intentionally simple — just 18 lines of code. It implements two aggregation rules:

1. **SAT:** `max(SAT_FLOOR, min(all zone t_sup_req))`
2. **OA flow:** `clamp((co2_max - 400) / (800 - 400), 0.15, 1.0) × total_mdot`

## 9.7 Extended Kalman Filter — ekf.py

The `ZoneEKF` class stores:

- `self.x`: 8-element state vector (NumPy array)
- `self.P`: 8×8 covariance matrix
- `self.Q`: 8×8 process noise covariance
- `self.R`: 3×3 measurement noise covariance

Methods:
- `predict(u, dt)`: Implements `x⁻ = f(x, u, dt)` and `P⁻ = FPFᵀ + Q` (currently scaffold)
- `update(z, u, dt)`: Implements the full predict-then-update cycle (currently scaffold)
- `params` (property): Returns the hidden parameter slice `x[3:]`

The `default_init()` factory function returns a dictionary with reasonable initial values for all matrices.

## 9.8 Occupancy Mirror — occupancy.py

The `ZoneOccupancy` class provides a `step(hour, day_of_week_ep)` method that returns the expected people count. The `build_occupancy_models(zones_cfg)` factory function creates one instance per zone, reading peak occupancy from a built-in lookup table.

## 9.9 Data Logging Mechanism

The orchestrator opens a CSV file at startup and writes one row per timestep. The CSV header is dynamically constructed:

```python
cols = ["datetime", "sim_hours"]
for z in ZONES:
    k = z["zone"].replace(" ", "")
    cols += [f"{k}_T", f"{k}_w", f"{k}_rh", f"{k}_co2",
             f"{k}_mdot_cmd", f"{k}_coolSP_cmd", f"{k}_occ"]
cols += ["AHU_SAT_cmd", "AHU_OA_cmd"]
```

This produces a CSV with 39 columns: datetime, sim_hours, 7 columns per zone × 5 zones, and 2 AHU columns.

---

\pagebreak

# 10. EnergyPlus Co-Simulation Interface

## 10.1 Python API Overview

The EnergyPlus Python API (`pyenergyplus`) provides a programmatic interface to the EnergyPlus simulation engine. It allows external Python code to:

- Start and control the simulation lifecycle
- Register callback functions that fire at specific simulation events
- Read output variables (sensor values)
- Write to actuators (control commands)
- Query simulation state (time, warmup flag, data availability)

The API is shipped with the EnergyPlus installation and must be on the `PYTHONPATH` for import.

## 10.2 Handle Resolution

Before reading variables or writing actuators, the Python code must obtain **handles** — integer identifiers that map to specific EnergyPlus objects. Handle resolution is performed once at the start of the simulation, after the API reports that data is fully ready.

### Variable Handles

```python
# Per-zone sensor handles
h["T:Zone 1"]   = ex.get_variable_handle(st, "Zone Mean Air Temperature", "Zone 1")
h["w:Zone 1"]   = ex.get_variable_handle(st, "Zone Air Humidity Ratio", "Zone 1")
h["rh:Zone 1"]  = ex.get_variable_handle(st, "Zone Air Relative Humidity", "Zone 1")
h["co2:Zone 1"] = ex.get_variable_handle(st, "Zone Air CO2 Concentration", "Zone 1")
```

### Actuator Handles

```python
# AHU-level actuators
h["sat_sp"]  = ex.get_actuator_handle(st, "System Node Setpoint",
                                       "Temperature Setpoint", "DX Coil Outlet Node")
h["oa_flow"] = ex.get_actuator_handle(st, "Outdoor Air Controller",
                                       "Air Mass Flow Rate", "VAV OA Controller")

# Per-zone actuators
h["mdot:Zone 1"] = ex.get_actuator_handle(st,
    "AirTerminal:SingleDuct:ConstantVolume:NoReheat", "Mass Flow Rate",
    "Zone 1 Air Terminal")
h["csp:Zone 1"]  = ex.get_actuator_handle(st,
    "Zone Temperature Control", "Cooling Setpoint", "Zone 1")
```

### Debugging Handle Resolution

The orchestrator dumps all available API data to `available_api_data.csv` at startup:

```python
with open("available_api_data.csv", "w") as fh:
    fh.write(ex.list_available_api_data_csv(st).decode("utf-8", "replace"))
```

This file lists every variable and actuator available in the current build, including exact string names needed for handle resolution. If any handle returns -1 (unresolved), the simulation is stopped with a fatal error message directing the user to this file.

## 10.3 Callback Registration

The Python control logic is registered as a callback that fires at a specific point in the EnergyPlus simulation loop:

```python
api.runtime.callback_end_zone_timestep_after_zone_reporting(state, orch.on_timestep)
```

This callback point fires **after each zone reporting timestep** — meaning EnergyPlus has fully computed all zone states (temperature, humidity, CO₂) for the current timestep. The Python callback can then:

1. Read the freshly computed zone states.
2. Compute control actions.
3. Write actuator values that will take effect at the next timestep.

## 10.4 Sensor Reading

Sensor values are read using the resolved variable handles:

```python
T   = ex.get_variable_value(st, self.h["T:Zone 1"])
w   = ex.get_variable_value(st, self.h["w:Zone 1"])
rh  = ex.get_variable_value(st, self.h["rh:Zone 1"])
co2 = ex.get_variable_value(st, self.h["co2:Zone 1"])
```

## 10.5 Actuator Writing

Actuator values are written after the control computation:

```python
# Per-zone actuators
ex.set_actuator_value(st, self.h["mdot:Zone 1"], mdot)     # Mass flow [kg/s]
ex.set_actuator_value(st, self.h["csp:Zone 1"], cool_sp)    # Cooling setpoint [°C]

# AHU actuators
ex.set_actuator_value(st, self.h["sat_sp"], sat_sp)         # SAT setpoint [°C]
ex.set_actuator_value(st, self.h["oa_flow"], oa_flow)       # OA mass flow [kg/s]
```

### Write Order

1. `mdot` per zone → VAV terminal mass flow rate, clamped to `[0, max_mdot]`
2. `cool_sp` per zone → zone temperature cooling setpoint
3. `sat_sp` → AHU supply air temperature setpoint
4. `oa_flow` → AHU outdoor air mass flow rate

## 10.6 Warm-Up Handling

EnergyPlus performs warm-up days at the start of the simulation to initialise zone temperatures and HVAC equipment states. During warm-up:

```python
if ex.warmup_flag(st):
    return  # Skip control during warm-up
```

The Python controller does not execute during warm-up — EnergyPlus uses its own default schedules and setpoints. Once warm-up is complete, the Python controller takes over.

---

\pagebreak

# 11. Output, Analysis, and Visualisation

## 11.1 Control Log CSV Schema

The primary output is `out/control_log.csv`, written by the Python orchestrator at every simulation timestep. Each row represents one 10-minute interval of simulated time.

| Column | Description | Units |
|---|---|---|
| `datetime` | Simulation timestamp (`MM-DD HH:MM`) | — |
| `sim_hours` | Total elapsed simulation hours | h |
| `{Zone}_T` | Zone mean air temperature | °C |
| `{Zone}_w` | Zone humidity ratio | kg/kg |
| `{Zone}_rh` | Zone relative humidity | % |
| `{Zone}_co2` | Zone CO₂ concentration | ppm |
| `{Zone}_mdot_cmd` | Commanded supply mass flow | kg/s |
| `{Zone}_coolSP_cmd` | Commanded cooling setpoint | °C |
| `{Zone}_occ` | Expected occupancy (mirrored) | people |
| `AHU_SAT_cmd` | AHU supply air temperature setpoint | °C |
| `AHU_OA_cmd` | AHU outdoor air mass flow | kg/s |

Where `{Zone}` ∈ {Zone1, Zone2, Zone3, Zone4, Zone5}.

**File size:** Approximately 12.5 MB for a full annual simulation (~52,560 rows × 39 columns).

## 11.2 Terminal Analysis Script — analyse_results.py

The `analyse_results.py` script reads the control log CSV and prints a comprehensive performance summary to the terminal:

### Temperature Report
- Mean, standard deviation, minimum, maximum for each zone
- Percentage of time within ±1°C of setpoint (tight comfort band)
- Percentage of time within ±2°C of setpoint (wide comfort band)
- Percentage of time above setpoint (comfort violations)

### CO₂ Report
- Mean and maximum CO₂ for each zone
- Percentage below 800 ppm (controller target)
- Percentage below 1000 ppm (ASHRAE 62.1 limit)
- WARNING flag if any zone exceeds 1000 ppm

### Humidity Report
- Mean and maximum relative humidity for each zone
- Percentage below 60% (comfort limit)
- Percentage above 60% (discomfort)

### Airflow Utilisation
- Mean and maximum flow for each zone
- Capacity (max_mdot) for reference
- Average utilisation percentage

### AHU Commands
- SAT distribution: percentage of time at each discrete SAT level
- OA flow statistics: mean, min, max

## 11.3 Matplotlib Visualisation — visualize.py

The `visualize.py` script generates three dark-themed interactive figures using Matplotlib:

### Common Features

All three figures share:
- **Dark theme:** Background `#0E1117`, panel `#1A1D27`, grid `#2A2D3A`
- **Zone colours:** Cyan-blue, lime-green, amber, purple, rose-pink
- **Semi-transparent fills** between the raw data line and rolling mean
- **2-day rolling mean** overlay (dashed line, 288-sample window)
- **Statistics annotation box** with mean, min, max per zone
- **Month filtering** (plots one month at a time, selectable via `MONTH_TO_PLOT`)

### Figure 1: Temperature

- All 5 zones plotted on the same axes
- Y-axis: Zone Mean Air Temperature (°C)
- Red dotted line at 24°C cooling setpoint
- Shows temperature tracking quality and any excursions

### Figure 2: Relative Humidity

- All 5 zones plotted on the same axes
- Y-axis: Zone Air Relative Humidity (%)
- Shows humidity management effectiveness

### Figure 3: CO₂ Concentration

- All 5 zones plotted on the same axes
- Y-axis: Zone Air CO₂ Concentration (ppm)
- Red dotted line at 1000 ppm ASHRAE 62.1 indicative limit
- Shows ventilation adequacy and CO₂ control

## 11.4 Interactive Web Dashboard — dashboard.html

The web dashboard provides a premium, interactive playback experience for the simulation data:

### Design Features

- **Glassmorphism UI:** Translucent panels with `backdrop-filter: blur(18px)`, subtle borders, and ambient gradient background
- **Typography:** Inter for body text, JetBrains Mono for data values
- **Responsive:** Adapts to screen widths from 640px to 1480px+

### Dashboard Sections

1. **Header and Transport Bar:**
   - Play/pause, restart, step-forward controls
   - Speed selector: 1×, 5×, 10×, 25×, 50×, 100×, 250×, 500×
   - Animated pulse dot (green when playing, amber when paused)
   - Simulation clock display (e.g., "Mar 15 — 14:20")
   - Progress scrubber bar with percentage

2. **Zone Overview Cards (5 cards):**
   - Zone-coloured accent bar
   - Live KPI values: Temperature, Humidity, CO₂, Airflow
   - Status dot: Green (OK), Amber (WARNING), Red (CRITICAL)
   - Status logic: CRITICAL if T > setpoint+2 or CO₂ > 1000; WARNING if T > setpoint+1 or CO₂ > 800 or RH > 70

3. **AHU Coordinator Panel (4 gauges):**
   - Supply Air Temp Setpoint with gauge bar
   - Outdoor Air Mass Flow with gauge bar
   - OA Ratio with colour-coded gauge (red < 15%, amber < 30%, green ≥ 30%)
   - Worst-Zone CO₂ with colour-coded gauge

4. **Charts (4 rolling-window charts):**
   - Temperature, Relative Humidity, CO₂, Airflow
   - 24-hour rolling window (144 samples at 10-min resolution)
   - Zone filter dropdowns for individual zone view
   - ASHRAE 1000 ppm reference line on CO₂ chart
   - Powered by Chart.js with dark theme and JetBrains Mono axes

5. **Controller Configuration Table:**
   - Shows all zone parameters: controller type, estimator, setpoints, gains, max flow
   - Live status column with OK/WARNING/CRITICAL badges

6. **File Loading:**
   - Drag-and-drop CSV upload
   - Click-to-browse file selector
   - Auto-load from `out/control_log.csv` (when served via `python -m http.server`)

---

\pagebreak

# 12. Performance Metrics and Compliance Criteria

## 12.1 Temperature Comfort

| Metric | Target | Method |
|---|---|---|
| Cooling setpoint | 24.0°C | All zones (except Zone 4 which may need tighter) |
| Tight band (±1°C) | Maximise % time in 23–25°C | Good control quality indicator |
| Wide band (±2°C) | Maximise % time in 22–26°C | Minimum acceptable comfort |
| Above setpoint | Minimise % time > 24°C | Indicates insufficient cooling |

## 12.2 Indoor Air Quality — CO₂

| Metric | Target | Standard |
|---|---|---|
| Controller target | < 800 ppm | Project design goal |
| ASHRAE 62.1 limit | < 1000 ppm | Industry standard maximum |
| Minimum OA fraction | ≥ 15% | Code minimum (enforced by clamp) |

## 12.3 Humidity Compliance

| Metric | Target | Notes |
|---|---|---|
| General comfort | RH < 60% | All occupied zones |
| Zone 4 (Server Room) | RH < 50% | Tighter target for electronics |
| Dehumidification trigger | RH > target → SAT request drops | Proportional, not bang-bang |

## 12.4 Airflow Utilisation

| Metric | Description |
|---|---|
| Flow range | 0 to max_mdot per zone |
| Zone 4 minimum | Always ≥ 30% of max_mdot |
| Utilisation % | mean_flow / max_flow × 100% |

## 12.5 AHU Command Analysis

| Metric | Description |
|---|---|
| SAT distribution | % time at each SAT level (12°C, 13°C, 14°C) |
| OA flow statistics | Mean, min, max outdoor air mass flow |
| OA ratio | Percentage of total supply air that is outdoor air |

---

\pagebreak

# 13. Results and Discussion

## 13.1 Annual Simulation Overview

The simulation covers a full 8,760-hour year (January 1 to December 31) with a 10-minute timestep resolution, producing approximately 52,560 data points per zone variable. The simulation uses Colombo, Sri Lanka weather data, representing a consistently hot and humid tropical climate.

Key observations from the annual simulation:

- The system operates in cooling mode for the entire year, with no heating events.
- The occupancy schedule creates sharp daily transitions between night mode (5% occupancy) and daytime mode (100% occupancy), testing the controller's ability to handle step-change disturbances.
- Weekend periods (0% occupancy) provide a baseline for understanding the building's unoccupied thermal behaviour.

## 13.2 Temperature Control Performance

The PI controller with anti-windup and adaptive gains is expected to maintain zone temperatures close to the 24°C cooling setpoint. Key performance indicators include:

- **Setpoint tracking:** The proportional term provides immediate response to temperature deviations, while the integral term eliminates steady-state error.
- **Morning ramp-up:** The 1.5× Kp multiplier during 07:30–09:00 helps the controller respond aggressively to the sudden occupancy increase at 08:00.
- **Night setback:** Reduced gains during unoccupied hours prevent unnecessary energy consumption while maintaining acceptable temperature drift.
- **Zone 4 (Server Room):** The minimum airflow floor ensures continuous cooling for the high-density equipment load.

Potential issues to monitor:
- Temperature spikes during rapid load changes (occupancy arrival, solar gain shifts)
- Over-cooling during light-load periods if the integral term has accumulated from a previous period
- Inter-zone coupling effects (mitigated by adiabatic internal walls in the model)

## 13.3 Humidity Management

In Colombo's humid climate, relative humidity management is as important as temperature control. The proportional SAT request strategy (12–14°C based on RH error) provides continuous modulation of dehumidification effort:

- When RH exceeds the target (55% for most zones, 50% for the server room), the zone requests colder supply air (down to 12°C), increasing moisture condensation on the DX coil.
- When RH is below target, the zone requests warmer supply air (up to 14°C), reducing unnecessary dehumidification and saving cooling energy.
- The proportional approach avoids the oscillations that would occur with a simple on/off humidity switch.

The server room's tighter humidity target (50%) reflects the need to protect electronic equipment from moisture damage.

## 13.4 CO₂ Control and Ventilation

The demand-controlled ventilation strategy adjusts outdoor air flow proportionally to the worst-case CO₂ concentration:

- During occupied hours, CO₂ generation from 30 people (total across all zones) drives the OA fraction upward.
- Zone 3 (Conference Room) with 12 people in 120 m³ is likely the "worst zone" most of the time, driving the OA fraction.
- During unoccupied hours, CO₂ decays toward the outdoor level (400 ppm), and the OA fraction drops to the 15% minimum.
- The 15% minimum OA floor ensures compliance with ventilation codes at all times.

## 13.5 Zone 4 Server Room Behaviour

The server room presents unique control challenges:

- **Constant load:** Unlike other zones, Zone 4's equipment operates at 90% capacity 24/7. The 60 W/m² × 40 m² = 2,400 W continuous load (plus 240 W lighting and minor people gains) requires sustained cooling.
- **No gain scheduling:** The `_gain_multiplier()` override ensures constant control authority regardless of time of day.
- **Minimum airflow:** The 30% floor (0.216 kg/s) ensures that the server room never loses cooling, even if the PI controller computes zero output during brief temperature undershoots.
- **Tighter humidity:** The 50% RH target provides more aggressive dehumidification for electronics protection.

## 13.6 Adaptive Gains — Day/Night Behaviour

The gain scheduling creates distinct behaviour patterns:

- **Night (00:00–07:30):** With 0.50× Kp and 0.40× Ki, the controller is deliberately sluggish. The zone temperature may drift slightly from setpoint, but this is acceptable in an unoccupied building and saves significant fan energy.
- **Ramp-up (07:30–09:00):** The 1.5× Kp boost is critical during the morning occupancy arrival. Without this boost, the sudden heat load from 30 people arriving would cause a significant temperature overshoot before the PI controller could ramp up airflow.
- **Peak (09:00–17:30):** Baseline gains provide steady, well-tuned control during the period with the most occupants and the highest cooling demand.
- **Ramp-down (17:30–19:00):** The 1.1× Kp boost smooths the transition as occupancy drops. Without it, the controller might maintain high airflow briefly after people leave, causing unnecessary over-cooling.
- **After-hours (19:00–24:00):** Reduced gains (0.70× Kp, 0.60× Ki) reflect the lower thermal loads while maintaining slightly more responsiveness than full night mode.

## 13.7 AHU Coordinator Effectiveness

The AHU coordinator's effectiveness can be assessed by examining:

- **SAT distribution:** In Colombo's humid climate, the SAT is expected to spend significant time at 12°C (dehumidification mode) rather than 14°C (cooling-only mode). The exact split depends on how often any zone exceeds its humidity target.
- **OA fraction:** During occupied hours, the OA fraction should track CO₂ levels proportionally. The 15% minimum during unoccupied hours provides baseline ventilation without excessive energy waste.
- **Conflict resolution:** The "most demanding zone" strategy for SAT ensures that no zone is undersupplied, at the cost of potentially over-cooling zones with lower demands. This is acceptable because zones with lower SAT needs can reduce their airflow to compensate.

## 13.8 Energy Implications

While this project focuses on control performance rather than energy optimisation, several design decisions have significant energy implications:

1. **Adaptive gains:** Reducing fan speed during unoccupied hours saves fan energy (which scales with the cube of flow rate for variable-speed fans).
2. **DCV:** Reducing outdoor air during low-occupancy periods saves cooling energy that would otherwise be spent on conditioning unnecessary outdoor air.
3. **Proportional SAT request:** Avoiding unnecessarily cold supply air temperatures saves cooling energy compared to a fixed low SAT.
4. **Zone 4 minimum flow:** The 30% airflow floor for the server room is a safety measure that consumes more energy than necessary during low-load periods, but this is an acceptable trade-off for equipment protection.

---

\pagebreak

# 14. Conclusions

This project has successfully designed, implemented, and demonstrated a **decentralised HVAC control system** for a five-zone commercial office building in Colombo, Sri Lanka. The key achievements are:

1. **Building Model:** A comprehensive EnergyPlus model was created with five distinct thermal zones (Open Office, Private Offices, Conference Room, Server Room, Reception), realistic construction materials, internal loads, occupancy schedules, and a complete VAV air distribution system with DX cooling.

2. **Decentralised Control:** Each zone operates an independent PI controller that uses only its own sensor measurements — temperature, humidity ratio, relative humidity, and CO₂ concentration. This true decentralisation ensures fault tolerance, scalability, and implementation simplicity.

3. **Anti-Windup:** The conditional integration (clamping) anti-windup strategy effectively prevents integrator windup when zone actuators saturate, avoiding the delayed response and excessive overshoot that plague unprotected PI controllers.

4. **Adaptive Gains:** Time-of-day gain scheduling adapts the controller's aggressiveness to the building's predictable daily load pattern — aggressive during morning ramp-up, moderate during peak occupancy, and gentle during unoccupied hours. This improves both comfort and energy performance.

5. **Humidity Management:** The proportional SAT request strategy (12–14°C based on RH error) provides smooth, continuous dehumidification control appropriate for Colombo's hot-humid climate, avoiding the oscillations of bang-bang humidity switches.

6. **AHU Coordination:** The lightweight coordinator resolves system-level conflicts using simple min/max rules — selecting the coldest SAT request and scaling OA proportionally to the worst CO₂ zone. This approach is computationally trivial yet effective.

7. **EKF Framework:** The mathematical framework for a per-zone Extended Kalman Filter has been designed, with an augmented state vector containing observable states and hidden physical parameters. The implementation provides scaffold methods and graceful fallback to PI-only control.

8. **Co-Simulation:** The Python-EnergyPlus co-simulation framework demonstrates real-time control override at every simulation timestep, enabling rapid prototyping of control strategies that would be difficult to implement in EnergyPlus's native EMS language.

9. **Visualisation:** Three complementary visualisation tools — terminal analysis, Matplotlib plots, and a premium web dashboard — provide comprehensive insight into the system's behaviour at different levels of detail.

The project demonstrates that hierarchical decentralised control is a viable and practical approach for multi-zone HVAC systems, combining the simplicity and fault tolerance of local controllers with the system-wide awareness of a lightweight coordinator.

---

\pagebreak

# 15. Future Work and Recommendations

The following areas are recommended for future development:

## 15.1 Complete EKF Implementation

The highest-priority item is completing the EKF implementation by:
- Implementing the nonlinear state transition function `f(x, u, Δt)` based on the thermal, moisture, and CO₂ balance equations.
- Computing the analytical Jacobian `F = ∂f/∂x` for the prediction step.
- Validating the filter's convergence with synthetic data before deploying with EnergyPlus.

## 15.2 Model Predictive Control (MPC)

With the EKF providing online parameter estimates, a natural next step is Model Predictive Control, which uses the estimated model to predict future zone temperatures and optimise control actions over a receding horizon. MPC can:
- Pre-cool the building before occupancy arrival, using the building's thermal mass.
- Optimise the trade-off between energy consumption and comfort.
- Incorporate weather forecasts and occupancy predictions.

## 15.3 Reinforcement Learning

Deep reinforcement learning (DRL) agents could be trained using the EnergyPlus simulation environment to discover control policies that outperform hand-tuned PI controllers. The co-simulation framework already provides the necessary interface.

## 15.4 Inter-Zone Coupling

The current model uses adiabatic internal walls, eliminating thermal coupling between zones. Future work could model inter-zone heat transfer through partitions, testing the controller's robustness to thermal interactions.

## 15.5 Real-Time Weather Integration

Instead of using a fixed EPW weather file, future versions could integrate real-time weather data or weather forecasts for predictive control strategies.

## 15.6 Multi-AHU Systems

Larger buildings may have multiple AHUs serving different floors or wings. Extending the coordinator to manage multiple AHUs with shared chiller plants would test the scalability of the hierarchical approach.

## 15.7 Fault Detection and Diagnostics

The EKF's hidden parameter estimates could be used for fault detection — for example, a sudden increase in the estimated heat transfer coefficient `U` might indicate an envelope breach (broken window, failed seal), and a sudden increase in `q_occ` during unoccupied hours might indicate an equipment malfunction.

## 15.8 Economic Analysis

Adding energy cost calculations using time-of-use electricity tariffs would enable economic optimisation of control strategies, including demand response and peak shaving.

## 15.9 Hardware Deployment

The modular, decentralised architecture of the control system is well-suited for deployment on real hardware (e.g., Raspberry Pi controllers communicating via BACnet). Future work could test the control logic on a physical building or test rig.

---

\pagebreak

# 16. References

1. ASHRAE. (2020). *ASHRAE Standard 55 — Thermal Environmental Conditions for Human Occupancy*. American Society of Heating, Refrigerating and Air-Conditioning Engineers.

2. ASHRAE. (2022). *ASHRAE Standard 62.1 — Ventilation and Acceptable Indoor Air Quality in Residential Buildings*. American Society of Heating, Refrigerating and Air-Conditioning Engineers.

3. U.S. Department of Energy. (2024). *EnergyPlus Engineering Reference*. U.S. Department of Energy, Building Technologies Office.

4. U.S. Department of Energy. (2024). *EnergyPlus Input Output Reference*. U.S. Department of Energy, Building Technologies Office.

5. Åström, K. J., & Hägglund, T. (2006). *Advanced PID Control*. ISA - The Instrumentation, Systems and Automation Society.

6. Borrelli, F., Bemporad, A., & Morari, M. (2017). *Predictive Control for Linear and Hybrid Systems*. Cambridge University Press.

7. Welch, G., & Bishop, G. (2006). *An Introduction to the Kalman Filter*. TR 95-041, Department of Computer Science, University of North Carolina at Chapel Hill.

8. Afram, A., & Janabi-Sharifi, F. (2014). Theory and applications of HVAC control systems — A review of model predictive control (MPC). *Building and Environment*, 72, 343–355.

9. Ma, Z., & Wang, S. (2011). Online fault detection and robust control of condenser cooling water systems in building central chiller plants. *Energy and Buildings*, 43(1), 153–165.

10. Dounis, A. I., & Caraiscos, C. (2009). Advanced control systems engineering for energy and comfort management in a building environment — A review. *Renewable and Sustainable Energy Reviews*, 13(6-7), 1246–1261.

11. Wang, S., & Ma, Z. (2008). Supervisory and optimal control of building HVAC systems: A review. *HVAC&R Research*, 14(1), 3–32.

12. Privara, S., Váňa, Z., Žáčeková, E., & Cigler, J. (2013). Building modeling: Selection of the most appropriate model for predictive control. *Energy and Buildings*, 55, 341–350.

13. Crawley, D. B., Lawrie, L. K., Winkelmann, F. C., et al. (2001). EnergyPlus: creating a new-generation building energy simulation program. *Energy and Buildings*, 33(4), 319–331.

14. Nassif, N. (2012). A robust CO₂-based demand-controlled ventilation control strategy for multi-zone HVAC systems. *Energy and Buildings*, 45, 72–81.

15. Kottek, M., Grieser, J., Beck, C., Rudolf, B., & Rubel, F. (2006). World Map of the Köppen-Geiger climate classification updated. *Meteorologische Zeitschrift*, 15(3), 259–263.

---

\pagebreak

# 17. Appendices

## Appendix A — Equation Quick Reference

| Quantity | Formula |
|---|---|
| Temperature error | `e = T_zone - T_setpoint` |
| PI output | `u = Kp_eff · e + Ki_eff · ∫(e dt)` |
| Effective proportional gain | `Kp_eff = Kp · kp_mult(hour, weekday)` |
| Effective integral gain | `Ki_eff = Ki · ki_mult(hour, weekday)` |
| Discrete integration | `Iₖ = Iₖ₋₁ + eₖ · Δt` |
| Anti-windup condition | Accept I update only if output NOT saturated in error direction |
| Actuator clamping | `mdot = clamp(u, 0, mdot_max)` |
| Zone 4 minimum flow | `mdot₄ = max(mdot_PI, 0.30 × mdot_max₄)` |
| Humidity SAT request | `t_sup = max(12, min(14, 13 - 0.2 × rh_err))` |
| AHU SAT setpoint | `T_SAT = max(10, min_z(t_sup_req_z))` |
| OA fraction | `φ = clamp((c_max - 400)/(800 - 400), 0.15, 1.0)` |
| OA mass flow | `ṁ_OA = φ × Σ(ṁ_z)` |
| EKF predict | `x⁻ = f(x, u, Δt); P⁻ = F P Fᵀ + Q` |
| EKF update | `K = P⁻Hᵀ(HP⁻Hᵀ + R)⁻¹; x = x⁻ + K(z - h(x⁻))` |
| Thermal balance | `C_T · dT/dt = ṁcₚ(T_sup - T) - U(T - T_out) + q_int + q_occ` |
| Moisture balance | `C_w · dw/dt = ṁ(w_sup - w) + moisture_gen` |
| CO₂ balance | `V · dc/dt = ṁ(c_sup - c) + k · N_occ` |

---

## Appendix B — Full Source Code Listings

### B.1 config.py

```python
"""Per-zone configuration. One dict per zone; the driver builds a controller
from each. Keep all zone-specific numbers here so the controller code stays generic.
"""

RHO_AIR = 1.2  # kg/m3, converts terminal max flow (m3/s) to a kg/s ceiling

ZONES = [
    dict(zone="Zone 1", terminal="Zone 1 Air Terminal", use="Open Office",
         max_flow_m3s=0.50, cool_sp=24.0, heat_sp=18.0, rh_target=55.0, kp=0.25, ki=0.008),
    dict(zone="Zone 2", terminal="Zone 2 Air Terminal", use="Private Offices",
         max_flow_m3s=0.35, cool_sp=24.0, heat_sp=18.0, rh_target=55.0, kp=0.25, ki=0.008),
    dict(zone="Zone 3", terminal="Zone 3 Air Terminal", use="Conference Room",
         max_flow_m3s=0.55, cool_sp=24.0, heat_sp=18.0, rh_target=55.0, kp=0.30, ki=0.010),
    dict(zone="Zone 4", terminal="Zone 4 Air Terminal", use="Server Room",
         max_flow_m3s=0.60, cool_sp=24.0, heat_sp=18.0, rh_target=50.0, kp=0.35, ki=0.012),
    dict(zone="Zone 5", terminal="Zone 5 Air Terminal", use="Reception",
         max_flow_m3s=0.35, cool_sp=24.0, heat_sp=18.0, rh_target=55.0, kp=0.25, ki=0.008),
]

for _z in ZONES:
    _z["max_mdot"] = _z["max_flow_m3s"] * RHO_AIR

CO2_SETPOINT = 800.0     # ppm, central coordinator target
OUTDOOR_CO2 = 400.0      # ppm
SAT_FLOOR = 10.0         # degC, lowest allowed AHU supply-air temperature
```

### B.2 controllers/zone_controller.py

```python
"""Base decentralised zone controller — PI with anti-windup + adaptive gains.

One instance per zone. It sees ONLY its own zone's measurements (that is what
makes the scheme decentralised). Each step it (1) updates its EKF, then
(2) runs a discrete PI control law to decide the zone's desired supply mass
flow and a local SAT request, which the AHU coordinator later aggregates.
"""
from estimation.ekf import ZoneEKF, default_init


class ZoneController:
    def __init__(self, cfg):
        self.cfg = cfg
        self.zone = cfg["zone"]
        self.cool_sp = cfg["cool_sp"]
        self.heat_sp = cfg["heat_sp"]
        self.kp = cfg["kp"]
        self.ki = cfg["ki"]
        self._integral = 0.0

        init = default_init()
        self.ekf = ZoneEKF(init["x0"], init["P0"], init["Q"], init["R"])
        self._last_u = dict(mdot=0.0, t_sup=13.0, w_sup=0.008, c_sup=400.0,
                            t_out=30.0, w_out=0.018, c_out=400.0, q_int=0.0,
                            volume=40.0 * 3.0)

    def _gain_multiplier(self, hour, is_weekday):
        if not is_weekday:
            return 0.50, 0.40
        if 7.5 <= hour < 9.0:
            return 1.50, 1.00
        elif 9.0 <= hour < 17.5:
            return 1.00, 1.00
        elif 17.5 <= hour < 19.0:
            return 1.10, 1.00
        elif 19.0 <= hour:
            return 0.70, 0.60
        else:
            return 0.50, 0.40

    def step(self, meas, dt, hour=12.0, is_weekday=True):
        try:
            self.ekf.update([meas["T"], meas["w"], meas["co2"]], self._last_u, dt)
            est = self.ekf.params.tolist()
        except NotImplementedError:
            est = None

        err = meas["T"] - self.cool_sp
        kp_mult, ki_mult = self._gain_multiplier(hour, is_weekday)
        kp_eff = self.kp * kp_mult
        ki_eff = self.ki * ki_mult

        integral_candidate = self._integral + err * dt
        u_raw = kp_eff * err + ki_eff * integral_candidate
        mdot = min(max(0.0, u_raw), self.cfg["max_mdot"])

        saturated_high = u_raw >= self.cfg["max_mdot"] and err > 0
        saturated_low  = u_raw <= 0.0               and err < 0
        if not (saturated_high or saturated_low):
            self._integral = integral_candidate

        rh_err = meas["rh"] - self.cfg["rh_target"]
        t_sup_req = max(12.0, min(14.0, 13.0 - 0.2 * rh_err))

        self._last_u.update(mdot=mdot, t_sup=t_sup_req)
        return dict(zone=self.zone, mdot=mdot, t_sup_req=t_sup_req,
                    co2=meas["co2"], cool_sp=self.cool_sp, est=est)
```

### B.3 controllers/ahu.py

```python
"""Central AHU coordinator (lightweight).

Aggregates every zone's request and picks the AHU-level commands:
  * supply-air-temperature setpoint
  * outdoor-air mass flow
"""
from config import CO2_SETPOINT, OUTDOOR_CO2, SAT_FLOOR


class AHUCoordinator:
    def __init__(self, zones):
        self.zones = zones

    def coordinate(self, requests):
        sat = max(SAT_FLOOR, min(r["t_sup_req"] for r in requests))
        co2_max = max(r["co2"] for r in requests)
        tot_mdot = sum(r["mdot"] for r in requests)
        oa_frac = (co2_max - OUTDOOR_CO2) / (CO2_SETPOINT - OUTDOOR_CO2)
        oa_frac = min(1.0, max(0.15, oa_frac))
        return dict(sat_sp=sat, oa_flow=oa_frac * tot_mdot)
```

### B.4 controllers/zone4.py (Server Room Override)

```python
"""Zone 4 — Server Room.

24/7 high equipment load: override gains + enforce minimum airflow floor.
"""
from controllers.zone_controller import ZoneController


class Zone4Controller(ZoneController):
    def _gain_multiplier(self, hour, is_weekday):
        return 1.0, 1.0

    def step(self, meas, dt, hour=12.0, is_weekday=True):
        req = super().step(meas, dt, hour, is_weekday)
        min_mdot = 0.30 * self.cfg["max_mdot"]
        req["mdot"] = max(req["mdot"], min_mdot)
        return req
```

### B.5 estimation/ekf.py

```python
"""Per-zone Extended Kalman Filter.

Augmented state:
    x = [ T, w, c, C_T, U, C_w, k, q_occ ]
"""
import numpy as np


class ZoneEKF:
    def __init__(self, x0, P0, Q, R):
        self.x = np.asarray(x0, dtype=float)
        self.P = np.asarray(P0, dtype=float)
        self.Q = np.asarray(Q, dtype=float)
        self.R = np.asarray(R, dtype=float)

    def predict(self, u, dt):
        raise NotImplementedError("fill in f() and its Jacobian")

    def update(self, z, u, dt):
        raise NotImplementedError("fill in h(), Jacobians, gain update")

    @property
    def params(self):
        return self.x[3:].copy()


def default_init():
    x0 = [24.0, 0.010, 500.0, 3.0e5, 50.0, 2.0e4, 0.01, 0.0]
    P0 = np.diag([0.5, 1e-6, 100.0, 1e9, 100.0, 1e6, 1e-3, 1.0])
    Q  = np.diag([0.01, 1e-9, 1.0, 1e6, 1.0, 1e3, 1e-5, 0.1])
    R  = np.diag([0.1, 1e-7, 25.0])
    return dict(x0=x0, P0=P0, Q=Q, R=R)
```

### B.6 occupancy.py

```python
"""IDF-schedule occupancy mirror — for logging only."""


def _office_occupancy_fraction(hour, day_of_week_ep):
    is_weekday = 2 <= day_of_week_ep <= 6
    if not is_weekday:
        return 0.0
    if hour < 8.0:
        return 0.05
    elif hour < 18.0:
        return 1.00
    else:
        return 0.05


class ZoneOccupancy:
    def __init__(self, max_people):
        self.max_people = max_people
        self.current = 0.0

    def step(self, hour, day_of_week_ep):
        fraction = _office_occupancy_fraction(hour, day_of_week_ep)
        self.current = self.max_people * fraction
        return self.current


_IDF_MAX_PEOPLE = {
    "Zone 1": 8, "Zone 2": 4, "Zone 3": 12, "Zone 4": 1, "Zone 5": 5,
}


def build_occupancy_models(zones_cfg):
    models = []
    for z in zones_cfg:
        max_p = _IDF_MAX_PEOPLE.get(z["zone"], 0)
        models.append(ZoneOccupancy(max_people=max_p))
    return models
```

---

## Appendix C — EnergyPlus IDF Highlights

### C.1 Key IDF Objects Summary

| IDF Object | Name | Purpose |
|---|---|---|
| `Building` | Multi-Zone VAV Building | Building metadata and convergence |
| `Timestep` | 6 | 10-minute intervals |
| `RunPeriod` | Annual Run | Jan 1 – Dec 31, Monday start |
| `Site:Location` | Colombo Sri Lanka | 6.9°N, 79.86°E, UTC+5.5 |
| `ZoneAirContaminantBalance` | — | Enables CO₂ tracking |
| `AirLoopHVAC` | VAV Air Loop | Main air distribution loop |
| `Coil:Cooling:DX:SingleSpeed` | VAV DX Cooling Coil | COP=3.5, autosized |
| `Fan:VariableVolume` | VAV Supply Fan | η=0.70, 600 Pa, min 25% |
| `Controller:OutdoorAir` | VAV OA Controller | NoEconomizer, Python-overridden |

### C.2 Zone Geometry Summary

| Zone | X Range | Y Range | Z Range | Exterior Walls |
|---|---|---|---|---|
| Zone 1 | 0–5 m | 0–8 m | 0–3 m | South, North, West |
| Zone 2 | 5–10 m | 0–8 m | 0–3 m | South, North |
| Zone 3 | 10–15 m | 0–8 m | 0–3 m | South, North |
| Zone 4 | 15–20 m | 0–8 m | 0–3 m | South, North |
| Zone 5 | 20–25 m | 0–8 m | 0–3 m | South, North, East |

---

## Appendix D — How to Run the Project

### D.1 Prerequisites

- EnergyPlus installed (v24.x or v25.x recommended)
- `pyenergyplus` on `PYTHONPATH` (ships with EnergyPlus install, under `pyenergyplus/`)
- Python 3.10+ with virtual environment
- NumPy (for EKF matrices)

### D.2 Step-by-Step Execution

```powershell
# 1. Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Run the simulation (generates out/control_log.csv)
python main.py

# 4. Visualise results (opens 3 interactive plot windows)
python visualize.py

# 5. Print performance summary to terminal
python analyse_results.py

# 6. Launch web dashboard (open http://localhost:8000/dashboard.html)
python -m http.server 8000
```

### D.3 Optional: Enable EnergyPlus Native CSV Output

Set `EPLUS_ROOT` in `main.py`:

```python
EPLUS_ROOT = r"C:\EnergyPlusV25-2-0"
```

This enables the `-r` flag for `ReadVarsESO` post-processing, generating `out/eplusout.csv` alongside the custom `control_log.csv`.

### D.4 Modifying the Simulation

- **Change zone parameters:** Edit `config.py` (gains, setpoints, flow limits)
- **Change occupancy schedule:** Edit the `Schedule:Compact` objects in the IDF and mirror in `occupancy.py`
- **Change weather file:** Replace `model/Colombo.epw` and update the `EPW` path in `main.py`
- **Add a new zone:** Add zone geometry/loads to the IDF, add a config entry to `config.py`, create a new zone controller file, and add to the terminal and air loop in the IDF

---

*End of Report*

*ME325 — Decentralised HVAC Control for a Multi-Zone Commercial Building*
*University of Moratuwa, Sri Lanka*

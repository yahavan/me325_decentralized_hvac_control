# ME325 3YP — Final Demonstration Video Script
### Decentralised HVAC Control for a Multi-Zone Building (EnergyPlus + Python)

**Total estimated length:** ~9–13 minutes  
**Format:** Slides (intro/theory) → Screen recordings (code/results/dashboard) → Slide (conclusion)

---

## Production Notes

| Element | Detail |
|---|---|
| Voice | Calm, measured pace — technical but accessible |
| Slide transitions | Fade or subtle slide-in |
| Screen recordings | Dark terminal / dark-themed plots / dashboard |
| Annotations | Use arrows/highlights to draw attention while speaking |
| Background music | Optional light ambient track, low volume |

---

---

## SEGMENT 1 — Title & Introduction
**Format: Slide**  
**Duration: ~45 seconds**

---

**[SLIDE: Project title, university logo, your name]**

> *"This is ME325 — a third-year project on decentralised HVAC control for a multi-zone commercial building. The goal was to design, implement, and evaluate a Python-driven control system co-simulated with EnergyPlus — a high-fidelity building energy simulation engine."*

> *"In this video, I'll walk you through the project motivation, the system architecture we designed, the control algorithms we implemented, and finally the simulation results."*

---

## SEGMENT 2 — Problem Statement & Objectives
**Format: Slide**  
**Duration: ~1 minute 30 seconds**

---

**[SLIDE: Problem statement — bullet points with building illustration]**

> *"Commercial buildings account for a significant share of global energy consumption — and HVAC systems are among the largest contributors within them. The challenge is particularly acute in tropical climates like Colombo, Sri Lanka, where outdoor temperatures range from 27 to 33 degrees Celsius year-round, and relative humidity regularly sits between 70 and 85 percent."*

> *"In such conditions, you can't rely on free cooling or economiser modes. The system must actively cool and dehumidify around the clock. Poorly designed control leads to thermal discomfort, high CO₂ levels from inadequate ventilation, and wasted energy."*

**[SLIDE: Project Objectives — 3 bullet points]**

> *"This project had three core objectives:"*

> *"**First** — implement a decentralised control architecture where each zone acts independently using only its own sensor readings. No zone can see another zone's conditions."*

> *"**Second** — implement a lightweight central AHU coordinator that resolves system-wide conflicts — specifically, setting the supply air temperature and outdoor air flow rate to serve all zones simultaneously."*

> *"**Third** — evaluate system performance against industry comfort and air quality standards: ASHRAE 55 for thermal comfort, ASHRAE 62.1 for CO₂ limits, and a 40–60% relative humidity target band."*

> *"It's important to note: the Extended Kalman Filter state estimator we originally planned was designed and scaffolded into the codebase, but full implementation of its Jacobian and physics functions was not completed within scope. The system operates entirely on the PI control loop — and the results we present today reflect that."*

---

## SEGMENT 3 — Building Energy Model (EnergyPlus)
**Format: Slide with building layout diagram**  
**Duration: ~1 minute**

---

**[SLIDE: Building layout diagram showing 5 zones and climate info]**

> *"Before diving into the control architecture, let's briefly look at the building model we designed in EnergyPlus."*

> *"The model represents a commercial office space divided into five thermal zones: an open office area, private offices, a conference room, a server room, and a reception area. These are all served by a single Variable Air Volume — or VAV — Air Handling Unit equipped with a direct expansion cooling coil and an outdoor air damper."*

> *"To test our controllers under challenging conditions, we simulated the building using a weather file for Colombo, Sri Lanka. This hot-humid tropical climate ensures the system faces high latent heat loads year-round, making dehumidification just as critical as temperature control."*

---

## SEGMENT 4 — System Architecture
**Format: Slide with architecture diagram**  
**Duration: ~1 minute 30 seconds**

---

**[SLIDE: System architecture block diagram — two-layer hierarchy]**

> *"Let me describe the overall system architecture. There are two distinct layers."*

> *"At the bottom layer is EnergyPlus — the building physics engine. It simulates a five-zone commercial office building: an open office, private offices, a conference room, a server room, and a reception area. Each zone has its own VAV air terminal connected to a single central AHU."*

> *"At the top layer is our Python control system. After every simulation timestep — which represents 10 minutes of simulated time — EnergyPlus fires a callback into Python. At that point, Python reads zone sensor data, runs the controllers, and writes actuator commands back into EnergyPlus before the next timestep begins."*

**[SLIDE: Timestep loop — 5-step diagram]**

> *"Within each timestep, five things happen in sequence:"*

> *"Step 1: Read — temperature, humidity ratio, relative humidity, and CO₂ concentration are read from all five zones."*

> *"Step 2: Local control — each zone's PI controller runs independently and produces a supply air mass flow request and a supply temperature request."*

> *"Step 3: Coordination — the AHU coordinator aggregates all zone requests."*

> *"Step 4: Write — the actuator commands are written back to EnergyPlus: mass flow per zone, cooling setpoints, supply air temperature, and outdoor air flow."*

> *"Step 5: Log — everything is recorded to a CSV file for post-analysis."*

---

## SEGMENT 5 — Control Design
**Format: Slide with equations**  
**Duration: ~2 minutes**

---

**[SLIDE: Zone-level PI controller — equation block]**

> *"Now let's look at the control design in detail, starting at the zone level."*

> *"Each zone runs an independent Proportional-Integral controller. The error signal is simply the difference between the measured zone temperature and the 24-degree Celsius cooling setpoint. A positive error means the zone is too warm and needs more airflow."*

> *"The PI output drives the supply air mass flow rate — more error means more cold air delivered. The output is clamped between zero and the zone's maximum mass flow rate."*

**[SLIDE: Anti-windup — code snippet or diagram]**

> *"A critical detail is anti-windup. Without it, if the actuator saturates — say, the VAV damper is already fully open — the integrator keeps accumulating error during that time. When the zone eventually cools, this accumulated error causes a severe undershoot."*

> *"We prevent this using conditional integration. The integrator only updates if the output is not saturated in the same direction as the error. If we're fully open and still too warm, we freeze the integrator. This keeps the controller stable even under sustained disturbances."*

**[SLIDE: AHU Coordinator — two rules]**

> *"At the system level, the AHU coordinator applies two simple but effective rules."*

> *"For supply air temperature: the AHU must serve the most demanding zone — the one requesting the coldest air. So the SAT setpoint is the minimum supply temperature request across all zones, with a safety floor of 10 degrees."*

> *"For outdoor air: we implement a simplified demand-controlled ventilation strategy. The outdoor air fraction is proportional to how close the worst-case zone CO₂ is to the 800 ppm target. If CO₂ is low, we supply minimum ventilation — 15% — as required by code. If CO₂ is at or above the target, we go to full outdoor air."*

**[SLIDE: Humidity override — sliding scale with dead-band]**

> *"To handle humidity, each zone controller includes an override. Previously we used simple binary logic, but in Colombo's climate, this logic caused chronic over-cooling by permanently locking the AHU into dehumidification mode."*

> *"Our current implementation uses a sliding scale with a 5% dead-band. If relative humidity is within 5% of the target, the supply air remains at 14 degrees. Between 5% and 10% excess, it linearly scales down to 13 degrees for mild dehumidification. Above 10% excess, it drops to 12 degrees for aggressive dehumidification."*

---

## SEGMENT 6 — Code Walkthrough (Screen Recording)
**Format: Screen recording — VS Code or file explorer**  
**Duration: ~1 minute 30 seconds**

---

**[RECORDING: Show project folder structure in VS Code or file explorer]**

> *"Here's a quick look at the codebase. The project is cleanly structured with separation of concerns."*

> *"main.py is the entry point — it handles the EnergyPlus API connection and the orchestrator loop."*

> *"Under the controllers folder, zone_controller.py defines the base PI class with the anti-windup logic. Zone 1 through 5 inherit from it, with Zone 4 — the server room — having a special override that enforces a 30-percent minimum airflow at all times."*

> *"ahu.py implements the AHU coordinator — it's a single function that takes the list of zone requests and returns the SAT setpoint and outdoor air flow command."*

**[RECORDING: Briefly open zone_controller.py and scroll through compute() method]**

> *"Here you can see the core compute method — the PI law, the anti-windup conditional, and the humidity SAT request being calculated and returned on every timestep."*

> *"The estimation folder contains the EKF scaffold — the state vector and covariance matrices are defined, but as mentioned, the physics Jacobians are not yet implemented. The system falls back to PI-only control gracefully if the EKF raises a NotImplementedError."*

---

## SEGMENT 7 — Running the Simulation (Screen Recording)
**Format: Screen recording — terminal**  
**Duration: ~45 seconds**

---

**[RECORDING: Open PowerShell terminal, activate venv, run python main.py — show output lines scrolling]**

> *"Running the simulation is straightforward. We activate the virtual environment, then run main.py. EnergyPlus launches and the Python callback fires at every zone timestep."*

> *"You can see the log lines as the simulation progresses — zone temperatures, commands, and AHU state at each 10-minute timestep. The full annual simulation — 365 days at 6 timesteps per hour — completes in a few minutes."*

> *"The result is a CSV file in the out directory — control_log.csv — which we'll now analyse."*

---

## SEGMENT 8 — Results: Plots (Screen Recording)
**Format: Screen recording — visualize.py output**  
**Duration: ~2 minutes**

---

**[RECORDING: Run python visualize.py — show the three dark-themed matplotlib windows appear]**

> *"Running the visualisation script opens three interactive plots for the simulation period."*

**[Focus on Temperature plot]**

> *"The first plot shows zone temperatures over time. The horizontal reference line at 24 degrees is the cooling setpoint. You can see all five zones tracking closely to this target — the rolling 24-hour mean lines sit right at the setpoint for most of the year. The server room, Zone 4, occasionally runs slightly cooler because of its guaranteed minimum airflow, which is intentional."*

**[Focus on Relative Humidity plot]**

> *"The relative humidity plot shows the impact of Colombo's climate. Humidity is the dominant challenge here. The humidity override kicks in frequently, pulling the SAT down to 12 degrees to drive dehumidification. Despite this, you can see some zones — particularly the open office — occasionally touch the upper edge of the comfort band during peak outdoor humidity periods."*

**[Focus on CO₂ plot]**

> *"The CO₂ plot shows levels staying well below the 1000 ppm ASHRAE limit across all zones. The demand-controlled ventilation strategy is working — outdoor air increases when CO₂ builds up during occupied hours and reduces during nights and weekends."*

---

## SEGMENT 9 — Results: Analysis Report (Screen Recording)
**Format: Screen recording — terminal running analyse_results.py**  
**Duration: ~2 minutes**

---

**[RECORDING: Run `python analyse_results.py` in terminal — script starts printing, scroll slowly section by section]**

> *"The analysis script gives us a full quantitative breakdown of system performance across every metric. Let's walk through it section by section."*

---

**[TERMINAL: TEMPERATURE section scrolls into view]**

> *"The temperature report shows five columns we care about most. The ±2°C column tells us the percentage of all timesteps where a zone sits within one degree of the 24-degree setpoint — our measure of tight control quality. The final column, is the same thing but restricted to occupied hours only — Monday to Friday, 8am to 6pm — which is when thermal comfort actually matters for the building's occupants."*



---

**[TERMINAL: CO₂ section scrolls into view]**

> *"The CO₂ report shows mean and peak concentrations alongside two compliance thresholds. The first is our own design target of 800 ppm. The second is the ASHRAE 62.1 indicative limit of 1000 ppm. The MaxRun column is particularly important — it tells us the longest continuous stretch, in hours, that any zone spent above 1000 ppm. A value of zero here means the system never allowed a sustained air quality violation."*

---

**[TERMINAL: HUMIDITY section scrolls into view]**

> *"The humidity section is the most challenging metric in this climate. We're reporting the percentage of time each zone spends inside the ASHRAE 55 optimal band — 40 to 60 percent relative humidity. Given that Colombo's outdoor humidity regularly sits above 80 percent, this is a direct test of the dehumidification strategy. The sliding-scale SAT override we implemented is the primary mechanism keeping these numbers in range."*

---

**[TERMINAL: AIRFLOW UTILISATION section scrolls into view]**

> *"Airflow utilisation tells us how hard the VAV system is working. The AvgUtil column shows mean flow as a percentage of each zone's maximum capacity. The Saturated column shows how often the VAV damper was fully open — sustained saturation in the same zone would indicate an undersized system or an overly aggressive controller. The AtZero column shows how often the controller cut airflow entirely — expected overnight and on weekends."*

> *"Notice Zone 4 — the server room — which has a non-zero minimum airflow enforced at all times by its safety floor. That's visible here as a much higher baseline utilisation compared to the other zones."*

---

**[TERMINAL: AHU COMMANDS section scrolls into view]**

> *"The AHU commands section shows the distribution of supply air temperature setpoints. The temperature bands let us see how the AHU was operating — specifically, how frequently the humidity override was pulling the SAT down to 12 or 13 degrees versus leaving it at the standard 14 degrees. This directly reflects how often the dehumidification logic was actively engaged over the full year."*
 
---

**[TERMINAL: Scroll to OVERALL PERFORMANCE SCORECARD section]**

> *"Finally, the scorecard. Each zone gets a combined score — weighted 40% temperature compliance, 35% CO₂ compliance, and 25% humidity compliance — and translated into a letter grade. A is 90 and above, B is 75 and above, C is 60, and D below that."*

**[TERMINAL: Scroll to COMPLIANCE SUMMARY section — bar chart lines visible]**

> *"Below the zone grades is the system-wide compliance summary. The four key metrics — temperature within one degree during occupied hours, CO₂ below 800 ppm during occupied hours, CO₂ below 1000 ppm at all times, and humidity in the optimal band — are each given a pass, warn, or fail tag. These represent the headline results of the project against the ASHRAE standards we set as our benchmarks at the start."*

---


## SEGMENT 10 — Live Dashboard (Screen Recording)
**Format: Screen recording — browser with dashboard.html**  
**Duration: ~1 minute**

---

**[RECORDING: Open dashboard.html in browser — drag and drop control_log.csv — dashboard loads]**

> *"Finally, we built an interactive web dashboard for live playback of the simulation log. Dropping the control_log CSV into the dashboard loads the full dataset."*

> *"The zone cards on the left show real-time temperature, humidity, CO₂, and airflow for each zone as the simulation plays back. The status dots pulse green for normal conditions, amber for warnings, and red for critical violations."*

> *"The AHU panel on the right shows the supply air temperature setpoint, outdoor air mass flow, and the worst-zone CO₂ driving the ventilation decision."*

> *"The charts at the bottom plot rolling history for all five zones simultaneously — you can select individual zones from the dropdown to focus on specific areas. The playback speed goes up to 500 times real-time, so you can watch an entire day of building operation in seconds."*

---

## SEGMENT 11 — Conclusion & Future Work
**Format: Slide**  
**Duration: ~1 minute**

---

**[SLIDE: Summary of what was achieved]**

> *"To summarise what was delivered in this project:"*

> *"We designed and implemented a fully functional decentralised HVAC control system for a five-zone commercial building, simulated in EnergyPlus with Python driving the control logic at every timestep."*

> *"The PI controller with anti-windup maintains zone temperatures close to the 24-degree setpoint. The AHU coordinator resolves supply air temperature and ventilation rate across all zones simultaneously. The humidity override provides an automatic dehumidification response that is essential for tropical operation."*

> *"Performance analysis shows decent results overall across all zones on the combined comfort, air quality, and humidity scorecard."*

**[SLIDE: What was not implemented + future work]**

> *"The Extended Kalman Filter state estimator was designed in full — the augmented state vector, the physical sub-models for thermal, moisture, and CO₂ dynamics, and the initialisation parameters are all specified and scaffolded in the codebase. Implementation of the full Jacobian and the recursive predict-update cycle was not completed within the project timeline."*

> *"If taken forward, the EKF would enable the system to estimate hidden zone parameters like thermal capacitance and occupant heat gain — allowing the controller to adapt to changing conditions without explicit occupancy schedules."*

> *"Other natural extensions include model predictive control using the identified zone models, energy consumption optimisation, and integration with real building management system hardware."*

**[SLIDE: Thank you / contact / references]**

> *"Thank you for watching. The full source code, EnergyPlus model, and simulation data are available in the project repository."*

---

---

## Appendix: Scene-by-Scene Checklist

| # | Scene | Type | Key Visual | Approx Time |
|---|---|---|---|---|
| 1 | Title & intro | Slide | Project title, name | 45s |
| 2 | Problem & objectives | Slide | Bullet points, climate context | 1m 30s |
| 3 | Building energy model | Slide | Building layout diagram | 1m |
| 4 | System architecture | Slide | Block diagram + timestep loop | 1m 30s |
| 5 | Control design | Slide | PI equation, anti-windup, AHU rules, humidity override | 2m |
| 6 | Code walkthrough | Screen recording | VS Code file tree + zone_controller.py | 1m 30s |
| 7 | Running the simulation | Screen recording | Terminal — main.py output | 45s |
| 8 | Results — plots | Screen recording | visualize.py — 3 figures | 2m |
| 9 | Results — analysis | Screen recording | analyse_results.py terminal output | 1m 30s |
| 10 | Dashboard demo | Screen recording | dashboard.html playback | 1m |
| 11 | Conclusion | Slide | Summary, limitations, future work | 1m |
| **Total** | | | | **~13m** |

---

## Tips for Recording

- **Terminal**: Use a large font size (18pt+), dark background. Run `analyse_results.py` and scroll slowly.
- **Plots**: Maximise the matplotlib windows. Hover over lines while speaking to show interactivity.
- **Dashboard**: Pre-load the CSV before recording to avoid waiting. Set playback to 100× for the demo.
- **Code**: Keep the editor in a dark theme. Fold large classes and open only the relevant methods.
- **Voice**: Pause after each sentence. Speak to the visuals — reference what's on screen while narrating.

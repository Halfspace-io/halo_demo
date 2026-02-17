# Offshore Wind Re-planner Demo App

## Overview
A demo application that replans offshore wind farm maintenance schedules when breakdowns occur, optimizing for revenue while respecting weather constraints and resource limitations. All data is stored in flat JSON files in `backend/data/` directory.

## Architecture

### Frontend (JavaScript)
- **Framework**: Vanilla JavaScript or lightweight framework (React/Vue) for simplicity
- **Visualization**: Interactive Gantt chart/timeline showing:
  - Original schedule
  - Breakdown event (highlighted)
  - Optimized new schedule
  - Weather windows (days when maintenance is possible)
  - Revenue impact visualization
- **UI Components**:
  - Schedule timeline view
  - Breakdown input form (windmill ID, severity, time)
  - Before/after comparison
  - Revenue metrics display

### Backend (Python with OR-Tools)
- **Solver**: Google OR-Tools CP-SAT solver for constraint programming
- **Data Source**: All data files read from `backend/data/` directory
- **Model Components**:
  - **Tasks**: Maintenance jobs with duration, revenue, dependencies
  - **Breakdown**: New urgent task with time window constraints (from `breakdown.json`)
  - **Weather Constraints**: Binary variables for maintenance feasibility per day (from `weather.json`)
  - **Resource Constraints**: Limited crews/boats with travel time between locations (from `resources.json` and `distances.json`)
  - **Objective**: Maximize revenue (minimize lost revenue from delays + breakdown downtime)

### Data Structure (Flat Files - stored in `backend/data/`)
- **Schedule Data** (`backend/data/schedule.json`): Existing maintenance tasks
  - Task ID, windmill ID, duration, start time window, revenue value, dependencies
  - **Output format**: The optimized schedule will be returned in the same format as this file
- **Weather Forecast** (`backend/data/weather.json`): Daily wind speed forecasts
  - Date, wind speed, wave height threshold check
  - Used to determine maintenance feasibility constraints
- **Breakdown Event** (`backend/data/breakdown.json`): Disruption details (input for re-planning)
  - Windmill ID, breakdown time, urgency, estimated repair duration
  - This file triggers the re-planning optimization
- **Windmills** (`backend/data/windmills.json`): Asset information
  - Windmill ID, location (coordinates), capacity, revenue per MWh
  - **Additional fields needed**: `rated_wind_speed_ms` (wind speed at full capacity, typically 12-15 m/s)
  - **Optional fields**: `cut_in_speed_ms` (minimum wind speed, e.g., 3-4 m/s), `cut_out_speed_ms` (maximum safe wind speed, e.g., 25 m/s)
  - Used for revenue calculations with cubic wind speed relationship
- **Resources** (`backend/data/resources.json`): Available crews/boats
  - Resource ID, type, daily working hours, qualifications
  - **Constraint source**: Limits available crews and their capabilities
- **Distance Matrix** (`backend/data/distances.json`): Travel times between windmills
  - From windmill, to windmill, travel time (hours)
  - **Constraint source**: Affects scheduling when crews move between locations

## Implementation Plan

### 1. Data Models & File Structure
- Define JSON schemas for all input files
- All data files stored in `backend/data/` directory
- **Revenue Calculation** (cubic relationship):
  - `Power (MW) = capacity × min(1.0, (wind_speed / rated_wind_speed)³)`
  - `Energy (MWh) = Power × hours`
  - `Revenue = Energy × price_per_MWh`
  - Or compactly: `revenue = capacity × min(1.0, (wind_speed / rated_wind_speed)³) × price_per_MWh × hours`
  - **Cut-in speed**: Below this (e.g., 3-4 m/s), no power generation (revenue = 0)
  - **Cut-out speed**: Above this (e.g., 25 m/s), turbine shuts down for safety (revenue = 0)
  - **Rated wind speed**: Wind speed at which turbine reaches full capacity (typically 12-15 m/s for offshore)

### 2. OR-Tools Optimization Model
- **Data Loading**: 
  - Read all input files from `backend/data/` directory
  - Load existing schedule from `schedule.json`
  - Load breakdown event from `breakdown.json` (triggers re-planning)
  - Load constraints from `resources.json`, `weather.json`, `distances.json`
  - Load windmill data from `windmills.json` for revenue calculations
- **Variables**:
  - Task start times (integer variables)
  - Task assignments (binary if task can be scheduled)
  - Weather feasibility (binary per day/task)
  - Resource assignments (which crew/boat handles which task)
- **Constraints** (from data files):
  - **Task Duration**: Each task has fixed duration (from `schedule.json`)
  - **Weather Threshold**: `wind_speed < threshold` for maintenance (from `weather.json`)
    - Use `maintenance_possible` flag and `wind_threshold_ms` from weather data
  - **Resource Constraints** (from `resources.json`):
    - Limited maintenance crews/boats (number of resources in file)
    - One task per crew at a time (crew cannot be in two places simultaneously)
    - Crew availability windows (working hours, rest periods from resource data)
    - Qualification matching (task requirements vs crew qualifications)
  - **Travel Time** (from `distances.json`):
    - Time to travel between windmills (depends on distance matrix)
    - If task ends at windmill A, next task at windmill B must start >= travel_time(A,B) later
    - Include port travel times for crew deployment
  - **Windmill Occupancy**: One maintenance task per windmill at a time
  - **Breakdown Urgency** (from `breakdown.json`):
    - Breakdown must be scheduled within `urgency_window_hours` from `breakdown_time`
    - Breakdown becomes a new urgent task with high priority
  - **Time Windows**: Tasks may have earliest start and latest finish times (from `schedule.json`)
  - **Task Dependencies**: Some tasks may require others to complete first (from `schedule.json`)
- **Objective Function**:
  - Maximize: `Σ(revenue from completed tasks) - Σ(lost revenue from delays) - breakdown_downtime_cost`
  - **Lost revenue from breakdown** = `Σ(revenue_per_hour × downtime_hours)` where:
    - `revenue_per_hour = capacity × min(1.0, (wind_speed/rated_wind_speed)³) × price_per_MWh`
    - Apply cut-in/cut-out speed constraints (revenue = 0 if wind < cut_in or wind > cut_out)
  - **Lost revenue from delays** = difference between original schedule revenue and delayed schedule revenue
    - Calculate revenue for each day using cubic formula based on forecast wind speed
    - Compare original task timing vs. delayed task timing
  - Use windmill capacity, rated_wind_speed, and revenue data from `windmills.json`
  - Use weather forecast from `weather.json` to calculate expected revenue per day
- **Output**:
  - Generate optimized schedule in same format as `schedule.json`
  - Include all original tasks with updated start times
  - Include breakdown repair task as new scheduled task
  - Output to file or return via API in JSON format matching `schedule.json` structure

### 3. Backend API (Python Flask/FastAPI)
- **Data Source**: All data files read from `backend/data/` directory
- Endpoint: `POST /replan` - reads `breakdown.json`, returns optimized schedule
  - Loads breakdown event from `backend/data/breakdown.json`
  - Runs optimization with all constraints from data files
  - Returns optimized schedule in same format as `schedule.json`
- Endpoint: `GET /schedule` - returns current schedule from `backend/data/schedule.json`
- Endpoint: `GET /weather` - returns weather forecast from `backend/data/weather.json`
- Endpoint: `GET /resources` - returns resources from `backend/data/resources.json`
- Revenue calculation service (uses `windmills.json` and `weather.json`)

### 4. Frontend Application
- Load initial schedule and weather data from backend API
- Breakdown input interface (can update `breakdown.json` via API)
- Call backend API to get optimized plan
- Render timeline comparison (original vs optimized)
- Display revenue impact metrics

### 5. Demo Data & Configuration
- Sample wind farm with 5-10 windmills
- 2-4 week planning horizon
- Sample maintenance tasks
- Weather forecast data
- Breakdown scenario examples

## File Structure
```
sentinelOrchestrator/
├── frontend/
│   ├── index.html
│   ├── js/
│   │   ├── app.js
│   │   ├── schedule-viewer.js
│   │   └── api-client.js
│   └── css/
│       └── style.css
├── backend/
│   ├── app.py (Flask/FastAPI)
│   ├── optimizer.py (OR-Tools model)
│   ├── revenue_calculator.py
│   ├── models.py (data models)
│   └── data/
│       ├── schedule.json
│       ├── weather.json
│       ├── windmills.json
│       ├── resources.json
│       ├── distances.json
│       └── breakdown.json (input)
└── README.md
```

## Additional Constraints to Consider
- **Travel Time**: Distance matrix between windmills (affects crew scheduling)
- **Crew Working Hours**: Daily working hours (e.g., 8-10 hours/day, rest periods)
- **Port Access**: Crews must start/end at port, affecting first/last tasks of day
- **Equipment Availability**: Specialized equipment may be limited (e.g., crane boats)
- **Crew Qualifications**: Different crews may have different skill sets
- **Daylight Requirements**: Some tasks may require daylight hours
- **Seasonal Constraints**: Certain maintenance only possible in specific seasons
- **Budget Limits**: Maximum cost per period (if cost data available)

## Key Assumptions (for demo)
- Time granularity: Daily (can be extended to hourly)
- Weather threshold: Fixed wind speed limit (e.g., 15 m/s) for maintenance feasibility
- **Revenue model**: **Cubic relationship with wind speed** (power ∝ wind_speed³)
  - Rated wind speed: 12-15 m/s (turbine reaches full capacity)
  - Cut-in speed: 3-4 m/s (below this, no generation)
  - Cut-out speed: 25 m/s (above this, turbine shuts down)
- 2-3 maintenance crews available (resource constraint)
- Travel time between windmills: Based on distance matrix
- Crews work 8-10 hour days with rest periods
- Tasks are independent except for resource conflicts and dependencies


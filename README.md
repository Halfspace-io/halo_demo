# Offshore Wind Re-planner Demo

A demo application that replans offshore wind farm maintenance schedules when breakdowns occur, optimizing for revenue while respecting weather constraints and resource limitations.

## Features

- **Revenue-based Optimization**: Uses cubic wind speed relationship to calculate revenue
- **Breakdown Handling**: Automatically determines optimal time to fix breakdowns based on revenue impact
- **Overdue Penalties**: Tasks can extend beyond deadlines with configurable penalties
- **Resource Constraints**: Respects limited crews, qualifications, and travel times
- **Weather Constraints**: Considers weather windows for maintenance feasibility
- **Visual Timeline**: Interactive frontend showing original vs optimized schedules with overdue periods highlighted in red

## Architecture

- **Backend**: Python with Flask API and OR-Tools CP-SAT solver
- **Frontend**: Vanilla JavaScript with interactive timeline visualization
- **Data**: All data stored in flat JSON files in `backend/data/`

## Setup

### Backend

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Run the Flask server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

### Frontend

1. Open `frontend/index.html` in a web browser
2. Or use a local web server:
```bash
cd frontend
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser

## Usage

1. Configure breakdown event in `backend/data/breakdown.json`
2. Set overdue penalty (or use default of €3000 per day - which roughly equals revenue from 7h at 8M/s)
3. Click "Re-plan Schedule" to optimize
4. View optimized schedule with overdue periods highlighted in red

## Data Files

All data files are stored in `backend/data/`:

- `schedule.json`: Existing maintenance tasks
- `breakdown.json`: Breakdown event (triggers re-planning)
- `weather.json`: Weather forecasts
- `windmills.json`: Windmill specifications
- `resources.json`: Available crews/boats
- `distances.json`: Travel time matrix

## API Endpoints

- `GET /schedule`: Get current schedule
- `GET /weather`: Get weather forecast
- `GET /resources`: Get available resources
- `GET /windmills`: Get windmill data
- `POST /replan`: Re-plan schedule (accepts `overdue_penalty_per_day` parameter)
- `GET /calculate-penalty`: Calculate default overdue penalty

## Revenue Calculation

Revenue is calculated using cubic relationship with wind speed:

```
Power (MW) = capacity × min(1.0, (wind_speed / rated_wind_speed)³)
Revenue = Power × price_per_MWh × hours
```

## License

Demo application for educational purposes.


# Sentinel Orchestrator — Offshore Wind Re-planner

A demo application that replans offshore wind farm maintenance schedules when breakdowns occur, optimizing for revenue while respecting weather constraints and resource limitations.

## Features

- **Revenue-based Optimization**: Uses cubic wind speed relationship to calculate revenue
- **Breakdown Handling**: Automatically determines optimal time to fix breakdowns based on revenue impact
- **Overdue Penalties**: Tasks can extend beyond deadlines with configurable penalties
- **Resource Constraints**: Respects limited crews, qualifications, and travel times
- **Weather Constraints**: Considers weather windows for maintenance feasibility
- **Visual Timeline**: Interactive Gantt chart showing original vs optimized schedules
- **AI Analysis**: LLM-powered explanations for optimization decisions (requires OpenAI API key)

## Architecture

- **Backend**: Python with FastAPI + OR-Tools CP-SAT solver, managed with `uv`
- **Frontend**: Svelte 5 + Vite with sidebar layout
- **Data**: All data stored in flat JSON files in `backend/data/`

## Setup

### Backend

```bash
cd backend
uv sync
uv run uvicorn app:app --reload --port 5000
```

The API will be available at `http://localhost:5000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open the URL shown in the terminal (typically `http://localhost:5173`).

### AI Explanations (optional)

Set the `OPENAI_API_KEY` environment variable to enable LLM-powered schedule analysis:

```bash
export OPENAI_API_KEY=sk-...
```

## Running Tests

```bash
cd backend
uv sync --extra dev
uv run pytest tests/ -v
```

## Data Files

All data files are stored in `backend/data/`:

- `schedule.json`: Existing maintenance tasks
- `breakdown.json`, `breakdown2.json`: Breakdown events (trigger re-planning)
- `weather.json`: Weather forecasts
- `windmills.json`: Windmill specifications
- `resources.json`: Available crews/boats
- `distances.json`: Travel time matrix

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/schedule` | Get current schedule |
| GET | `/weather` | Get weather forecast |
| GET | `/resources` | Get available resources |
| GET | `/windmills` | Get windmill data |
| GET | `/breakdown` | Get breakdown events |
| GET | `/calculate-penalty` | Get default overdue penalty |
| POST | `/replan` | Re-plan schedule with breakdown |
| POST | `/calculate-objective` | Calculate costs for current schedule |
| POST | `/explain-optimization` | Generate AI explanation |

## Revenue Calculation

Revenue is calculated using cubic relationship with wind speed:

```
Power (MW) = capacity * min(1.0, (wind_speed / rated_wind_speed)^3)
Revenue = Power * price_per_MWh * hours
```

## License

Demo application for educational purposes.

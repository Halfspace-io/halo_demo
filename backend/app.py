"""FastAPI backend for the offshore wind re-planner."""
import json
import traceback
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from calculations import ObjectiveValueCalculator, RevenueCalculator
from llm_reasoning import GenerateLLMExplanation
from models import DataLoader, Windmill
from optimizer import ScheduleOptimizer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent / "data"
data_loader = DataLoader(str(DATA_DIR))
llm_explainer = GenerateLLMExplanation()


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class ReplanRequest(BaseModel):
    overdue_penalty_per_day: Optional[float] = None
    overtime_cost_per_hour: float = 500
    spill_over_penalty_routine: float = 5000
    spill_over_penalty_repairs: float = 10000
    breakdown_file: Optional[str] = "breakdown.json"


class CalculateObjectiveRequest(BaseModel):
    overdue_penalty_per_day: float = 3000
    overtime_cost_per_hour: float = 500
    spill_over_penalty_routine: float = 5000
    spill_over_penalty_repairs: float = 10000


class ExplainOptimizationRequest(BaseModel):
    original_schedule: dict = {}
    optimized_schedule: dict = {}
    breakdown_info: Optional[dict] = None
    weather_data: dict = {}
    cost_parameters: dict = {}
    cost_metrics: dict = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_revenue_matrix(windmills: List[Windmill]) -> Dict[str, Dict[str, float]]:
    """Generate and save revenue matrix, and return it."""
    revenue_matrix = RevenueCalculator.generate_revenue_matrix(windmills)
    generated_dir = DATA_DIR / "generated"
    generated_dir.mkdir(exist_ok=True)
    with open(generated_dir / "revenue_matrix.json", "w") as f:
        json.dump(revenue_matrix, f, indent=2)
    return revenue_matrix


# ---------------------------------------------------------------------------
# GET endpoints
# ---------------------------------------------------------------------------

@app.get("/schedule")
def get_schedule():
    try:
        with open(DATA_DIR / "schedule.json") as f:
            return json.load(f)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/weather")
def get_weather():
    try:
        with open(DATA_DIR / "weather.json") as f:
            return json.load(f)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/resources")
def get_resources():
    try:
        with open(DATA_DIR / "resources.json") as f:
            return json.load(f)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/windmills")
def get_windmills():
    try:
        with open(DATA_DIR / "windmills.json") as f:
            return json.load(f)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/breakdown")
def get_breakdown():
    try:
        breakdowns = []

        breakdown_path = DATA_DIR / "breakdown.json"
        if breakdown_path.exists():
            with open(breakdown_path) as f:
                breakdown_data = json.load(f)
            if "breakdown_event" in breakdown_data:
                breakdowns.append(breakdown_data["breakdown_event"])

        breakdown2_path = DATA_DIR / "breakdown2.json"
        if breakdown2_path.exists():
            with open(breakdown2_path) as f:
                breakdown2_data = json.load(f)
            if "breakdown_event" in breakdown2_data:
                breakdowns.append(breakdown2_data["breakdown_event"])

        return {"breakdowns": breakdowns}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/calculate-penalty")
def calculate_penalty():
    return {"penalty_per_day": 3000.0}


# ---------------------------------------------------------------------------
# POST endpoints
# ---------------------------------------------------------------------------

@app.post("/calculate-objective")
def calculate_objective(body: CalculateObjectiveRequest):
    try:
        (
            tasks,
            planning_horizon_start,
            planning_horizon_end,
            spill_over_cutoff_date,
        ) = data_loader.load_schedule()
        windmills = data_loader.load_windmills()
        weather_forecasts, _ = data_loader.load_weather()

        revenue_matrix = _generate_revenue_matrix(windmills)

        calculator = ObjectiveValueCalculator(
            planning_horizon_start=planning_horizon_start,
            spill_over_cutoff_date=spill_over_cutoff_date,
            tasks=tasks,
            windmills=windmills,
            weather_forecasts=weather_forecasts,
            revenue_matrix=revenue_matrix,
            overdue_penalty_per_day=body.overdue_penalty_per_day,
            overtime_cost_per_hour=body.overtime_cost_per_hour,
            spill_over_penalty_routine=body.spill_over_penalty_routine,
            spill_over_penalty_repairs=body.spill_over_penalty_repairs,
            breakdown=None,
        )

        return calculator.calculate_all()

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/replan")
def replan(body: ReplanRequest):
    try:
        (
            tasks,
            planning_horizon_start,
            planning_horizon_end,
            spill_over_cutoff_date,
        ) = data_loader.load_schedule()
        windmills = data_loader.load_windmills()
        resources = data_loader.load_resources()
        weather_forecasts, _ = data_loader.load_weather()
        distances = data_loader.load_distances()

        revenue_matrix = _generate_revenue_matrix(windmills)

        breakdown = None
        if body.breakdown_file:
            breakdown = data_loader.load_breakdown_from_file(body.breakdown_file)

        optimizer = ScheduleOptimizer(
            planning_horizon_start=planning_horizon_start,
            planning_horizon_end=planning_horizon_end,
            spill_over_cutoff_date=spill_over_cutoff_date,
            tasks=tasks,
            windmills=windmills,
            resources=resources,
            weather_forecasts=weather_forecasts,
            distances=distances,
            revenue_matrix=revenue_matrix,
            overdue_penalty_per_day=int(body.overdue_penalty_per_day) if body.overdue_penalty_per_day is not None else None,
            overtime_cost_per_hour=int(body.overtime_cost_per_hour),
            spill_over_penalty_routine=int(body.spill_over_penalty_routine),
            spill_over_penalty_repairs=int(body.spill_over_penalty_repairs),
            breakdown=breakdown,
        )

        solution, cost_metrics_for_llm_explanation = optimizer.solve()

        if "error" in solution:
            return JSONResponse(status_code=400, content=solution)

        optimized_schedule = {
            "tasks": [],
            "planning_horizon_start": solution.get("planning_horizon_start"),
            "planning_horizon_end": solution.get("planning_horizon_end"),
            "spill_over_cutoff_date": spill_over_cutoff_date,
            "objective_value": solution.get("objective_value"),
            "downtime_cost_for_breakdown": solution.get("downtime_cost_for_breakdown"),
            "downtime_cost_for_scheduled_tasks": solution.get("downtime_cost_for_scheduled_tasks"),
            "revenue_calculation_dates": solution.get("revenue_calculation_dates"),
            "cost_of_overtime": solution.get("cost_of_overtime"),
            "cost_of_spill_over": solution.get("cost_of_spill_over"),
            "cost_metrics_for_llm": cost_metrics_for_llm_explanation,
        }

        for task_sol in solution["tasks"]:
            original_task = next(t for t in tasks if t.id == task_sol["id"])
            optimized_task = {
                "id": original_task.id,
                "windmill_id": original_task.windmill_id,
                "task_type": original_task.task_type,
                "description": original_task.description,
                "duration_hours": original_task.duration_hours,
                "start_time": task_sol["start_time"],
                "latest_finish": original_task.latest_finish,
                "original_latest_finish": original_task.latest_finish,
                "required_qualifications": original_task.required_qualifications,
                "dependencies": original_task.dependencies,
            }
            if "overdue_info" in task_sol:
                optimized_task["overdue_info"] = task_sol["overdue_info"]
            optimized_schedule["tasks"].append(optimized_task)

        if solution.get("breakdown"):
            breakdown_sol = solution["breakdown"]
            optimized_schedule["tasks"].append(
                {
                    "id": breakdown.id,
                    "windmill_id": breakdown.windmill_id,
                    "task_type": "breakdown_repair",
                    "description": breakdown.description,
                    "duration_hours": breakdown.estimated_repair_duration_hours,
                    "start_time": breakdown_sol["start_time"],
                    "latest_finish": breakdown_sol["finish_time"],
                    "required_qualifications": breakdown.required_qualifications,
                    "dependencies": [],
                    "is_breakdown": True,
                }
            )

        return optimized_schedule

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": traceback.format_exc()},
        )


@app.post("/explain-optimization")
def explain_optimization(body: ExplainOptimizationRequest):
    if not llm_explainer.is_available():
        return JSONResponse(
            status_code=500,
            content={
                "error": "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
            },
        )

    result = llm_explainer.explain_optimization(
        original_schedule=body.original_schedule,
        optimized_schedule=body.optimized_schedule,
        breakdown_info=body.breakdown_info,
        weather_data=body.weather_data,
        cost_parameters=body.cost_parameters,
        cost_metrics_on_task_level=body.cost_metrics,
    )

    if "error" in result:
        return JSONResponse(status_code=500, content=result)

    return result


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)

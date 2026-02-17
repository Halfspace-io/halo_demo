"""Flask API for the offshore wind re-planner."""
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
from models import DataLoader
from optimizer import ScheduleOptimizer
from calculations import RevenueCalculator, ObjectiveValueCalculator
from llm_reasoning import GenerateLLMExplanation
from typing import List, Dict
from models import Windmill

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

data_loader = DataLoader("backend/data")

# Initialize LLM explanation generator
llm_explainer = GenerateLLMExplanation()


@app.route('/schedule', methods=['GET'])
def get_schedule():
    """Get current schedule."""
    try:
        schedule_path = Path("backend/data/schedule.json")
        with open(schedule_path, 'r') as f:
            schedule = json.load(f)
        return jsonify(schedule)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/weather', methods=['GET'])
def get_weather():
    """Get weather forecast."""
    try:
        weather_path = Path("backend/data/weather.json")
        with open(weather_path, 'r') as f:
            weather = json.load(f)
        return jsonify(weather)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/resources', methods=['GET'])
def get_resources():
    """Get resources."""
    try:
        resources_path = Path("backend/data/resources.json")
        with open(resources_path, 'r') as f:
            resources = json.load(f)
        return jsonify(resources)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/windmills', methods=['GET'])
def get_windmills():
    """Get windmills."""
    try:
        windmills_path = Path("backend/data/windmills.json")
        with open(windmills_path, 'r') as f:
            windmills = json.load(f)
        return jsonify(windmills)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/breakdown', methods=['GET'])
def get_breakdown():
    """Get breakdown event(s) from all breakdown files."""
    try:
        breakdowns = []
        
        # Load breakdown.json
        breakdown_path = Path("backend/data/breakdown.json")
        if breakdown_path.exists():
            with open(breakdown_path, 'r') as f:
                breakdown_data = json.load(f)
            if 'breakdown_event' in breakdown_data:
                breakdowns.append(breakdown_data['breakdown_event'])
        
        # Load breakdown2.json
        breakdown2_path = Path("backend/data/breakdown2.json")
        if breakdown2_path.exists():
            with open(breakdown2_path, 'r') as f:
                breakdown2_data = json.load(f)
            if 'breakdown_event' in breakdown2_data:
                breakdowns.append(breakdown2_data['breakdown_event'])
        
        return jsonify({"breakdowns": breakdowns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/calculate-objective', methods=['POST'])
def calculate_objective():
    """Calculate objective value for the current schedule without optimization."""
    try:
        # Get optional parameters (same as replan)
        data = request.get_json() or {}
        overdue_penalty_per_day = data.get('overdue_penalty_per_day', 3000)
        overtime_cost_per_hour = data.get('overtime_cost_per_hour', 500)
        spill_over_penalty_routine = data.get('spill_over_penalty_routine', 5000)
        spill_over_penalty_repairs = data.get('spill_over_penalty_repairs', 10000)
        
        # Load all data
        (
            tasks,
            planning_horizon_start,
            planning_horizon_end,
            spill_over_cutoff_date
        ) = data_loader.load_schedule()
        windmills = data_loader.load_windmills()
        weather_forecasts, _ = data_loader.load_weather()
        
        revenue_matrix = generate_revenue_matrix(windmills)
        
        # Create calculator
        calculator = ObjectiveValueCalculator(
            planning_horizon_start=planning_horizon_start,
            spill_over_cutoff_date=spill_over_cutoff_date,
            tasks=tasks,
            windmills=windmills,
            weather_forecasts=weather_forecasts,
            revenue_matrix=revenue_matrix,
            overdue_penalty_per_day=overdue_penalty_per_day,
            overtime_cost_per_hour=overtime_cost_per_hour,
            spill_over_penalty_routine=spill_over_penalty_routine,
            spill_over_penalty_repairs=spill_over_penalty_repairs,
            breakdown=None  # Original schedule has no breakdown repair
        )
        
        # Calculate all terms
        result = calculator.calculate_all()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def generate_revenue_matrix(windmills: List[Windmill]) -> Dict[str, Dict[str, float]]:
    """Generate and save revenue matrix, and return it."""
    revenue_matrix = RevenueCalculator.generate_revenue_matrix(windmills)
    generated_dir = Path("backend/data/generated")
    generated_dir.mkdir(exist_ok=True)
    with open(generated_dir / "revenue_matrix.json", 'w') as f:
        json.dump(revenue_matrix, f, indent=2)
    return revenue_matrix

@app.route('/replan', methods=['POST'])
def replan():
    """Re-plan schedule based on breakdown."""
    try:
        # Get optional parameters
        data = request.get_json() or {}
        overdue_penalty_per_day = data.get('overdue_penalty_per_day')
        overtime_cost_per_hour = data.get('overtime_cost_per_hour', 500)
        spill_over_penalty_routine = data.get('spill_over_penalty_routine', 5000)
        spill_over_penalty_repairs = data.get('spill_over_penalty_repairs', 10000)
        breakdown_file = data.get('breakdown_file', 'breakdown.json')
        
        # Load all data
        (
            tasks, 
            planning_horizon_start, 
            planning_horizon_end, 
            spill_over_cutoff_date
        ) = data_loader.load_schedule()
        windmills = data_loader.load_windmills()
        resources = data_loader.load_resources()
        weather_forecasts, _ = data_loader.load_weather()
        distances = data_loader.load_distances()
        
        revenue_matrix = generate_revenue_matrix(windmills)
        
        if breakdown_file:
            breakdown = data_loader.load_breakdown_from_file(breakdown_file)
            # return jsonify({"error": "No breakdown event found"}), 400
        else:
            breakdown = None
        # Create optimizer
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
            overdue_penalty_per_day=overdue_penalty_per_day,
            overtime_cost_per_hour=overtime_cost_per_hour,
            spill_over_penalty_routine=spill_over_penalty_routine,
            spill_over_penalty_repairs=spill_over_penalty_repairs,
            breakdown=breakdown
        )
        
        # Solve
        solution, cost_metrics_for_llm_explanation = optimizer.solve()
        
        if "error" in solution:
            return jsonify(solution), 400
        
        # Format response in schedule.json format
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
            "cost_metrics_for_llm": cost_metrics_for_llm_explanation
        }
        
        # Convert solution tasks to schedule format
        for task_sol in solution["tasks"]:
            # Find original task
            original_task = next(t for t in tasks if t.id == task_sol["id"])
            
            optimized_task = {
                "id": original_task.id,
                "windmill_id": original_task.windmill_id,
                "task_type": original_task.task_type,
                "description": original_task.description,
                "duration_hours": original_task.duration_hours,
                "start_time": task_sol["start_time"],
                "latest_finish": original_task.latest_finish,  # Preserve original deadline
                "original_latest_finish": original_task.latest_finish,  # Also store as original for frontend
                "required_qualifications": original_task.required_qualifications,
                "dependencies": original_task.dependencies
            }
            
            if "overdue_info" in task_sol:
                optimized_task["overdue_info"] = task_sol["overdue_info"]
            
            optimized_schedule["tasks"].append(optimized_task)
        
        # Add breakdown as a task
        if solution.get("breakdown"):
            breakdown_sol = solution["breakdown"]
            optimized_schedule["tasks"].append({
                "id": breakdown.id,
                "windmill_id": breakdown.windmill_id,
                "task_type": "breakdown_repair",
                "description": breakdown.description,
                "duration_hours": breakdown.estimated_repair_duration_hours,
                "start_time": breakdown_sol["start_time"],
                "latest_finish": breakdown_sol["finish_time"],
                "required_qualifications": breakdown.required_qualifications,
                "dependencies": [],
                "is_breakdown": True
            })
        
        return jsonify(optimized_schedule)
    
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/calculate-penalty', methods=['GET'])
def calculate_penalty():
    """Get default overdue penalty."""
    try:
        # Hardcoded default penalty value
        default_penalty = 3000.0
        
        return jsonify({
            "penalty_per_day": default_penalty
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/explain-optimization', methods=['POST'])
def explain_optimization():
    """Generate an LLM explanation for why the optimizer chose this schedule."""
    if not llm_explainer.is_available():
        return jsonify({
            "error": "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        }), 500
    
    data = request.get_json() or {}
    
    # Extract all the context needed for explanation
    original_schedule = data.get('original_schedule', {})
    optimized_schedule = data.get('optimized_schedule', {})
    breakdown_info = data.get('breakdown_info')
    weather_data = data.get('weather_data', {})
    cost_parameters = data.get('cost_parameters', {})
    
    # Generate explanation using the LLM
    cost_metrics_on_task_level = data.get('cost_metrics', {})

    result = llm_explainer.explain_optimization(
        original_schedule=original_schedule,
        optimized_schedule=optimized_schedule,
        breakdown_info=breakdown_info,
        weather_data=weather_data,
        cost_parameters=cost_parameters,
        cost_metrics_on_task_level=cost_metrics_on_task_level
    )
    
    if "error" in result:
        return jsonify(result), 500
    
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=5000)


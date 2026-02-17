"""Shared fixtures for optimizer tests."""
import pytest
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from models import Task, Windmill, Resource, WeatherForecast, BreakdownEvent
from optimizer import ScheduleOptimizer


# =============================================================================
# SCHEDULE CONFIG FIXTURE - loads dates from schedule.json
# =============================================================================

@pytest.fixture
def schedule_config():
    """Load planning horizon and spill over dates from schedule.json."""
    schedule_path = Path(__file__).parent.parent / "data" / "schedule.json"
    with open(schedule_path, 'r') as f:
        data = json.load(f)
    return {
        "planning_horizon_start": data["planning_horizon_start"],
        "planning_horizon_end": data["planning_horizon_end"],
        "spill_over_cutoff_date": data["spill_over_cutoff_date"],
    }


@pytest.fixture
def planning_start_date(schedule_config):
    """Get planning start as datetime object."""
    return datetime.fromisoformat(schedule_config["planning_horizon_start"].replace('Z', '+00:00')).replace(tzinfo=None)


# =============================================================================
# WINDMILL FIXTURES
# =============================================================================

@pytest.fixture
def sample_windmills():
    """Create sample windmills for testing."""
    return [
        Windmill(
            id="WM001",
            name="Windmill 1",
            location={"lat": 55.5, "lon": 7.5},
            capacity_mw=5.0,
            revenue_per_mwh=100.0,
            rated_wind_speed_ms=12.0,
            cut_in_speed_ms=3.0,
            cut_out_speed_ms=25.0
        ),
        Windmill(
            id="WM002",
            name="Windmill 2",
            location={"lat": 55.6, "lon": 7.6},
            capacity_mw=5.0,
            revenue_per_mwh=100.0,
            rated_wind_speed_ms=12.0,
            cut_in_speed_ms=3.0,
            cut_out_speed_ms=25.0
        ),
        Windmill(
            id="WM003",
            name="Windmill 3",
            location={"lat": 55.7, "lon": 7.7},
            capacity_mw=5.0,
            revenue_per_mwh=100.0,
            rated_wind_speed_ms=12.0,
            cut_in_speed_ms=3.0,
            cut_out_speed_ms=25.0
        ),
    ]


# =============================================================================
# RESOURCE FIXTURES
# =============================================================================

@pytest.fixture
def sample_resources():
    """Create sample resources for testing."""
    return [
        Resource(
            id="R001",
            type="maintenance_crew",
            name="Team Alpha",
            daily_working_hours=12,
            rest_hours_after_work=2,
            qualifications=["maintenance", "repairs", "emergency_repairs"],
            base_location="harbor"
        ),
        Resource(
            id="R002",
            type="maintenance_crew",
            name="Team Beta",
            daily_working_hours=12,
            rest_hours_after_work=2,
            qualifications=["maintenance"],
            base_location="harbor"
        ),
    ]


# =============================================================================
# WEATHER FIXTURES
# =============================================================================

@pytest.fixture
def sample_weather(planning_start_date):
    """Create 14 days of sample weather data starting from planning_horizon_start."""
    forecasts = []
    for i in range(14):
        date = (planning_start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        forecasts.append(
            WeatherForecast(
                date=date,
                wind_speed_ms=8.0,  # Default moderate wind
                wave_height_m=1.0,
                maintenance_possible=True
            )
        )
    return forecasts


@pytest.fixture
def high_wind_weather(planning_start_date):
    """Create weather with high wind speeds (high revenue loss from downtime)."""
    forecasts = []
    for i in range(14):
        date = (planning_start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        forecasts.append(
            WeatherForecast(
                date=date,
                wind_speed_ms=18.0,  # High wind = high revenue
                wave_height_m=1.0,
                maintenance_possible=True
            )
        )
    return forecasts


@pytest.fixture
def impossible_weather(planning_start_date):
    """Create weather where maintenance is impossible on all days."""
    forecasts = []
    for i in range(14):
        date = (planning_start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        forecasts.append(
            WeatherForecast(
                date=date,
                wind_speed_ms=30.0,  # Above cut-out
                wave_height_m=3.0,
                maintenance_possible=False
            )
        )
    return forecasts


# =============================================================================
# REVENUE MATRIX FIXTURE
# =============================================================================

@pytest.fixture
def sample_revenue_matrix():
    """Create sample revenue matrix for windmills."""
    # Revenue per hour at each wind speed (0-25 m/s)
    # Simplified: revenue = wind_speed * 100 (within operating range)
    matrix = {}
    for wm_id in ["WM001", "WM002", "WM003"]:
        matrix[wm_id] = {}
        for wind_speed in range(26):
            if 3 <= wind_speed <= 25:  # Within cut-in to cut-out range
                matrix[wm_id][wind_speed] = wind_speed * 100
            else:
                matrix[wm_id][wind_speed] = 0
    return matrix


# =============================================================================
# TASK FIXTURES
# =============================================================================

@pytest.fixture
def single_task(planning_start_date, schedule_config):
    """Create a single simple task."""
    # Task starts 2 days after planning start, deadline 3 days after start
    task_start = planning_start_date + timedelta(days=2)
    latest_finish = planning_start_date + timedelta(days=5)
    
    return Task(
        id="TASK001",
        windmill_id="WM001",
        task_type="corrective",
        description="Test maintenance task",
        duration_hours=4,
        latest_finish=latest_finish.strftime("%Y-%m-%dT%H:%M:%S"),
        required_qualifications=["maintenance"],
        dependencies=[],
        start_time=task_start.strftime("%Y-%m-%dT08:00:00")
    )


@pytest.fixture
def multiple_tasks_same_windmill(planning_start_date, schedule_config):
    """Create multiple tasks on the same windmill (for overlap testing)."""
    task1_start = planning_start_date + timedelta(days=2)
    task2_start = planning_start_date + timedelta(days=3)
    latest_finish = datetime.fromisoformat(
        schedule_config["spill_over_cutoff_date"].replace('Z', '+00:00')
    ).replace(tzinfo=None)
    
    return [
        Task(
            id="TASK001",
            windmill_id="WM001",
            task_type="corrective",
            description="First task on WM001",
            duration_hours=4,
            latest_finish=latest_finish.strftime("%Y-%m-%dT18:00:00"),
            required_qualifications=["maintenance"],
            dependencies=[],
            start_time=task1_start.strftime("%Y-%m-%dT08:00:00")
        ),
        Task(
            id="TASK002",
            windmill_id="WM001",
            task_type="corrective",
            description="Second task on WM001",
            duration_hours=4,
            latest_finish=latest_finish.strftime("%Y-%m-%dT18:00:00"),
            required_qualifications=["maintenance"],
            dependencies=[],
            start_time=task2_start.strftime("%Y-%m-%dT08:00:00")
        ),
    ]


# =============================================================================
# BREAKDOWN FIXTURES
# =============================================================================

@pytest.fixture
def sample_breakdown(planning_start_date):
    """Create a sample breakdown event."""
    # Breakdown occurs 1 day after planning start
    breakdown_time = planning_start_date + timedelta(days=1, hours=10)
    
    return BreakdownEvent(
        id="BREAKDOWN001",
        windmill_id="WM001",
        breakdown_time=breakdown_time.strftime("%Y-%m-%dT%H:%M:%S"),
        description="Emergency turbine repair",
        estimated_repair_duration_hours=4,
        required_qualifications=["repairs"]
    )


# =============================================================================
# OPTIMIZER FIXTURES
# =============================================================================

@pytest.fixture
def simple_optimizer(sample_windmills, sample_resources, sample_weather, 
                     sample_revenue_matrix, single_task, schedule_config):
    """Create a simple optimizer with one task and no breakdown."""
    return ScheduleOptimizer(
        planning_horizon_start=schedule_config["planning_horizon_start"],
        planning_horizon_end=schedule_config["planning_horizon_end"],
        spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
        tasks=[single_task],
        windmills=sample_windmills,
        resources=sample_resources,
        weather_forecasts=sample_weather,
        distances={},
        revenue_matrix=sample_revenue_matrix,
    )


@pytest.fixture
def optimizer_with_breakdown(sample_windmills, sample_resources, sample_weather,
                              sample_revenue_matrix, sample_breakdown, schedule_config):
    """Create an optimizer with a breakdown event but no regular tasks."""
    return ScheduleOptimizer(
        planning_horizon_start=schedule_config["planning_horizon_start"],
        planning_horizon_end=schedule_config["planning_horizon_end"],
        spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
        tasks=[],
        windmills=sample_windmills,
        resources=sample_resources,
        weather_forecasts=sample_weather,
        distances={},
        revenue_matrix=sample_revenue_matrix,
        breakdown=sample_breakdown,
    )

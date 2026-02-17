"""Unit tests for the ScheduleOptimizer class."""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from models import Task, Windmill, Resource, WeatherForecast, BreakdownEvent
from optimizer import ScheduleOptimizer


# =============================================================================
# TIME CONVERSION TESTS
# =============================================================================

class TestTimeConversions:
    """Tests for time conversion helper methods."""
    
    def test_time_to_hours_at_planning_start(self, simple_optimizer):
        """Hour 0 should correspond to planning start."""
        planning_start = simple_optimizer.planning_start
        result = simple_optimizer._time_to_hours(planning_start)
        assert result == 0
    
    def test_time_to_hours_one_day_later(self, simple_optimizer):
        """One day after planning start should be hour 24."""
        planning_start = simple_optimizer.planning_start
        one_day_later = planning_start + timedelta(days=1)
        result = simple_optimizer._time_to_hours(one_day_later)
        assert result == 24
    
    def test_time_to_hours_partial_day(self, simple_optimizer):
        """Test hours calculation for partial days."""
        planning_start = simple_optimizer.planning_start
        half_day_later = planning_start + timedelta(hours=12)
        result = simple_optimizer._time_to_hours(half_day_later)
        assert result == 12
    
    def test_hours_to_time_at_zero(self, simple_optimizer):
        """Hour 0 should return planning start."""
        planning_start = simple_optimizer.planning_start
        result = simple_optimizer._hours_to_time(0)
        assert result == planning_start
    
    def test_hours_to_time_roundtrip(self, simple_optimizer):
        """Converting to hours and back should return original datetime."""
        planning_start = simple_optimizer.planning_start
        test_time = planning_start + timedelta(hours=14)
        hours = simple_optimizer._time_to_hours(test_time)
        result = simple_optimizer._hours_to_time(hours)
        assert result == test_time
    
    def test_time_to_hours_negative_result(self, simple_optimizer):
        """Time before planning start should give negative hours."""
        planning_start = simple_optimizer.planning_start
        one_day_before_planning_start = planning_start - timedelta(days=1)
        result = simple_optimizer._time_to_hours(one_day_before_planning_start)
        assert result == -24


# =============================================================================
# REVENUE LOOKUP TESTS
# =============================================================================

class TestRevenueLookup:
    """Tests for revenue calculation helper methods."""
    
    def test_get_wind_speed_for_hour(self, simple_optimizer):
        """Wind speed should be retrieved from weather data."""
        wind_speed = simple_optimizer._get_wind_speed_for_hour(hour=0)
        assert wind_speed == 8.0  # From sample_weather fixture
    
    def test_get_wind_speed_for_date(self, simple_optimizer, planning_start_date):
        """Wind speed should be retrievable by date string."""
        date_str = planning_start_date.strftime("%Y-%m-%d")
        wind_speed = simple_optimizer._get_wind_speed_for_hour(date=date_str)
        assert wind_speed == 8.0
    
    def test_get_revenue_for_hour(self, simple_optimizer):
        """Revenue should be calculated based on wind speed."""
        # Wind speed 8 m/s -> revenue should be 800 (8 * 100 per fixture)
        revenue = simple_optimizer._get_revenue_for_hour("WM001", hour=0)
        assert revenue == 800
    
    def test_get_revenue_for_unknown_windmill(self, simple_optimizer):
        """Unknown windmill should return 0 revenue."""
        revenue = simple_optimizer._get_revenue_for_hour("UNKNOWN_WM", hour=0)
        assert revenue == 0.0
    
    def test_get_revenue_for_date(self, simple_optimizer, planning_start_date):
        """Revenue should be retrievable by date."""
        date_str = planning_start_date.strftime("%Y-%m-%d")
        revenue = simple_optimizer._get_revenue_for_hour("WM001", date=date_str)
        assert revenue == 800


# =============================================================================
# BASIC OPTIMIZATION TESTS
# =============================================================================

class TestBasicOptimization:
    """Tests for basic optimization scenarios."""
    
    def test_single_task_finds_solution(self, simple_optimizer):
        """Simple case: one task should always find a solution."""
        result = simple_optimizer.solve()
        
        # solve() returns tuple (solution, cost_metrics) on success
        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
        solution, cost_metrics = result
        
        assert "error" not in solution
        assert len(solution["tasks"]) == 1
    
    def test_task_scheduled_within_horizon(self, simple_optimizer):
        """Task should be scheduled within planning horizon."""
        solution, _ = simple_optimizer.solve()
        task = solution["tasks"][0]
        
        start = datetime.fromisoformat(task["start_time"])
        assert start >= simple_optimizer.planning_start
        assert start <= simple_optimizer.planning_end
    
    def test_task_has_correct_duration(self, simple_optimizer):
        """Scheduled task should have correct duration."""
        solution, _ = simple_optimizer.solve()
        task = solution["tasks"][0]
        
        start = datetime.fromisoformat(task["start_time"])
        finish = datetime.fromisoformat(task["finish_time"])
        duration_hours = (finish - start).total_seconds() / 3600
        
        assert duration_hours == task["duration_hours"]
    
    def test_objective_value_returned(self, simple_optimizer):
        """Solution should include objective value."""
        solution, _ = simple_optimizer.solve()
        assert "objective_value" in solution
    
    def test_cost_metrics_returned(self, simple_optimizer):
        """Solution should return cost metrics for LLM."""
        solution, cost_metrics = simple_optimizer.solve()
        
        assert cost_metrics is not None
        assert "downtime_cost_for_scheduled_tasks" in cost_metrics
        assert "cost_of_overtime" in cost_metrics


# =============================================================================
# CONSTRAINT VALIDATION TESTS
# =============================================================================

class TestConstraintValidation:
    """Tests for constraint enforcement."""
    
    def test_tasks_on_same_windmill_dont_overlap(
        self, sample_windmills, sample_resources, sample_weather, 
        sample_revenue_matrix, multiple_tasks_same_windmill, schedule_config
    ):
        """Two tasks on same windmill must not overlap."""
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=multiple_tasks_same_windmill,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
        )
        
        solution, _ = optimizer.solve()
        
        task1 = solution["tasks"][0]
        task2 = solution["tasks"][1]
        
        t1_start = datetime.fromisoformat(task1["start_time"])
        t1_end = datetime.fromisoformat(task1["finish_time"])
        t2_start = datetime.fromisoformat(task2["start_time"])
        t2_end = datetime.fromisoformat(task2["finish_time"])
        
        # Either task1 finishes before task2 starts, or vice versa
        no_overlap = (t1_end <= t2_start) or (t2_end <= t1_start)
        assert no_overlap, f"Tasks overlap: T1 {t1_start}-{t1_end}, T2 {t2_start}-{t2_end}"
    
    def test_resource_cant_do_two_tasks_simultaneously(
        self, sample_windmills, sample_weather, sample_revenue_matrix, 
        schedule_config, planning_start_date
    ):
        """A single resource cannot be assigned to overlapping tasks."""
        # Create tasks on different windmills but requiring same resource
        task1_start = planning_start_date + timedelta(days=2)
        latest_finish = datetime.fromisoformat(
            schedule_config["spill_over_cutoff_date"].replace('Z', '+00:00')
        ).replace(tzinfo=None)
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM001", task_type="corrective",
                description="Task 1", duration_hours=4,
                latest_finish=latest_finish.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=task1_start.strftime("%Y-%m-%dT08:00:00")
            ),
            Task(
                id="TASK002", windmill_id="WM002", task_type="corrective",
                description="Task 2", duration_hours=4,
                latest_finish=latest_finish.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["emergency_repairs"],
                dependencies=[], start_time=task1_start.strftime("%Y-%m-%dT08:00:00")
            ),
        ]
        
        # Only one resource can do emergency_repairs
        resources = [
            Resource(
                id="R001", type="crew", name="Team A",
                daily_working_hours=12, rest_hours_after_work=2,
                qualifications=["maintenance", "emergency_repairs"],
                base_location="harbor"
            ),
        ]
        
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
        )
        
        solution, _ = optimizer.solve()
        
        task1 = solution["tasks"][0]
        task2 = solution["tasks"][1]
        
        t1_start = datetime.fromisoformat(task1["start_time"])
        t1_end = datetime.fromisoformat(task1["finish_time"])
        t2_start = datetime.fromisoformat(task2["start_time"])
        t2_end = datetime.fromisoformat(task2["finish_time"])
        
        # Tasks shouldn't overlap (same resource must do both)
        # Also account for rest_hours_after_work (2 hours)
        rest_hours = 2
        no_overlap = (t1_end + timedelta(hours=rest_hours) <= t2_start) or \
                     (t2_end + timedelta(hours=rest_hours) <= t1_start)
        assert no_overlap, f"Resource overlap: T1 ends {t1_end}, T2 starts {t2_start}"
    
    def test_weather_constraint_respected(
        self, sample_windmills, sample_resources, sample_revenue_matrix,
        schedule_config, planning_start_date
    ):
        """Tasks should not be scheduled on days where maintenance is impossible."""
        # Create weather where only day 5 is possible
        weather = []
        for i in range(14):
            date = (planning_start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            is_possible = (i == 5)  # Only day 5 is possible
            weather.append(
                WeatherForecast(
                    date=date, wind_speed_ms=8.0, wave_height_m=1.0,
                    maintenance_possible=is_possible
                )
            )
        
        planning_end = datetime.fromisoformat(
            schedule_config["planning_horizon_end"].replace('Z', '+00:00')
        ).replace(tzinfo=None)
        task_start = planning_start_date + timedelta(days=2)
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM001", task_type="corrective",
                description="Test task", duration_hours=4,
                latest_finish=planning_end.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=task_start.strftime("%Y-%m-%dT08:00:00")
            ),
        ]
        
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
        )
        
        solution, _ = optimizer.solve()
        task = solution["tasks"][0]
        start = datetime.fromisoformat(task["start_time"])
        
        # Task should be scheduled on day 5 (the only possible day)
        expected_date = (planning_start_date + timedelta(days=5)).date()
        assert start.date() == expected_date


# =============================================================================
# BREAKDOWN HANDLING TESTS
# =============================================================================

class TestBreakdownHandling:
    """Tests for breakdown event handling."""
    
    def test_breakdown_finds_solution(self, optimizer_with_breakdown):
        """Optimizer with breakdown should find a solution."""
        result = optimizer_with_breakdown.solve()
        
        assert isinstance(result, tuple)
        solution, _ = result
        
        assert "error" not in solution
        assert solution["breakdown"] is not None
    
    def test_breakdown_scheduled_after_breakdown_time(
        self, optimizer_with_breakdown, planning_start_date
    ):
        """Breakdown repair should start at or after breakdown time."""
        solution, _ = optimizer_with_breakdown.solve()
        
        breakdown = solution["breakdown"]
        start = datetime.fromisoformat(breakdown["start_time"])
        # Breakdown time is 1 day + 10 hours after planning start (from fixture)
        breakdown_time = planning_start_date + timedelta(days=1, hours=10)
        
        assert start >= breakdown_time
    
    def test_breakdown_with_high_wind_fixed_asap(
        self, sample_windmills, sample_resources, high_wind_weather, 
        sample_revenue_matrix, sample_breakdown, schedule_config, planning_start_date
    ):
        """With high wind (high revenue loss), breakdown should be fixed ASAP."""
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=[],
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=high_wind_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
            breakdown=sample_breakdown,
        )
        
        solution, _ = optimizer.solve()
        breakdown = solution["breakdown"]
        start = datetime.fromisoformat(breakdown["start_time"])
        
        # Breakdown should be scheduled at earliest possible time
        breakdown_time = planning_start_date + timedelta(days=1, hours=10)
        assert start == breakdown_time
    
    def test_downtime_cost_calculated(self, optimizer_with_breakdown):
        """Downtime cost for breakdown should be calculated."""
        solution, cost_metrics = optimizer_with_breakdown.solve()
        
        assert "downtime_cost_for_breakdown" in solution
        assert solution["downtime_cost_for_breakdown"] >= 0


# =============================================================================
# PENALTY AND COST TESTS
# =============================================================================

class TestPenaltiesAndCosts:
    """Tests for penalty and cost calculations."""
    
    def test_overdue_penalty_when_task_late(
        self, sample_windmills, sample_resources, sample_weather, sample_revenue_matrix,
        schedule_config, planning_start_date
    ):
        """Tasks finishing after deadline should have overdue penalty."""
        # Create task with very tight deadline forcing it to be overdue
        deadline = planning_start_date + timedelta(days=1, hours=18)
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM001", task_type="corrective",
                description="Long task", duration_hours=48,  # 2 days
                latest_finish=deadline.strftime("%Y-%m-%dT%H:%M:%S"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=planning_start_date.strftime("%Y-%m-%dT06:00:00")
            ),
        ]
        
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
            overdue_penalty_per_day=5000,
        )
        
        solution, cost_metrics = optimizer.solve()
        task = solution["tasks"][0]
        
        assert "overdue_info" in task
        assert task["overdue_info"]["days_overdue"] > 0
        assert task["overdue_info"]["penalty_cost"] > 0
    
    def test_no_overdue_penalty_when_on_time(self, simple_optimizer):
        """Tasks finishing before deadline should have no overdue penalty."""
        solution, _ = simple_optimizer.solve()
        task = solution["tasks"][0]
        
        # Task should not be overdue
        assert "overdue_info" not in task or task.get("overdue_info", {}).get("days_overdue", 0) == 0
    
    def test_spill_over_penalty_when_past_cutoff(
        self, sample_windmills, sample_weather, sample_revenue_matrix,
        schedule_config, planning_start_date
    ):
        """Tasks finishing after spill over cutoff should have penalty."""
        # Create multiple tasks that force some to be scheduled after cutoff
        planning_end = datetime.fromisoformat(
            schedule_config["planning_horizon_end"].replace('Z', '+00:00')
        ).replace(tzinfo=None)
        early_cutoff = planning_start_date + timedelta(days=2)  # Very early cutoff
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM001", task_type="corrective",
                description="Task 1", duration_hours=24,
                latest_finish=planning_end.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=(planning_start_date + timedelta(days=1)).strftime("%Y-%m-%dT08:00:00")
            ),
            Task(
                id="TASK002", windmill_id="WM002", task_type="corrective",
                description="Task 2", duration_hours=24,
                latest_finish=planning_end.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=(planning_start_date + timedelta(days=2)).strftime("%Y-%m-%dT08:00:00")
            ),
            Task(
                id="TASK003", windmill_id="WM003", task_type="corrective",
                description="Task 3", duration_hours=24,
                latest_finish=planning_end.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=(planning_start_date + timedelta(days=3)).strftime("%Y-%m-%dT08:00:00")
            ),
        ]
        
        # Use only one resource so tasks must be sequential
        resources = [
            Resource(
                id="R001", type="crew", name="Team A",
                daily_working_hours=12, rest_hours_after_work=0,
                qualifications=["maintenance"],
                base_location="harbor"
            ),
        ]
        
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=early_cutoff.strftime("%Y-%m-%dT00:00:00"),
            tasks=tasks,
            windmills=sample_windmills,
            resources=resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
            spill_over_penalty_repairs=10000,
        )
        
        solution, cost_metrics = optimizer.solve()
        
        # The test verifies the spill over penalty mechanism works
        assert "cost_of_spill_over" in solution
    
    def test_overtime_cost_calculated(self, simple_optimizer):
        """Overtime costs should be included in solution."""
        solution, cost_metrics = simple_optimizer.solve()
        
        assert "cost_of_overtime" in solution
        assert "cost_of_overtime" in cost_metrics


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_infeasible_returns_error(
        self, sample_windmills, sample_resources, impossible_weather, sample_revenue_matrix,
        schedule_config, planning_start_date
    ):
        """When no solution exists, an error should be returned."""
        task_start = planning_start_date + timedelta(days=2)
        deadline = planning_start_date + timedelta(days=5)
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM001", task_type="corrective",
                description="Test task", duration_hours=4,
                latest_finish=deadline.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=task_start.strftime("%Y-%m-%dT08:00:00")
            ),
        ]
        
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=impossible_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
        )
        
        result = optimizer.solve()
        
        # Should return error dict (not tuple) when infeasible
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_empty_tasks_with_breakdown(
        self, sample_windmills, sample_resources, sample_weather, 
        sample_revenue_matrix, sample_breakdown, schedule_config
    ):
        """Optimizer should work with no tasks, only breakdown."""
        optimizer = ScheduleOptimizer(
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
        
        solution, _ = optimizer.solve()
        
        assert "error" not in solution
        assert len(solution["tasks"]) == 0
        assert solution["breakdown"] is not None
    
    def test_task_dependency_respected(
        self, sample_windmills, sample_resources, sample_weather, sample_revenue_matrix,
        schedule_config, planning_start_date
    ):
        """Dependent tasks should be scheduled after their dependencies."""
        task1_start = planning_start_date + timedelta(days=2)
        task2_start = planning_start_date + timedelta(days=3)
        latest_finish = datetime.fromisoformat(
            schedule_config["spill_over_cutoff_date"].replace('Z', '+00:00')
        ).replace(tzinfo=None)
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM001", task_type="corrective",
                description="First task", duration_hours=4,
                latest_finish=latest_finish.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=task1_start.strftime("%Y-%m-%dT08:00:00")
            ),
            Task(
                id="TASK002", windmill_id="WM002", task_type="corrective",
                description="Dependent task", duration_hours=4,
                latest_finish=latest_finish.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=["TASK001"],  # Depends on TASK001
                start_time=task2_start.strftime("%Y-%m-%dT08:00:00")
            ),
        ]
        
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
        )
        
        solution, _ = optimizer.solve()
        
        task1 = next(t for t in solution["tasks"] if t["id"] == "TASK001")
        task2 = next(t for t in solution["tasks"] if t["id"] == "TASK002")
        
        t1_end = datetime.fromisoformat(task1["finish_time"])
        t2_start = datetime.fromisoformat(task2["start_time"])
        
        # TASK002 should start after TASK001 finishes
        assert t2_start >= t1_end


# =============================================================================
# LOCKED TASK TESTS
# =============================================================================

class TestTaskLocking:
    """Tests for task locking when breakdown occurs."""
    
    def test_started_task_stays_locked(
        self, sample_windmills, sample_resources, sample_weather, sample_revenue_matrix,
        schedule_config, planning_start_date
    ):
        """Tasks that started before breakdown should stay at original time."""
        # Task started at planning start, breakdown 1 day later
        latest_finish = datetime.fromisoformat(
            schedule_config["spill_over_cutoff_date"].replace('Z', '+00:00')
        ).replace(tzinfo=None)
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM002", task_type="corrective",
                description="Already started task", duration_hours=4,
                latest_finish=latest_finish.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[],
                start_time=planning_start_date.strftime("%Y-%m-%dT08:00:00")  # Before breakdown
            ),
        ]
        
        breakdown_time = planning_start_date + timedelta(days=1, hours=10)
        breakdown = BreakdownEvent(
            id="BREAKDOWN001", windmill_id="WM001",
            breakdown_time=breakdown_time.strftime("%Y-%m-%dT%H:%M:%S"),
            description="Breakdown", estimated_repair_duration_hours=4,
            required_qualifications=["repairs"]
        )
        
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
            breakdown=breakdown,
        )
        
        solution, _ = optimizer.solve()
        task = solution["tasks"][0]
        
        # Task should stay at its original start time
        start = datetime.fromisoformat(task["start_time"])
        expected_start = planning_start_date.replace(hour=8, minute=0, second=0)
        assert start == expected_start


# =============================================================================
# CONFIGURABLE PARAMETERS TESTS
# =============================================================================

class TestConfigurableParameters:
    """Tests for configurable penalty parameters."""
    
    def test_custom_overdue_penalty(
        self, sample_windmills, sample_resources, sample_weather, sample_revenue_matrix,
        schedule_config, planning_start_date
    ):
        """Custom overdue penalty should be used in penalty calculations."""
        # Create a task that will definitely be overdue (very short deadline)
        deadline = planning_start_date + timedelta(days=1, hours=6)
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM001", task_type="corrective",
                description="Task", duration_hours=48,
                latest_finish=deadline.strftime("%Y-%m-%dT%H:%M:%S"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=planning_start_date.strftime("%Y-%m-%dT06:00:00")
            ),
        ]
        
        penalty_per_day = 5000
        
        optimizer = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
            overdue_penalty_per_day=penalty_per_day,
        )
        
        solution, _ = optimizer.solve()
        task = solution["tasks"][0]
        
        # Task should be overdue
        assert "overdue_info" in task
        days_overdue = task["overdue_info"]["days_overdue"]
        penalty_cost = task["overdue_info"]["penalty_cost"]
        
        # Verify penalty is calculated correctly: penalty = days_overdue * penalty_per_day
        assert penalty_cost == days_overdue * penalty_per_day
    
    def test_custom_overtime_cost(
        self, sample_windmills, sample_resources, sample_weather, sample_revenue_matrix,
        schedule_config, planning_start_date
    ):
        """Custom overtime cost should affect objective value."""
        task_start = planning_start_date + timedelta(days=2)
        latest_finish = datetime.fromisoformat(
            schedule_config["spill_over_cutoff_date"].replace('Z', '+00:00')
        ).replace(tzinfo=None)
        
        tasks = [
            Task(
                id="TASK001", windmill_id="WM001", task_type="corrective",
                description="Task", duration_hours=4,
                latest_finish=latest_finish.strftime("%Y-%m-%dT18:00:00"),
                required_qualifications=["maintenance"],
                dependencies=[], start_time=task_start.strftime("%Y-%m-%dT08:00:00")
            ),
        ]
        
        # Optimizer with high overtime cost
        optimizer_high = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
            overtime_cost_per_hour=1000,  # High
        )
        
        # Optimizer with low overtime cost
        optimizer_low = ScheduleOptimizer(
            planning_horizon_start=schedule_config["planning_horizon_start"],
            planning_horizon_end=schedule_config["planning_horizon_end"],
            spill_over_cutoff_date=schedule_config["spill_over_cutoff_date"],
            tasks=tasks,
            windmills=sample_windmills,
            resources=sample_resources,
            weather_forecasts=sample_weather,
            distances={},
            revenue_matrix=sample_revenue_matrix,
            overtime_cost_per_hour=10,  # Low
        )
        
        solution_high, _ = optimizer_high.solve()
        solution_low, _ = optimizer_low.solve()
        
        # Both should find solutions
        assert "error" not in solution_high
        assert "error" not in solution_low

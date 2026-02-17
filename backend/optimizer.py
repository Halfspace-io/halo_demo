"""OR-Tools optimization model for schedule re-planning."""
from ortools.sat.python import cp_model
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from models import (
    Task, BreakdownEvent, Windmill, Resource, WeatherForecast
)
from calculations import RevenueCalculator


class ScheduleOptimizer:
    """Optimizes maintenance schedule using OR-Tools CP-SAT."""
    
    def __init__(
        self,
        planning_horizon_start: str,
        planning_horizon_end: str,
        spill_over_cutoff_date: str,
        tasks: List[Task],
        windmills: List[Windmill],
        resources: List[Resource],
        weather_forecasts: List[WeatherForecast],
        distances: Dict[str, Dict[str, float]],
        revenue_matrix: Dict[str, Dict[str, float]],
        overdue_penalty_per_day: Optional[float] = None,
        overtime_cost_per_hour: float = 500,
        spill_over_penalty_routine: float = 5000,
        spill_over_penalty_repairs: float = 10000,
        breakdown: Optional[BreakdownEvent] = None
    ):
        self.tasks = tasks
        self.breakdown = breakdown
        self.windmills = {wm.id: wm for wm in windmills}
        self.resources = resources
        self.weather_forecasts = weather_forecasts
        self.distances = distances
        self.revenue_matrix = revenue_matrix
        self.overdue_penalty_per_day = overdue_penalty_per_day
        self.overtime_cost_per_hour = overtime_cost_per_hour
        self.spill_over_penalty_routine = spill_over_penalty_routine
        self.spill_over_penalty_repairs = spill_over_penalty_repairs
        
        # Create weather lookup by date
        self.weather_by_date = {fc.date: fc for fc in weather_forecasts}
        
        # Find planning horizon
        self.planning_start = datetime.strptime(planning_horizon_start[:len("YYYY-MM-DD")], '%Y-%m-%d').replace(tzinfo=None)
        self.planning_end = datetime.strptime(planning_horizon_end[:len("YYYY-MM-DD")], '%Y-%m-%d').replace(tzinfo=None)
        self.spill_over_cutoff_date = datetime.strptime(spill_over_cutoff_date[:len("YYYY-MM-DD")], '%Y-%m-%d').replace(tzinfo=None)
        
        # Convert to hours from planning start
        self.horizon_hours = int((self.planning_end - self.planning_start).total_seconds() / 3600)
        
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Variables
        self.task_start_vars = {}
        self.task_assigned_vars = {}
        self.resource_task_vars = {}
        self.overdue_days_vars = {}
        self.breakdown_start_var = None
    
    def _time_to_hours(self, dt: datetime) -> int:
        """Convert datetime to hours from planning start."""
        delta = dt.replace(tzinfo=None) - self.planning_start
        return int(delta.total_seconds() / 3600)
    
    def _hours_to_time(self, hours: int) -> datetime:
        """Convert hours from planning start to datetime."""
        return self.planning_start + timedelta(hours=hours)
    
    def _get_wind_speed_for_hour(self, hour: int = None, date: str = None) -> float:
        """Get wind speed for a given hour from planning start."""
        if hour is None and date:
            return self.weather_by_date[date].wind_speed_ms
        elif hour is not None and date is None:
            dt = self._hours_to_time(hour)
            date_str = dt.strftime("%Y-%m-%d")
            if date_str in self.weather_by_date:
                return self.weather_by_date[date_str].wind_speed_ms
            return sum(fc.wind_speed_ms for fc in self.weather_forecasts) / len(self.weather_forecasts)
        else:
            raise ValueError("Either hour or date must be provided")

    def _get_revenue_for_hour(self, windmill_id: str, hour: int = None, date: str = None) -> float:
        """Get revenue per hour for a windmill at a given hour based on wind speed."""
        wind_speed = self._get_wind_speed_for_hour(hour, date)
        wind_speed_key = int(wind_speed)  # Round to integer for lookup
        if windmill_id in self.revenue_matrix:
            windmill_revenues = self.revenue_matrix[windmill_id]
            if wind_speed_key in windmill_revenues:
                return windmill_revenues[wind_speed_key]
        return 0.0
    
    def build_model(self):
        """Build the optimization model."""
        # Get breakdown time if available (for locking already-started tasks)
        breakdown_time = None
        if self.breakdown:
            breakdown_time = datetime.fromisoformat(
                self.breakdown.breakdown_time.replace('Z', '+00:00')
            ).replace(tzinfo=None)
        
        # Create variables for tasks
        for task in self.tasks:
            latest_finish_hours = self._time_to_hours(
                datetime.fromisoformat(task.latest_finish.replace('Z', '+00:00'))
            )
            # Lock tasks that have already started before the breakdown 
            # and set min value=time of breakdown for later tasks
            planning_end_hours = self._time_to_hours(self.planning_end)
            if breakdown_time and task.start_time:
                breakdown_time_hours = self._time_to_hours(breakdown_time)
                task_start_time = datetime.fromisoformat(
                    task.start_time.replace('Z', '+00:00')
                ).replace(tzinfo=None)
                if task_start_time < breakdown_time:
                    # Task start time variable - can start from planning start (hour 0)
                    self.task_start_vars[task.id] = self.model.NewIntVar(
                        0,
                        latest_finish_hours + 168,  # Allow 7 days overdue
                        f"start_{task.id}"
                    )
                    # This task has already started - lock it to its original start time
                    original_start_hours = self._time_to_hours(task_start_time)
                    self.model.Add(self.task_start_vars[task.id] == original_start_hours)
                else:
                    self.task_start_vars[task.id] = self.model.NewIntVar(
                        breakdown_time_hours, # Today's date
                        planning_end_hours,
                        f"start_{task.id}"
                    )
            else:
                self.task_start_vars[task.id] = self.model.NewIntVar(
                    0,
                    planning_end_hours,
                    f"start_{task.id}"
                )
            
            # Task assignment variable (1 if task is scheduled)
            self.task_assigned_vars[task.id] = self.model.NewBoolVar(
                f"assigned_{task.id}"
            )
            
            # Overdue days variable
            task_finish_hours = self.task_start_vars[task.id] + task.duration_hours
            overdue_hours = task_finish_hours - latest_finish_hours
            self.overdue_days_vars[task.id] = self.model.NewIntVar(
                0, 168, f"overdue_days_{task.id}"
            )
            
            # Create a boolean for whether task is overdue
            is_overdue = self.model.NewBoolVar(f"is_overdue_{task.id}")
            self.model.Add(overdue_hours > 0).OnlyEnforceIf(is_overdue)
            self.model.Add(overdue_hours <= 0).OnlyEnforceIf(is_overdue.Not())
            
            # If overdue, constrain overdue_days to ceiling of overdue_hours/24
            self.model.Add(
                self.overdue_days_vars[task.id] * 24 >= overdue_hours
            ).OnlyEnforceIf(is_overdue)
            self.model.Add(
                self.overdue_days_vars[task.id] * 24 <= overdue_hours + 23
            ).OnlyEnforceIf(is_overdue)
            
            # If not overdue, overdue_days should be 0
            self.model.Add(self.overdue_days_vars[task.id] == 0).OnlyEnforceIf(is_overdue.Not())
            
            # Resource assignment variables
            self.resource_task_vars[task.id] = {}
            for resource in self.resources:
                # Check if resource has required qualifications
                if all(q in resource.qualifications for q in task.required_qualifications):
                    self.resource_task_vars[task.id][resource.id] = self.model.NewBoolVar(
                        f"resource_{resource.id}_task_{task.id}"
                    )
        
        # Create variables for breakdown
        if self.breakdown:
            breakdown_time_hours = self._time_to_hours(
                datetime.fromisoformat(
                    self.breakdown.breakdown_time.replace('Z', '+00:00')
                )
            )
            self.breakdown_start_var = self.model.NewIntVar(
                breakdown_time_hours,
                self._time_to_hours(self.spill_over_cutoff_date),
                "breakdown_start"
            )
            
            # Resource assignment for breakdown
            self.resource_task_vars[self.breakdown.id] = {}
            for resource in self.resources:
                if all(q in resource.qualifications 
                       for q in self.breakdown.required_qualifications):
                    self.resource_task_vars[self.breakdown.id][resource.id] = \
                        self.model.NewBoolVar(
                            f"resource_{resource.id}_breakdown"
                        )
        
        # Add constraints
        self._add_task_constraints()
        self._add_resource_constraints()
        self._add_weather_constraints()
        self._add_dependency_constraints()
        
        # Set objective
        self._set_objective()
    
    def _add_task_constraints(self):
        """Add constraints for tasks."""
        for task in self.tasks:
            # Task must be assigned
            self.model.Add(self.task_assigned_vars[task.id] == 1)
            
            # Task duration constraint
            task_finish = self.task_start_vars[task.id] + task.duration_hours
            # No upper bound on finish time (can go overdue)
                            
        # Prevent overlapping tasks on the same windmill
        for i, task1 in enumerate(self.tasks):
            for j in range(i + 1, len(self.tasks)):
                task2 = self.tasks[j]
                if task1.windmill_id != task2.windmill_id:
                    continue
                else:
                    start1 = self.task_start_vars[task1.id]
                    finish1 = start1 + task1.duration_hours
                    start2 = self.task_start_vars[task2.id]
                    finish2 = start2 + task2.duration_hours

                    # Introduce boolean for ordering
                    task1_before_task2 = self.model.NewBoolVar(f"windmill_{task1.id}_before_{task2.id}")
                    task2_before_task1 = self.model.NewBoolVar(f"windmill_{task2.id}_before_{task1.id}")

                    # If task1 before task2: finish1 <= start2
                    self.model.Add(finish1 <= start2).OnlyEnforceIf(task1_before_task2)
                    # If task2 before task1: finish2 <= start1
                    self.model.Add(finish2 <= start1).OnlyEnforceIf(task2_before_task1)
                    # Exactly one ordering must be true
                    self.model.AddBoolOr([task1_before_task2, task2_before_task1])
                    self.model.Add(task1_before_task2 + task2_before_task1 == 1)
        # Also prevent overlapping tasks on the same windmill with the breakdown
        if self.breakdown:
            for task in [t for t in self.tasks if t.windmill_id == self.breakdown.windmill_id]:    
                start1 = self.task_start_vars[task.id]   
                finish1 = start1 + task.duration_hours
                start2 = self.breakdown_start_var
                finish2 = start2 + self.breakdown.estimated_repair_duration_hours
                task1_before_breakdown = self.model.NewBoolVar(f"windmill_{task.id}_before_breakdown")
                breakdown_before_task1 = self.model.NewBoolVar(f"breakdown_before_{task.id}")
                self.model.Add(finish1 <= start2).OnlyEnforceIf(task1_before_breakdown)
                self.model.Add(finish2 <= start1).OnlyEnforceIf(breakdown_before_task1)
                self.model.AddBoolOr([task1_before_breakdown, breakdown_before_task1])
                self.model.Add(task1_before_breakdown + breakdown_before_task1 == 1)

    def _add_resource_constraints(self):
        """Add constraints for resources."""
        # Each task must be assigned to exactly one resource
        for task in self.tasks:
            resource_vars = list(self.resource_task_vars[task.id].values())
            if resource_vars:
                self.model.Add(sum(resource_vars) == 1)
        
        # Breakdown must be assigned to exactly one resource
        if self.breakdown and self.breakdown.id in self.resource_task_vars:
            breakdown_resource_vars = list(self.resource_task_vars[self.breakdown.id].values())
            if breakdown_resource_vars:
                self.model.Add(sum(breakdown_resource_vars) == 1)
        
        # Each resource can only do one task at a time
        for resource in self.resources:
            # Collect all tasks this resource can do with their variables
            resource_task_pairs = []
            
            for task in self.tasks:
                if resource.id in self.resource_task_vars[task.id]:
                    resource_task_pairs.append((
                        task,
                        self.task_start_vars[task.id],
                        task.duration_hours,
                        self.resource_task_vars[task.id][resource.id]
                    ))
            
            if self.breakdown and resource.id in self.resource_task_vars.get(self.breakdown.id, {}):
                resource_task_pairs.append((
                    self.breakdown,
                    self.breakdown_start_var,
                    self.breakdown.estimated_repair_duration_hours,
                    self.resource_task_vars[self.breakdown.id][resource.id]
                ))
            
            # Add non-overlapping constraints for all pairs
            for i, (task1, start1, duration1, assigned1) in enumerate(resource_task_pairs):
                for task2, start2, duration2, assigned2 in resource_task_pairs[i+1:]:
                    finish1 = start1 + duration1
                    finish2 = start2 + duration2
                    
                    # If both tasks use same resource, they cannot overlap
                    # Use intermediate boolean variable for ordering
                    task1_before_task2 = self.model.NewBoolVar(
                        f"{task1.id}_before_{task2.id}_on_{resource.id}"
                    )
                    
                    # If both assigned, enforce non-overlap with rest hours between tasks
                    # task1 finishes + rest hours before task2 starts
                    self.model.Add(finish1 + resource.rest_hours_after_work <= start2).OnlyEnforceIf(
                        [assigned1, assigned2, task1_before_task2]
                    )
                    # task2 finishes + rest hours before task1 starts
                    self.model.Add(finish2 + resource.rest_hours_after_work <= start1).OnlyEnforceIf(
                        [assigned1, assigned2, task1_before_task2.Not()]
                    )
    
    def _add_weather_constraints(self):
        """Add constraints for weather."""
        days_where_maintenance_is_not_possible = [
            datetime.strptime(e.date, "%Y-%m-%d") for e in self.weather_forecasts 
            if e.maintenance_possible == False
        ]
        # convert days to hours since planning start
        days_where_maintenance_is_not_possible_hours = [
            self._time_to_hours(dt) for dt in days_where_maintenance_is_not_possible
        ]
        def add_forbidden_intervals(
            decision_variable: cp_model.IntVar,
            task_duration_hours: Optional[int] = 0
            ):
            for h in days_where_maintenance_is_not_possible_hours:
                forbidden_interval = [h, h + 24]
                lower = self.model.NewBoolVar("x_before_interval")
                upper = self.model.NewBoolVar("x_after_interval")

                
                self.model.Add(decision_variable < forbidden_interval[0] - task_duration_hours).OnlyEnforceIf(lower)
                self.model.Add(decision_variable >= forbidden_interval[0]).OnlyEnforceIf(lower.Not())

                # If upper is true → x >= b
                self.model.Add(decision_variable >= forbidden_interval[1]).OnlyEnforceIf(upper)
                self.model.Add(decision_variable < forbidden_interval[0]).OnlyEnforceIf(upper.Not())

                # Enforce that one of them must hold
                self.model.AddBoolOr([lower, upper])

        for id, task in self.task_start_vars.items():
            task_duration_hours = sum([t.duration_hours for t in self.tasks if t.id == id])
            add_forbidden_intervals(
                decision_variable=task,
                task_duration_hours=task_duration_hours
            )

        if self.breakdown:
            add_forbidden_intervals(
                decision_variable=self.breakdown_start_var,
                task_duration_hours=self.breakdown.estimated_repair_duration_hours
            )
    
    def _add_dependency_constraints(self):
        """Add constraints for task dependencies."""
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id in self.task_start_vars:
                    dep_task = next(t for t in self.tasks if t.id == dep_id)
                    dep_finish = self.task_start_vars[dep_id] + dep_task.duration_hours
                    self.model.Add(
                        dep_finish <= self.task_start_vars[task.id]
                    )

    def _lost_revenue_from_downtime_for_breakdown(self):
        """Calculate lost revenue from downtime for breakdown."""
        windmill_id = self.breakdown.windmill_id
        repair_duration = self.breakdown.estimated_repair_duration_hours
        
        breakdown_time = datetime.fromisoformat(
            self.breakdown.breakdown_time.replace('Z', '+00:00')
        )
        breakdown_time_hours = self._time_to_hours(breakdown_time.replace(tzinfo=None))
        
        max_start_hour = self._time_to_hours(self.spill_over_cutoff_date) - repair_duration
        
        # Pre-compute lost revenue for each possible breakdown start hour
        # For start hour S: lost revenue = sum of revenue from breakdown_time to (S + repair_duration)
        lost_revenue_by_start = []
        dates_used_set = set()
        
        for start_hour in range(breakdown_time_hours, max_start_hour + 1):
            # Calculate lost revenue: sum revenue for each hour from breakdown to repair finish
            repair_finish_hour = start_hour + repair_duration
            total_lost = 0.0
            for hour in range(breakdown_time_hours, repair_finish_hour):
                revenue = self._get_revenue_for_hour(windmill_id, hour)
                total_lost += revenue
                # Track dates used
                dt = self._hours_to_time(hour)
                dates_used_set.add(dt.strftime("%Y-%m-%d"))
            lost_revenue_by_start.append(int(total_lost * 1000))  # Scale by 1000
        
        # Store dates used for revenue calculation (for display)
        self.revenue_calculation_dates = sorted(list(dates_used_set))
        
        max_lost_revenue = max(lost_revenue_by_start) if lost_revenue_by_start else 0
        lost_revenue = self.model.NewIntVar(0, max_lost_revenue, "lost_revenue")
        
        # AddElement: lost_revenue = lost_revenue_by_start[breakdown_start_var]
        # Create an offset variable for array indexing
        breakdown_start_offset = self.model.NewIntVar(
            0, max_start_hour - breakdown_time_hours, "breakdown_start_offset"
        )
        self.model.Add(breakdown_start_offset == self.breakdown_start_var - breakdown_time_hours)

        # Use the offset for AddElement
        self.model.AddElement(breakdown_start_offset, lost_revenue_by_start, lost_revenue)
        return lost_revenue
        
    def _lost_revenue_from_downtime_for_scheduled_tasks(self):
        """Calculate lost revenue from downtime for scheduled tasks.
        
        For each task, the windmill is down during the task execution.
        Lost revenue = sum of revenue for each hour the task is running.
        """
        cost_of_downtime_all_tasks = {}
        
        for task in self.tasks:
            windmill_id = task.windmill_id
            duration = task.duration_hours
            task_start_var = self.task_start_vars[task.id]
            
            if self.breakdown: # If breakdown we are inside the planning horizon, so we need to find a new starting day
                min_start = (
                    datetime.strptime(self.breakdown.breakdown_time,'%Y-%m-%dT%H:%M:%S')
                    - self.planning_start
                ).days
            else:
                min_start = 0  # Tasks can start from planning start
            max_start = (self.planning_end - self.planning_start).days
            spill_over_cutoff_day = (self.spill_over_cutoff_date - self.planning_start).days
            # Pre-compute lost revenue for each possible start hour
            lost_revenue_per_day = []
            for start_day in range(min_start, max_start + 1):
                start_date_str = (self.planning_start + timedelta(days=start_day)).strftime("%Y-%m-%d")
                # Calculate lost revenue: sum revenue for each hour the task is running
                if start_date_str in self.weather_by_date.keys():
                    revenue_per_hour_on_a_given_day = self._get_revenue_for_hour(
                        windmill_id=windmill_id, date=start_date_str
                    )
                else: # If date not found, use average revenue per hour
                    revenue_per_hour_on_a_given_day = sum(self.revenue_matrix[windmill_id].values())/ len(self.revenue_matrix[windmill_id])
                total_lost = revenue_per_hour_on_a_given_day * duration
                if start_day < spill_over_cutoff_day:
                    lost_revenue_per_day.append(int(total_lost * 1000))  # Scale by 1000
                else:
                    lost_revenue_per_day.append(0)

             # Create day variable from hours: task_start_day = task_start_hours // 24
            task_start_day = self.model.NewIntVar(0, len(lost_revenue_per_day) - 1, f"start_day_{task.id}")
            self.model.AddDivisionEquality(task_start_day, task_start_var, 24)
            # Use AddElement to look up the lost revenue based on start hour
            cost_of_downtime_during_service = self.model.NewIntVar(0, max(lost_revenue_per_day), f"day_revenue_{task.id}")
            self.model.AddElement(task_start_day, lost_revenue_per_day, cost_of_downtime_during_service)
            
            cost_of_downtime_all_tasks[task.id] = cost_of_downtime_during_service
        
        return cost_of_downtime_all_tasks
    
    def _calculate_spill_over_task_penalties(self):
        """Calculate spill over task penalties.

        For each task planned outside the planning horizon, a spill over penalty is applied.
        Returns:
            Dict with task_id -> {penalty}
        """
        # Cost of spill over: penalty for tasks planned after self.spill_over_cutoff_date
        SPILL_OVER_PENALTY_ROUTINE = int(self.spill_over_penalty_routine * 1000)  # Scale to match other units
        SPILL_OVER_PENALTY_REPAIRS = int(self.spill_over_penalty_repairs * 1000)

        spill_over_task_penalties = {}

        # Calculate spill over cutoff hour from planning start
        spill_over_cutoff_hour = self._time_to_hours(self.spill_over_cutoff_date)

        for task in self.tasks:
            task_start = self.task_start_vars[task.id]
            task_finish = task_start + task.duration_hours

            # Boolean variable: 1 if spill over (finish after cutoff), 0 otherwise
            is_spill_over = self.model.NewBoolVar(f"is_spill_over_{task.id}")
            self.model.Add(task_finish > spill_over_cutoff_hour).OnlyEnforceIf(is_spill_over)
            self.model.Add(task_finish <= spill_over_cutoff_hour).OnlyEnforceIf(is_spill_over.Not())

            # Choose penalty amount according to task_type
            if getattr(task, "task_type", None) == "preventive":
                penalty_amount = SPILL_OVER_PENALTY_ROUTINE
            elif getattr(task, "task_type", None) == "corrective":
                penalty_amount = SPILL_OVER_PENALTY_REPAIRS
            else:
                penalty_amount = 0  # If task_type is unknown, no penalty

            task_spill_penalty = is_spill_over * penalty_amount
            spill_over_task_penalties[task.id] = task_spill_penalty
        
        return spill_over_task_penalties
    
    def _calculate_overtime_costs(self):
        """
        Calculate overtime costs for all tasks.
        Add overtime cost for any task hours between 18:00 and 06:00 - cost per hour is configurable in the UI.
        Returns:
            Dict with task_id -> {overtime_cost}
        """
        planning_epoch = self.planning_start.replace(tzinfo=None)
        OVERTIME_COST_PER_HOUR = self.overtime_cost_per_hour
        all_tasks_overtime_costs = {}

        list_of_tasks = self.tasks + [self.breakdown] if self.breakdown else self.tasks
        for task in list_of_tasks:
            # Decision variable for task start in hours from planning_epoch
            if type(task) == BreakdownEvent:
                task_start_hour_var = self.breakdown_start_var
                duration = task.estimated_repair_duration_hours
            else:
                task_start_hour_var = self.task_start_vars[task.id]
                duration = task.duration_hours

            overtime_hour_vars = []
            for offset in range(duration):
                hour_var = self.model.NewIntVar(0, 23, f"hour_of_day_{task.id}_{offset}")
                abs_hour_var = self.model.NewIntVar(0, self.horizon_hours, f"abs_hour_{task.id}_{offset}")
                self.model.Add(abs_hour_var == task_start_hour_var + offset)
                # Map abs_hour_var to hour_of_day
                # hour_of_day = (abs_hour_var + planning_epoch.hour) % 24
                self.model.AddModuloEquality(hour_var, abs_hour_var + planning_epoch.hour, 24)

                # Overtime if hour_of_day > 18 or hour_of_day < 6
                is_overtime = self.model.NewBoolVar(f"is_overtime_{task.id}_{offset}")
                
                gt_18 = self.model.NewBoolVar(f"gt_18_{task.id}_{offset}")
                self.model.Add(hour_var >= 18).OnlyEnforceIf(gt_18)
                self.model.Add(hour_var < 18).OnlyEnforceIf(gt_18.Not())
                
                lt_6 = self.model.NewBoolVar(f"lt_6_{task.id}_{offset}")
                self.model.Add(hour_var < 6).OnlyEnforceIf(lt_6)
                self.model.Add(hour_var >= 6).OnlyEnforceIf(lt_6.Not())

                # OR together (either gt_18 or lt_6 gives overtime)
                self.model.AddBoolOr([gt_18, lt_6]).OnlyEnforceIf(is_overtime)
                self.model.AddBoolAnd([gt_18.Not(), lt_6.Not()]).OnlyEnforceIf(is_overtime.Not())

                overtime_hour_vars.append(is_overtime)

            # Sum all overtime hours for this task
            total_overtime_hours = self.model.NewIntVar(0, duration, f"total_overtime_hours_{task.id}")
            self.model.Add(total_overtime_hours == sum(overtime_hour_vars))

            # Cost for this task
            task_overtime_costs = self.model.NewIntVar(0, duration * OVERTIME_COST_PER_HOUR * 1000, f"task_overtime_cost_{task.id}")
            self.model.Add(task_overtime_costs == total_overtime_hours * OVERTIME_COST_PER_HOUR * 1000)
            all_tasks_overtime_costs[task.id] = task_overtime_costs
        
        return all_tasks_overtime_costs
    
    def _calculate_overdue_penalties(self):
        """Calculate overdue penalties for all tasks."""
        overdue_penalties = {}
        for task in self.tasks:
            # Calculate penalty per day
            if task.task_type == "preventive":
                continue
            elif self.overdue_penalty_per_day:
                penalty_per_day = self.overdue_penalty_per_day
            else:
                penalty_per_day = 3000.0  # Hardcoded default penalty
            
            # Penalty = penalty_per_day × overdue_days
            penalty = self.model.NewIntVar(
                0, int(penalty_per_day * 168 * 1000),  # Scale by 1000
                f"penalty_{task.id}"
            )
            self.model.Add(
                penalty == int(penalty_per_day * 1000) * self.overdue_days_vars[task.id]
            )
            overdue_penalties[task.id] = penalty

        return overdue_penalties
    
    def _set_objective(self):
        """Set the objective function."""
        # Maximize: revenue - lost_revenue_from_breakdown - overdue_penalties - cost of overtime
        
        objective_terms = []
        
        # Lost revenue from downtime, for scheduled tasks downtime == duration of work
        # for breakdown downtime is duration of repair + potential delay of task start
        if self.breakdown:
            self.downtime_cost_from_breakdown = self._lost_revenue_from_downtime_for_breakdown()
            objective_terms.append(-self.downtime_cost_from_breakdown)
    
        self.downtime_cost_for_scheduled_tasks = self._lost_revenue_from_downtime_for_scheduled_tasks()
        # add each task's downtime cost to the objective terms
        for task_id, downtime_cost in self.downtime_cost_for_scheduled_tasks.items():
            objective_terms.append(-downtime_cost)
        
        self.overdue_penalties = self._calculate_overdue_penalties()
        for task_id, overdue_penalty in self.overdue_penalties.items():
            objective_terms.append(-overdue_penalty)

        self.all_tasks_overtime_costs = self._calculate_overtime_costs()
        for task_id, overtime_cost in self.all_tasks_overtime_costs.items():
            objective_terms.append(-overtime_cost)
 
        
        self.spill_over_task_penalties = self._calculate_spill_over_task_penalties()
        for task_id, spill_over_penalty in self.spill_over_task_penalties.items():
            objective_terms.append(-spill_over_penalty)
            
        # Maximize (minimize negative)
        if objective_terms:
            self.model.Maximize(sum(objective_terms))
        else:
            # Dummy objective if no terms
            self.model.Maximize(0)
    
    def solve(self) -> Dict:
        """Solve the optimization problem."""
        self.build_model()
        
        # Solve
        status = self.solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution()
        else:
            return {"error": "No solution found", "status": status}
    
    def _extract_solution(self) -> Dict:
        """Extract solution from solver."""
        try: 
            downtime_cost_for_breakdown = self.solver.Value(self.downtime_cost_from_breakdown) / 1000
        except AttributeError:
            downtime_cost_for_breakdown = 0
        
        # Get dates used for revenue calculation
        revenue_dates = getattr(self, 'revenue_calculation_dates', None)
        
        solution = {
            "tasks": [],
            "breakdown": None,
            "objective_value": self.solver.ObjectiveValue() / 1000,
            "downtime_cost_for_breakdown": downtime_cost_for_breakdown,
            "downtime_cost_for_scheduled_tasks": sum([self.solver.Value(cost) / 1000 for cost in self.downtime_cost_for_scheduled_tasks.values()]),
            "revenue_calculation_dates": revenue_dates,
            "cost_of_overtime": sum([self.solver.Value(cost) / 1000 for cost in self.all_tasks_overtime_costs.values()]),
            "cost_of_spill_over": sum([self.solver.Value(penalty) / 1000 for penalty in self.spill_over_task_penalties.values()])
        }
        cost_metrics_for_llm_explanation = {
            "downtime_cost_for_breakdown": downtime_cost_for_breakdown,
            "downtime_cost_for_scheduled_tasks": {task_id:self.solver.Value(cost) / 1000 for task_id, cost in self.downtime_cost_for_scheduled_tasks.items()},
            "cost_of_overtime": {task_id:self.solver.Value(cost) / 1000 for task_id, cost in self.all_tasks_overtime_costs.items()},
            "cost_of_spill_over": {task_id: self.solver.Value(penalty) / 1000 for task_id, penalty in self.spill_over_task_penalties.items()},
            "overdue_penalties": {task_id: self.solver.Value(penalty) / 1000 for task_id, penalty in self.overdue_penalties.items()}
        }
        
        # Extract task solutions
        for task in self.tasks:
            start_hours = self.solver.Value(self.task_start_vars[task.id])
            start_time = self._hours_to_time(start_hours)
            finish_time = start_time + timedelta(hours=task.duration_hours)
            
            overdue_days = self.solver.Value(self.overdue_days_vars[task.id])
            
            task_solution = {
                "id": task.id,
                "windmill_id": task.windmill_id,
                "start_time": start_time.isoformat(),
                "finish_time": finish_time.isoformat(),
                "duration_hours": task.duration_hours
            }
            
            if overdue_days > 0:
                if self.overdue_penalty_per_day:
                    penalty_per_day = self.overdue_penalty_per_day
                else:
                    penalty_per_day = 3000.0  # Hardcoded default penalty
                
                task_solution["overdue_info"] = {
                    "days_overdue": overdue_days,
                    "penalty_cost": penalty_per_day * overdue_days
                }
            
            solution["tasks"].append(task_solution)
        
        # Extract breakdown solution
        if self.breakdown:
            start_hours = self.solver.Value(self.breakdown_start_var)
            start_time = self._hours_to_time(start_hours)
            finish_time = start_time + timedelta(
                hours=self.breakdown.estimated_repair_duration_hours
            )
            
            solution["breakdown"] = {
                "id": self.breakdown.id,
                "windmill_id": self.breakdown.windmill_id,
                "start_time": start_time.isoformat(),
                "finish_time": finish_time.isoformat(),
                "duration_hours": self.breakdown.estimated_repair_duration_hours
            }
        
        return solution, cost_metrics_for_llm_explanation


"""Calculation utilities for revenue and objective function evaluation."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Windmill, WeatherForecast, Task, BreakdownEvent


class RevenueCalculator:
    """Calculates revenue based on wind speed using cubic relationship."""
    
    @staticmethod
    def calculate_power_mw(wind_speed_ms: float, windmill: Windmill) -> float:
        """
        Calculate power in MW based on wind speed.
        Power is proportional to wind speed cubed.
        """
        if wind_speed_ms < windmill.cut_in_speed_ms:
            return 0.0
        if wind_speed_ms > windmill.cut_out_speed_ms:
            return 0.0
        
        # Power = capacity × min(1.0, (wind_speed / rated_wind_speed)³)
        power_factor = min(1.0, (wind_speed_ms / windmill.rated_wind_speed_ms) ** 3)
        return windmill.capacity_mw * power_factor
    
    @staticmethod
    def calculate_revenue_per_hour(wind_speed_ms: float, windmill: Windmill) -> float:
        """
        Calculate revenue per hour based on wind speed.
        Revenue = Power (MW) × price_per_MWh
        """
        power_mw = RevenueCalculator.calculate_power_mw(wind_speed_ms, windmill)
        return power_mw * windmill.revenue_per_mwh
    

    @staticmethod
    def generate_revenue_matrix(windmills: List[Windmill]) -> Dict[str, Dict[int, float]]:
        """
        Generate a matrix of revenue per hour for each windmill at each wind speed.
        
        Args:
            windmills: List of Windmill objects
            
        Returns:
            Dictionary in format: {windmill_id: {wind_speed: revenue_per_hour, ...}}
            where wind_speed is integer m/s from 0 to max cut_out_speed
        """
        if not windmills:
            return {}
        
        # Find the highest cut_out_speed among all windmills
        max_cut_out_speed = max(wm.cut_out_speed_ms for wm in windmills)
        max_wind_speed = int(max_cut_out_speed)
        
        result = {}
        
        for windmill in windmills:
            windmill_revenues = {}
            
            for wind_speed in range(0, max_wind_speed + 1):
                # calculate_revenue_per_hour already returns 0 for speeds
                # outside cut_in and cut_out range
                revenue = RevenueCalculator.calculate_revenue_per_hour(
                    float(wind_speed), windmill
                )
                windmill_revenues[wind_speed] = round(revenue, 2)
            
            result[windmill.id] = windmill_revenues
        
        return result


class ObjectiveValueCalculator:
    """Calculates objective function terms from a schedule without optimization."""
    
    def __init__(
        self,
        planning_horizon_start: str,
        spill_over_cutoff_date: str,
        tasks: List[Task],
        windmills: List[Windmill],
        weather_forecasts: List[WeatherForecast],
        revenue_matrix: Dict[str, Dict[int, float]],
        overdue_penalty_per_day: float = 3000.0,
        overtime_cost_per_hour: float = 500.0,
        spill_over_penalty_routine: float = 5000.0,
        spill_over_penalty_repairs: float = 10000.0,
        breakdown: Optional[BreakdownEvent] = None
    ):
        self.tasks = tasks
        self.breakdown = breakdown
        self.windmills = {wm.id: wm for wm in windmills}
        self.weather_forecasts = weather_forecasts
        self.revenue_matrix = revenue_matrix
        self.overdue_penalty_per_day = overdue_penalty_per_day
        self.overtime_cost_per_hour = overtime_cost_per_hour
        self.spill_over_penalty_routine = spill_over_penalty_routine
        self.spill_over_penalty_repairs = spill_over_penalty_repairs
        
        # Create weather lookup by date
        self.weather_by_date = {fc.date: fc for fc in weather_forecasts}
        
        # Parse dates
        self.planning_start = datetime.strptime(
            planning_horizon_start[:len("YYYY-MM-DD")], '%Y-%m-%d'
        ).replace(tzinfo=None)
        self.spill_over_cutoff_date = datetime.strptime(
            spill_over_cutoff_date[:len("YYYY-MM-DD")], '%Y-%m-%d'
        ).replace(tzinfo=None)
    
    def _time_to_hours(self, dt: datetime) -> int:
        """Convert datetime to hours from planning start."""
        delta = dt.replace(tzinfo=None) - self.planning_start
        return int(delta.total_seconds() / 3600)
    
    def _hours_to_time(self, hours: int) -> datetime:
        """Convert hours from planning start to datetime."""
        return self.planning_start + timedelta(hours=hours)
    
    def _get_wind_speed_for_hour(self, hour: int = None, date: str = None) -> float:
        """Get wind speed for a given hour from planning start."""
        if hour is None and date is not None:
            return self.weather_by_date[date].wind_speed_ms
        elif hour is not None:
            dt = self._hours_to_time(hour)
            date_str = dt.strftime("%Y-%m-%d")
            if date_str in self.weather_by_date:
                return self.weather_by_date[date_str].wind_speed_ms
            # Fallback to average if date not found
            if self.weather_forecasts:
                return sum(fc.wind_speed_ms for fc in self.weather_forecasts) / len(self.weather_forecasts)
            return 0.0
        else:
            raise ValueError("Either hour or date must be provided")

    
    def _get_revenue_for_hour(self, windmill_id: str, hour: int = None, date: str = None) -> float:
        """Get revenue per hour for a windmill at a given hour based on wind speed."""
        wind_speed = self._get_wind_speed_for_hour(hour, date)
        wind_speed_key = int(wind_speed)
        if windmill_id in self.revenue_matrix:
            windmill_revenues = self.revenue_matrix[windmill_id]
            if wind_speed_key in windmill_revenues:
                return windmill_revenues[wind_speed_key]
        return 0.0
    
    def _parse_task_start_time(self, task: Task) -> Optional[datetime]:
        """Parse task start_time to datetime."""
        if not task.start_time:
            return None
        return datetime.fromisoformat(
            task.start_time.replace('Z', '+00:00')
        ).replace(tzinfo=None)
    
    def _parse_latest_finish(self, task: Task) -> datetime:
        """Parse task latest_finish to datetime."""
        return datetime.fromisoformat(
            task.latest_finish.replace('Z', '+00:00')
        ).replace(tzinfo=None)
    
    def calculate_overdue_tasks(self) -> Dict:
        """
        Calculate overdue information for each task.
        
        Returns:
            Dict with task_id -> {days_overdue, penalty_cost} for overdue tasks
        """
        overdue_tasks = {}
        
        for task in self.tasks:
            if task.task_type == "preventive":
                continue
            start_time = self._parse_task_start_time(task)
            if not start_time:
                continue
            
            finish_time = start_time + timedelta(hours=task.duration_hours)
            latest_finish = self._parse_latest_finish(task)
            
            if finish_time > latest_finish:
                overdue_hours = (finish_time - latest_finish).total_seconds() / 3600
                overdue_days = int((overdue_hours + 23) // 24)  # Ceiling division
                
                overdue_tasks[task.id] = {
                    "days_overdue": overdue_days,
                    "penalty_cost": self.overdue_penalty_per_day * overdue_days
                }
        
        return overdue_tasks
    
    def calculate_total_penalties(self) -> float:
        """
        Calculate total overdue penalties.
        
        Returns:
            Total penalty amount in euros
        """
        overdue_tasks = self.calculate_overdue_tasks()
        return sum(info["penalty_cost"] for info in overdue_tasks.values())
    
    def calculate_downtime_cost_for_breakdown(
        self, 
        breakdown_repair_start: Optional[datetime] = None
    ) -> float:
        """
        Calculate lost revenue from breakdown downtime.
        
        Args:
            breakdown_repair_start: When the repair starts. If None and breakdown exists,
                                   uses breakdown time as repair start.
        
        Returns:
            Total lost revenue in euros, 0.0 if no breakdown
        """
        if not self.breakdown:
            return 0.0
        
        windmill_id = self.breakdown.windmill_id
        repair_duration = self.breakdown.estimated_repair_duration_hours
        
        breakdown_time = datetime.fromisoformat(
            self.breakdown.breakdown_time.replace('Z', '+00:00')
        ).replace(tzinfo=None)
        breakdown_time_hours = self._time_to_hours(breakdown_time)
        
        # Use provided repair start or breakdown time
        if breakdown_repair_start:
            repair_start_hours = self._time_to_hours(breakdown_repair_start)
        else:
            repair_start_hours = breakdown_time_hours
        
        repair_finish_hours = repair_start_hours + repair_duration
        
        # Calculate lost revenue: sum revenue for each hour from breakdown to repair finish
        total_lost = 0.0
        for hour in range(breakdown_time_hours, repair_finish_hours):
            revenue = self._get_revenue_for_hour(windmill_id, hour)
            total_lost += revenue
        
        return total_lost

    def calculate_downtime_cost_for_scheduled_tasks(self) -> Dict:
        """
        Calculate downtime cost for scheduled tasks.
        
        Returns:
            Dict with task_id -> {downtime_cost}
        """
        downtime_cost_for_scheduled_tasks = {}
        for task in self.tasks:
            start_time = self._parse_task_start_time(task)
            if start_time >= self.spill_over_cutoff_date:
                downtime_cost_for_scheduled_tasks[task.id] = 0
            else:
                revenue_per_hour_on_a_given_day = self._get_revenue_for_hour(
                    task.windmill_id, date=start_time.strftime("%Y-%m-%d")
                )
                downtime_cost_for_scheduled_tasks[task.id] = (
                    revenue_per_hour_on_a_given_day * task.duration_hours
                )
        
        return downtime_cost_for_scheduled_tasks
    
    def calculate_cost_of_overtime(self) -> Dict:
        """
        Calculate overtime cost for all tasks.
        Overtime is hours worked between 18:00 and 06:00.
        
        Returns:
            Dict with task_id -> {overtime_hours, overtime_cost} and "total" key
        """
        overtime_info = {}
        total_overtime_cost = 0.0
        
        tasks_to_check = list(self.tasks)
        if self.breakdown:
            tasks_to_check.append(self.breakdown)
        
        for task in tasks_to_check:
            if isinstance(task, BreakdownEvent):
                # For breakdown, we need a start time - skip if not available
                # In practice, this would come from the optimized schedule
                continue
            
            start_time = self._parse_task_start_time(task)
            if not start_time:
                continue
            
            duration = task.duration_hours
            start_hours = self._time_to_hours(start_time)
            
            overtime_hours = 0
            for offset in range(duration):
                abs_hour = start_hours + offset
                dt = self._hours_to_time(abs_hour)
                hour_of_day = dt.hour
                
                # Overtime if hour_of_day >= 18 or hour_of_day < 6
                if hour_of_day >= 18 or hour_of_day < 6:
                    overtime_hours += 1
            
            overtime_cost = overtime_hours * self.overtime_cost_per_hour
            overtime_info[task.id] = {
                "overtime_hours": overtime_hours,
                "overtime_cost": overtime_cost
            }
            total_overtime_cost += overtime_cost
        
        overtime_info["total"] = total_overtime_cost
        return overtime_info
    
    def calculate_cost_of_spill_over(self) -> Dict:
        """
        Calculate spill over penalties for tasks finishing after cutoff date.
        
        Returns:
            Dict with task_id -> {is_spill_over, penalty} and "total" key
        """
        spill_over_info = {}
        total_spill_over_cost = 0.0
        
        spill_over_cutoff_hours = self._time_to_hours(self.spill_over_cutoff_date)
        
        for task in self.tasks:
            start_time = self._parse_task_start_time(task)
            if not start_time:
                continue
            
            start_hours = self._time_to_hours(start_time)
            finish_hours = start_hours + task.duration_hours
            
            is_spill_over = finish_hours > spill_over_cutoff_hours
            
            if is_spill_over:
                # Choose penalty based on task type
                task_type = getattr(task, "task_type", None)
                if task_type == "preventive":
                    penalty = self.spill_over_penalty_routine
                elif task_type == "corrective":
                    penalty = self.spill_over_penalty_repairs
                else:
                    penalty = 0.0
            else:
                penalty = 0.0
            
            spill_over_info[task.id] = {
                "is_spill_over": is_spill_over,
                "penalty": penalty
            }
            total_spill_over_cost += penalty
        
        spill_over_info["total"] = total_spill_over_cost
        return spill_over_info
    
    def calculate_all(self, breakdown_repair_start: Optional[datetime] = None) -> Dict:
        """
        Calculate all objective function terms.
        
        Args:
            breakdown_repair_start: When the breakdown repair starts (for lost revenue calc)
        
        Returns:
            Dict with all calculated terms and total objective value
        """
        overdue_tasks = self.calculate_overdue_tasks()
        total_penalties = self.calculate_total_penalties()
        downtime_cost_from_breakdown = self.calculate_downtime_cost_for_breakdown(breakdown_repair_start)
        downtime_cost_for_scheduled_tasks = self.calculate_downtime_cost_for_scheduled_tasks()
        overtime_info = self.calculate_cost_of_overtime()
        spill_over_info = self.calculate_cost_of_spill_over()
        
        downtime_cost_for_scheduled_tasks_total = sum(
            [cost for cost in downtime_cost_for_scheduled_tasks.values()]
        )
        if overdue_tasks:
            overdue_tasks_total = sum(
                [cost["penalty_cost"] for cost in overdue_tasks.values()]
            )
        else:
            overdue_tasks_total = 0

        total_costs = (
            overdue_tasks_total +
            total_penalties +
            downtime_cost_from_breakdown +
            downtime_cost_for_scheduled_tasks_total +
            overtime_info["total"] +
            spill_over_info["total"]
        )
        
        return {
            "overdue_tasks": overdue_tasks,
            "total_penalties": total_penalties,
            "downtime_cost_for_breakdown": downtime_cost_from_breakdown,
            "downtime_cost_for_scheduled_tasks": downtime_cost_for_scheduled_tasks_total,
            "cost_of_overtime": overtime_info,
            "cost_of_spill_over": spill_over_info,
            "total_costs": total_costs,
            "objective_value": -total_costs  # Matches optimizer's maximization format
        }


"""Data models for the offshore wind re-planner."""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
from pathlib import Path


@dataclass
class Windmill:
    """Represents a windmill/turbine."""
    id: str
    name: str
    location: Dict[str, float]
    capacity_mw: float
    revenue_per_mwh: float
    rated_wind_speed_ms: float
    cut_in_speed_ms: float
    cut_out_speed_ms: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Windmill':
        return cls(
            id=data['id'],
            name=data['name'],
            location=data['location'],
            capacity_mw=data['capacity_mw'],
            revenue_per_mwh=data['revenue_per_mwh'],
            rated_wind_speed_ms=data.get('rated_wind_speed_ms', 13.0),
            cut_in_speed_ms=data.get('cut_in_speed_ms', 3.5),
            cut_out_speed_ms=data.get('cut_out_speed_ms', 25.0)
        )


@dataclass
class WeatherForecast:
    """Represents weather forecast for a day."""
    date: str
    wind_speed_ms: float
    wave_height_m: float
    maintenance_possible: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WeatherForecast':
        return cls(
            date=data['date'],
            wind_speed_ms=data['wind_speed_ms'],
            wave_height_m=data['wave_height_m'],
            maintenance_possible=data['maintenance_possible']
        )


@dataclass
class Resource:
    """Represents a maintenance crew/boat."""
    id: str
    type: str
    name: str
    daily_working_hours: int
    rest_hours_after_work: int
    qualifications: List[str]
    base_location: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Resource':
        return cls(
            id=data['id'],
            type=data['type'],
            name=data['name'],
            daily_working_hours=data['daily_working_hours'],
            rest_hours_after_work=data['rest_hours_after_work'],
            qualifications=data['qualifications'],
            base_location=data['base_location']
        )


@dataclass
class Task:
    """Represents a maintenance task."""
    id: str
    windmill_id: str
    task_type: str
    description: str
    duration_hours: int
    latest_finish: str
    required_qualifications: List[str]
    dependencies: List[str]
    start_time: Optional[str] = None
    estimated_revenue_loss_if_delayed: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(
            id=data['id'],
            windmill_id=data['windmill_id'],
            task_type=data['task_type'],
            description=data['description'],
            duration_hours=data['duration_hours'],
            latest_finish=data['latest_finish'],
            required_qualifications=data['required_qualifications'],
            dependencies=data.get('dependencies', []),
            start_time=data.get('start_time'),
            estimated_revenue_loss_if_delayed=data.get('estimated_revenue_loss_if_delayed')
        )


@dataclass
class BreakdownEvent:
    """Represents a breakdown event."""
    id: str
    windmill_id: str
    breakdown_time: str
    description: str
    estimated_repair_duration_hours: int
    required_qualifications: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BreakdownEvent':
        return cls(
            id=data['id'],
            windmill_id=data['windmill_id'],
            breakdown_time=data['breakdown_time'],
            description=data['description'],
            estimated_repair_duration_hours=data['estimated_repair_duration_hours'],
            required_qualifications=data['required_qualifications']
        )


class DataLoader:
    """Loads data from JSON files."""
    
    def __init__(self, data_dir: str = "backend/data"):
        self.data_dir = Path(data_dir)
    
    def load_windmills(self) -> List[Windmill]:
        """Load windmills from JSON file."""
        with open(self.data_dir / "windmills.json", 'r') as f:
            data = json.load(f)
        return [Windmill.from_dict(wm) for wm in data['windmills']]
    
    def load_weather(self) -> tuple[List[WeatherForecast], Dict[str, Any]]:
        """Load weather forecast from JSON file."""
        with open(self.data_dir / "weather.json", 'r') as f:
            data = json.load(f)
        forecasts = [WeatherForecast.from_dict(fc) for fc in data['forecast']]
        config = {
            'wind_threshold_ms': data.get('wind_threshold_ms', 15.0),
            'wave_threshold_m': data.get('wave_threshold_m', 2.0)
        }
        return forecasts, config
    
    def load_resources(self) -> List[Resource]:
        """Load resources from JSON file."""
        with open(self.data_dir / "resources.json", 'r') as f:
            data = json.load(f)
        return [Resource.from_dict(r) for r in data['resources']]
    
    def load_schedule(self) -> List[Task]:
        """Load schedule from JSON file."""
        with open(self.data_dir / "schedule.json", 'r') as f:
            data = json.load(f)
        return (
            [Task.from_dict(t) for t in data['tasks']], 
            data["planning_horizon_start"], 
            data["planning_horizon_end"], 
            data["spill_over_cutoff_date"]
        )
    
    def load_breakdown(self) -> Optional[BreakdownEvent]:
        """Load breakdown event from JSON file."""
        with open(self.data_dir / "breakdown.json", 'r') as f:
            data = json.load(f)
        if 'breakdown_event' in data:
            return BreakdownEvent.from_dict(data['breakdown_event'])
        return None
    
    def load_breakdown_from_file(self, filename: str) -> Optional[BreakdownEvent]:
        """Load breakdown event from a specific JSON file."""
        with open(self.data_dir / filename, 'r') as f:
            data = json.load(f)
        if 'breakdown_event' in data:
            return BreakdownEvent.from_dict(data['breakdown_event'])
        return None
    
    def load_distances(self) -> Dict[str, Dict[str, float]]:
        """Load distance matrix from JSON file."""
        with open(self.data_dir / "distances.json", 'r') as f:
            data = json.load(f)
        return data['travel_times']
    


# Unit Tests for optimizer.py

## Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py       # Shared fixtures
└── test_optimizer.py # 33 test cases
```

## Test Categories (33 tests total)

| Category | Tests | Description |
|----------|-------|-------------|
| Time Conversions | 6 | `_time_to_hours`, `_hours_to_time` roundtrips |
| Revenue Lookup | 5 | `_get_wind_speed_for_hour`, `_get_revenue_for_hour` |
| Basic Optimization | 5 | Single task solving, duration, objective value |
| Constraint Validation | 3 | Windmill overlap, resource conflicts, weather |
| Breakdown Handling | 4 | Breakdown scheduling, ASAP with high wind |
| Penalties & Costs | 4 | Overdue, spill-over, overtime penalties |
| Edge Cases | 3 | Infeasibility, empty tasks, dependencies |
| Task Locking | 1 | Locked tasks before breakdown |
| Configurable Parameters | 2 | Custom penalty/overtime costs |

## Running Tests

```bash
# Run all optimizer tests
python3 -m pytest backend/tests/test_optimizer.py -v

# Run specific test class
python3 -m pytest backend/tests/test_optimizer.py::TestBreakdownHandling -v

# Run with coverage (requires pytest-cov)
python3 -m pytest backend/tests/ --cov=backend/optimizer --cov-report=html
```


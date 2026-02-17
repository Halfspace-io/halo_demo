# Plan for Adding a Constraint to the Optimization Model

## Overview
This document outlines the process for adding a new constraint to the OR-Tools CP-SAT optimization model in `backend/optimizer.py`.

## Current Constraint Structure

The optimizer currently has these constraint types:
1. **Task Constraints** (`_add_task_constraints`) - Ensures tasks are assigned
2. **Resource Constraints** (`_add_resource_constraints`) - One resource per task, non-overlapping tasks
3. **Weather Constraints** (`_add_weather_constraints`) - Prevents work during bad weather
4. **Travel Time Constraints** (`_add_travel_time_constraints`) - Accounts for travel between locations
5. **Dependency Constraints** (`_add_dependency_constraints`) - Enforces task ordering

## Step-by-Step Plan

### Step 1: Define Your Constraint Requirements
**Questions to answer:**
- What should the constraint enforce? (e.g., max tasks per day, resource capacity limits, time windows)
- Which entities does it affect? (tasks, resources, windmills, breakdown events)
- Is it a hard constraint (must be satisfied) or soft constraint (penalty in objective)?

**Example constraints you might want to add:**
- Maximum number of tasks per resource per day
- Resource rest periods between tasks
- Minimum time between tasks at the same windmill
- Resource capacity limits (e.g., max hours per day)
- Task priority constraints
- Windmill-specific constraints

### Step 2: Identify Required Data
**Check if data exists:**
- Review `backend/models.py` for available fields
- Check JSON data files in `backend/data/`:
  - `schedule.json` - task data
  - `resources.json` - resource data
  - `windmills.json` - windmill data
  - `weather.json` - weather data
  - `distances.json` - travel times

**If new data is needed:**
- Add fields to the relevant model class in `models.py`
- Update JSON files with new fields
- Update `DataLoader` if needed

### Step 3: Create the Constraint Method
**Follow this pattern:**

```python
def _add_[your_constraint_name]_constraints(self):
    """Add constraints for [description]."""
    # Your constraint logic here
    pass
```

**Key OR-Tools CP-SAT patterns:**

1. **Simple constraint:**
   ```python
   self.model.Add(variable1 <= variable2)
   ```

2. **Conditional constraint (only if assigned):**
   ```python
   self.model.Add(constraint).OnlyEnforceIf(assignment_var)
   ```

3. **Either/or constraint:**
   ```python
   bool_var = self.model.NewBoolVar("name")
   self.model.Add(option1).OnlyEnforceIf(bool_var)
   self.model.Add(option2).OnlyEnforceIf(bool_var.Not())
   ```

4. **For all pairs:**
   ```python
   for i, item1 in enumerate(items):
       for item2 in items[i+1:]:
           # Add constraint between item1 and item2
   ```

### Step 4: Handle Both Tasks and Breakdown Events
**Important:** Most constraints need to handle both:
- Regular tasks (`self.tasks`)
- Breakdown events (`self.breakdown`)

**Pattern:**
```python
# Collect all tasks including breakdown
all_tasks = list(self.tasks)
if self.breakdown:
    all_tasks.append(self.breakdown)

for task in all_tasks:
    # Get appropriate variables
    if isinstance(task, BreakdownEvent):
        start_var = self.breakdown_start_var
        duration = task.estimated_repair_duration_hours
        # ... breakdown-specific logic
    else:
        start_var = self.task_start_vars[task.id]
        duration = task.duration_hours
        # ... regular task logic
```

### Step 5: Add Method Call to build_model()
**Location:** In `build_model()` method, around line 148-153

```python
# Add constraints
self._add_task_constraints()
self._add_resource_constraints()
self._add_weather_constraints()
self._add_travel_time_constraints()
self._add_dependency_constraints()
self._add_[your_constraint_name]_constraints()  # ADD YOUR NEW CONSTRAINT HERE
```

### Step 6: Implementation Checklist
- [ ] Create new constraint method
- [ ] Handle both tasks and breakdown events
- [ ] Use appropriate OR-Tools CP-SAT methods
- [ ] Add method call to `build_model()`
- [ ] Ensure constraint uses existing decision variables or creates new ones if needed
- [ ] Consider if constraint needs to interact with resource assignment variables

### Step 7: Testing
**Test your constraint:**
1. Run the optimizer with sample data
2. Verify the constraint is being enforced
3. Check edge cases (no breakdown, single task, etc.)
4. Validate solution makes sense

## Example: Adding a Resource Rest Period Constraint

Here's a concrete example of adding a constraint that enforces rest periods between tasks:

```python
def _add_resource_rest_period_constraints(self):
    """Ensure resources get rest_hours_after_work between tasks."""
    for resource in self.resources:
        resource_task_pairs = []
        
        # Collect all tasks this resource can do
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
        
        # Add rest period constraints for all pairs
        for i, (task1, start1, duration1, assigned1) in enumerate(resource_task_pairs):
            for task2, start2, duration2, assigned2 in resource_task_pairs[i+1:]:
                finish1 = start1 + duration1
                finish2 = start2 + duration2
                
                # Use same ordering variable as resource constraints
                task1_before_task2 = self.model.NewBoolVar(
                    f"rest_{task1.id}_before_{task2.id}_on_{resource.id}"
                )
                
                # If task1 before task2: task1 finish + rest <= task2 start
                self.model.Add(
                    finish1 + resource.rest_hours_after_work <= start2
                ).OnlyEnforceIf([assigned1, assigned2, task1_before_task2])
                
                # If task2 before task1: task2 finish + rest <= task1 start
                self.model.Add(
                    finish2 + resource.rest_hours_after_work <= start1
                ).OnlyEnforceIf([assigned1, assigned2, task1_before_task2.Not()])
```

## Common Decision Variables Available

- `self.task_start_vars[task.id]` - Start time for each task
- `self.task_assigned_vars[task.id]` - Whether task is assigned (usually always 1)
- `self.resource_task_vars[task.id][resource.id]` - Whether resource is assigned to task
- `self.breakdown_start_var` - Start time for breakdown repair
- `self.overdue_days_vars[task.id]` - Days overdue for each task

## Next Steps

1. **Tell me what constraint you want to add** - I can help you implement it specifically
2. **Review existing constraints** - Look at `_add_resource_constraints()` or `_add_travel_time_constraints()` for complex examples
3. **Start implementing** - Follow the steps above

## Questions to Consider

- Does your constraint need new decision variables?
- Should it be a hard constraint or soft (penalty in objective)?
- Does it apply to all tasks or only specific types?
- Does it need to coordinate with existing constraints?

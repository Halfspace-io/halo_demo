"""LLM-powered reasoning and explanations for optimization decisions."""
from dotenv import load_dotenv
from openai import OpenAI
import os
from typing import Dict, Optional

# Load environment variables
load_dotenv()


class GenerateLLMExplanation:
    """Generates natural language explanations for optimization decisions using GPT-4."""
    
    SYSTEM_PROMPT = """You are an offshore wind farm maintenance planner who is an expert in explaining offshore wind farm schedule optimization decisions.

    RULES:
    - DO NOT explain what optimization is or what the optimizer does - the user already knows
    - Just explain WHY this specific schedule was chosen
    - Use bullet points max 5 bullets, so do not use bullets on insignificant decisions (e.g. moving task003 from 08 to 06 on the same day)
    - Be extremely concise max 1-2 lines per bullet
    - Make references to tasks, dates and windpeeds, e.g. task001 was moved from Jan 17 to Jan 21 to reduce cost of downtime during high wind speeds on Jan 17th.
    - Focus on trade-offs made, e.g. the optimizer chose to fix the breakdown later because of low wind speeds in the coming days means the loss of revenue from downtime is smaller than the penalty for scheduled repair becoming overdue, if breakdown was fixed immediately the cost of downtime would have been higher.
    - Only focus on one cost driver at the time, e.g. avoiding spill over penalty and not avoiding spill over penalty and minimizing downtime downtime.
    - Remeber to take the full picture into account, e.g. if the optimizer chose to move T2 from Jan 18 to Jan 17 even though Jan 17 has higher wind speeds, this could be because this move allows for T1, which has longer duration, to be scheduled on the lower wind day; Jan 18 - this argument needs to be in the explanation.
    - DO NOT make up false arguments, like this one "T6 moved to Jan 17 to minimize downtime costs, as Jan 17 has lower winds than Jan 21." This is false because wind speeds are NOT lower on Jan 17 than on Jan 21. Or like this one: "T7 moved to Jan 25 to avoid spill-over penalties, as it was initially scheduled after the cutoff date." This is false because T7 was not scheduled after the cutoff date.
    - If tasks are moved from spill over days into regular days, explain how tasks were moved around to make room for the spill over tasks. Only use the "avoid spill-over penalties" argument for tasks that were initially scheduled after the spill-over cutoff date.


    FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
    The optimized schedule:
    Start by summarizing the impact of decisions made on the overall cost
    then list the most impacful decisions and why they were made.
    • [most impactful decision and why]
    • [second most impactful decision and why]
    • [etc.]
    with a new line between each bullet.

    EXAMPLE:
    The optimized schedule:
    • waits 2 days to fixe breakdown - as wind forecasts for the coming days are low, and fixing the breakdown immediately would push scheduled repair tasks past its deadline and incur a penalty for being overdue.
    • moves T1 from Jan 17 to Jan 21 to reduce cost of downtime during high wind speeds on Jan 17th compared to Jan 21st.
    • pays overtime to complete T3 on Jan 18 to avoid a penalty for being overdue.
    • T2 moved to Jan 17 to make room for T1 on Jan 18, which has longer duration and is therefore more expensive high wind speeds days.
    """

    def __init__(self):
        """Initialize the LLM explanation generator."""
        self.client = None
        if os.getenv("OPENAI_API_KEY"):
            self.client = OpenAI()
    
    def is_available(self) -> bool:
        """Check if OpenAI client is configured."""
        return self.client is not None
    
    def explain_optimization(
        self,
        original_schedule: Dict,
        optimized_schedule: Dict,
        breakdown_info: Optional[Dict],
        weather_data: Dict,
        cost_parameters: Dict,
        cost_metrics_on_task_level: Dict
    ) -> Dict:
        """
        Generate an explanation for the optimization decisions.
        
        Args:
            original_schedule: The original schedule before optimization
            optimized_schedule: The optimized schedule
            breakdown_info: Information about the breakdown event (if any)
            weather_data: Weather forecast data
            cost_parameters: Cost parameters used in optimization
            
        Returns:
            Dict with 'explanation' and 'model' keys, or 'error' key on failure
        """
        if not self.client:
            return {
                "error": "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
            }
        
        try:
            # Build the prompt
            prompt = self._build_prompt(
                original_schedule=original_schedule,
                optimized_schedule=optimized_schedule,
                breakdown_info=breakdown_info,
                weather_data=weather_data,
                cost_parameters=cost_parameters,
                cost_metrics_on_task_level=cost_metrics_on_task_level
            )
            
            # Call OpenAI GPT-4o (faster than GPT-4)
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            explanation = response.choices[0].message.content
            
            return {
                "explanation": explanation,
                "model": "gpt-4"
            }
            
        except Exception as e:
            import traceback
            return {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _build_prompt(
        self,
        original_schedule: Dict,
        optimized_schedule: Dict,
        breakdown_info: Optional[Dict],
        weather_data: Dict,
        cost_parameters: Dict,
        cost_metrics_on_task_level: Dict
    ) -> str:
        """Build a detailed prompt for the LLM to explain the optimization."""
        task_id_mapping = {
            "TASK001": "T1",
            "TASK002": "T2",
            "TASK003": "T3",
            "TASK004": "T4",
            "TASK005": "T5",
            "TASK006": "T6",
            "TASK007": "T7",
            "TASK008": "T8",
            "TASK009": "T9",
            "TASK010": "T10",
            "TASK011": "T11",
            "TASK012": "T12",
        }
        # Format weather forecast
        weather_str = self._format_weather(weather_data)
        days_where_maintenance_is_impossible_str = ", ".join([
            f["date"] for f in weather_data["forecast"] if not f["maintenance_possible"]
        ])
        
        # Format breakdown info
        breakdown_str = self._format_breakdown(breakdown_info)
        
        # Format cost parameters
        cost_str = self._format_cost_parameters(cost_parameters)
        
        # Format optimization results
        results_str = self._format_results(optimized_schedule)
        
        # Format task changes
        changes_str, overdue_str, breakdown_repair_str = self._format_task_changes(
            original_schedule, optimized_schedule, task_id_mapping
        )

        cost_metrics_on_task_level_string = self._format_cost_metrics_on_task_level(
            cost_metrics_on_task_level,
            task_id_mapping
            )

        # Build final prompt
        prompt = f"""Please explain why the optimizer chose this maintenance schedule.

{breakdown_str}

Use the Weather Forecast to reason about why tasks has been moved to a day with less wind, because shutting down a windmill to do maintenance is more expensive during days with high wind as higher wind means more revenue during uptime for windmills:
{weather_str}
On the following days maintenance is impossible: {days_where_maintenance_is_impossible_str}, so dont make up an argument about how a tasks was not scheduled on one of theese days because of high wind, as scheduling tasks on these days is not possible.
But use this information to explain why some tasks becomes overdue, because it was not possible to schedule them before their deadline due to rough weather.

{cost_str}
Here are the total costs from the optimization:
{results_str}
And here are the costs on task level from the optimization:
{cost_metrics_on_task_level_string}
{breakdown_repair_str}
please use the above information to explain the optimizer's decision to do the following task changes: (Original → Optimized):
{changes_str}
Note that the spill-over cutoff date is: {optimized_schedule.get('spill_over_cutoff_date', 'N/A')}. Only taks that had an Original start time after this date was penalized.

Explain the trade-offs the optimizer made. Specifically address:
1. If there was a breakdown, please answer why was the breakdown repair was scheduled at this time? What would have been the cost of fixing it immediately vs. waiting? If there was no breakdown - do not answer this question.
3. How did the wind forecast influence the decision about when to repair the breakdown?
2. If any tasks became overdue, explain if thay decision was because it was not possible to do this task before its dealine or because there was a economic reason to do so (e.g. the overdue penalty was smaller than the cost of downtime, due to high winds before the deadline)
4. If any tasks pushed past the spill-over date, please explain if this was because no other feasible solution existed or because there was a economic reason to do so (e.g. the spill-over penalty was smaller than the cost of downtime, due to high winds)"""

        return prompt
    
    def _format_weather(self, weather_data: Dict) -> str:
        """Format weather forecast for the prompt."""
        if not weather_data or 'forecast' not in weather_data:
            return "  No weather data available."
        
        weather_lines = []
        for fc in weather_data['forecast'][:10]:  # Limit to first 10 days
            weather_lines.append(f"  - {fc['date']}: {fc['wind_speed_ms']} m/s")
        return "\n".join(weather_lines)
    
    def _format_breakdown(self, breakdown_info: Optional[Dict]) -> str:
        """Format breakdown information for the prompt."""
        if not breakdown_info:
            return "No breakdown event."
        
        return f"""Breakdown Event:
  - Windmill: {breakdown_info.get('windmill_id', 'N/A')}
  - Time reported: {breakdown_info.get('breakdown_time', 'N/A')}
  - Description: {breakdown_info.get('description', 'N/A')}
  - Estimated repair duration: {breakdown_info.get('estimated_repair_duration_hours', 'N/A')} hours"""
    
    def _format_cost_parameters(self, cost_parameters: Dict) -> str:
        """Format cost parameters for the prompt."""
        return f"""Cost Parameters:
  - Overdue penalty: €{cost_parameters.get('overdue_penalty_per_day', 3000)} per day
  - Overtime cost: €{cost_parameters.get('overtime_cost_per_hour', 500)} per hour
  - Spill-over penalty (Preventive): €{cost_parameters.get('spill_over_penalty_routine', 5000)}
  - Spill-over penalty (Corrective): €{cost_parameters.get('spill_over_penalty_repairs', 10000)}"""
    
    def _format_results(self, optimized_schedule: Dict) -> str:
        """Format optimization results for the prompt."""
        return f"""Optimization Results:
  - Objective value: {optimized_schedule.get('objective_value', 'N/A')}
  - Downtime cost from breakdown: €{optimized_schedule.get('downtime_cost_for_breakdown', 0)}
  - Downtime cost from scheduled tasks: {optimized_schedule.get('downtime_cost_for_scheduled_tasks', 0)}
  - Cost of overtime: €{optimized_schedule.get('cost_of_overtime', 0)}
  - Cost of spill-over: €{optimized_schedule.get('cost_of_spill_over', 0)}"""
    
    def _format_task_changes(
        self, 
        original_schedule: Dict, 
        optimized_schedule: Dict,
        task_id_mapping: Dict
    ) -> tuple:
        """Format task changes, overdue tasks, and breakdown repair info."""
        original_tasks = {t['id']: t for t in original_schedule.get('tasks', [])}
        optimized_tasks = optimized_schedule.get('tasks', [])
        
        task_changes = []
        overdue_tasks = []
        breakdown_task = None
        
        for opt_task in optimized_tasks:
            task_id = opt_task['id']
            
            # Check if this is the breakdown repair task
            if opt_task.get('is_breakdown') or opt_task.get('task_type') == 'breakdown_repair':
                breakdown_task = opt_task
                continue
                
            orig_task = original_tasks.get(task_id)
            if orig_task:
                orig_start = orig_task.get('start_time', '')
                opt_start = opt_task.get('start_time', '')
                
                if orig_start != opt_start:
                    task_changes.append(
                        f"  - {task_id_mapping.get(task_id, task_id)} ({opt_task.get('task_type', '')}): "
                        f"moved from {orig_start[:16] if orig_start else 'N/A'} to {opt_start[:16] if opt_start else 'N/A'}"
                    )
                
                if opt_task.get('overdue_info'):
                    overdue_info = opt_task['overdue_info']
                    overdue_tasks.append(
                        f"  - {task_id_mapping.get(task_id, task_id)}: {overdue_info.get('days_overdue', 0)} days overdue, "
                        f"penalty €{overdue_info.get('penalty_cost', 0)}"
                    )
        
        changes_str = "\n".join(task_changes) if task_changes else "  No tasks were moved."
        overdue_str = "\n".join(overdue_tasks) if overdue_tasks else "  No tasks are overdue."
        
        breakdown_repair_str = ""
        if breakdown_task:
            breakdown_repair_str = "The optimizer chose to fix the breakdown at this time:\n"
            start_time = breakdown_task.get('start_time', 'N/A')
            if start_time and start_time != 'N/A':
                start_time = start_time[:16]
            breakdown_repair_str = f"""
Breakdown Repair Scheduled:
  - Start: {start_time}
  - Duration: {breakdown_task.get('duration_hours', 'N/A')} hours"""
        
        return changes_str, overdue_str, breakdown_repair_str

    def _format_cost_metrics_on_task_level(self, cost_metrics_on_task_level: Dict, task_id_mapping: Dict) -> str:
        """Format cost metrics on task level for the prompt."""
        string = ""
        for key in cost_metrics_on_task_level.keys():
            if type(cost_metrics_on_task_level[key]) == dict:
                string += f"The {key} for each task is: \n"
                for id, cost in cost_metrics_on_task_level[key].items():
                    string += f"{task_id_mapping.get(id, id)}: {cost}\t"
            else:
                string += f"{key} was {cost_metrics_on_task_level[key]} in total"
            string += "\n\n"
        
        return string


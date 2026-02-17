/** API client for backend communication */
const API_BASE_URL = 'http://localhost:5000';

class APIClient {
    async getSchedule() {
        const response = await fetch(`${API_BASE_URL}/schedule`);
        if (!response.ok) {
            throw new Error(`Failed to fetch schedule: ${response.statusText}`);
        }
        return await response.json();
    }

    async getWeather() {
        const response = await fetch(`${API_BASE_URL}/weather`);
        if (!response.ok) {
            throw new Error(`Failed to fetch weather: ${response.statusText}`);
        }
        return await response.json();
    }

    async getResources() {
        const response = await fetch(`${API_BASE_URL}/resources`);
        if (!response.ok) {
            throw new Error(`Failed to fetch resources: ${response.statusText}`);
        }
        return await response.json();
    }

    async getWindmills() {
        const response = await fetch(`${API_BASE_URL}/windmills`);
        if (!response.ok) {
            throw new Error(`Failed to fetch windmills: ${response.statusText}`);
        }
        return await response.json();
    }

    async getBreakdown() {
        const response = await fetch(`${API_BASE_URL}/breakdown`);
        if (!response.ok) {
            throw new Error(`Failed to fetch breakdown: ${response.statusText}`);
        }
        return await response.json();
    }

    async replan(overduePenaltyPerDay = null, overtimeCostPerHour = 500, spillOverRoutine = 5000, spillOverRepairs = 10000, breakdownFile = 'breakdown.json') {
        const body = {};
        if (overduePenaltyPerDay !== null) {
            body.overdue_penalty_per_day = overduePenaltyPerDay;
        }
        body.overtime_cost_per_hour = overtimeCostPerHour;
        body.spill_over_penalty_routine = spillOverRoutine;
        body.spill_over_penalty_repairs = spillOverRepairs;
        body.breakdown_file = breakdownFile;

        const response = await fetch(`${API_BASE_URL}/replan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `Failed to replan: ${response.statusText}`);
        }

        return await response.json();
    }

    async calculateDefaultPenalty() {
        const response = await fetch(`${API_BASE_URL}/calculate-penalty`);
        if (!response.ok) {
            throw new Error(`Failed to calculate penalty: ${response.statusText}`);
        }
        return await response.json();
    }

    async calculateObjective(overduePenaltyPerDay = 3000, overtimeCostPerHour = 500, spillOverRoutine = 5000, spillOverRepairs = 10000) {
        const body = {
            overdue_penalty_per_day: overduePenaltyPerDay,
            overtime_cost_per_hour: overtimeCostPerHour,
            spill_over_penalty_routine: spillOverRoutine,
            spill_over_penalty_repairs: spillOverRepairs
        };

        const response = await fetch(`${API_BASE_URL}/calculate-objective`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `Failed to calculate objective: ${response.statusText}`);
        }

        return await response.json();
    }

    async explainOptimization(originalSchedule, optimizedSchedule, breakdownInfo, weatherData, costParameters) {
        const body = {
            original_schedule: originalSchedule,
            optimized_schedule: optimizedSchedule,
            breakdown_info: breakdownInfo,
            weather_data: weatherData,
            cost_parameters: costParameters
        };

        const response = await fetch(`${API_BASE_URL}/explain-optimization`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                original_schedule: originalSchedule,
                optimized_schedule: optimizedSchedule,
                breakdown_info: breakdownInfo,
                weather_data: weatherData,
                cost_parameters: costParameters,
                cost_metrics: optimizedSchedule.cost_metrics_for_llm
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `Failed to explain optimization: ${response.statusText}`);
        }

        return await response.json();
    }
}

const apiClient = new APIClient();


/** Main application logic */
const scheduleViewer = new ScheduleViewer('schedule-viewer');

let originalSchedule = null;
let optimizedSchedule = null;
let originalObjectiveValues = null; // Objective values for original schedule
let currentExplanation = null; // AI-generated explanation for the optimization
let breakdownInfo = null;
let activeBreakdown = null; // Currently selected breakdown for visualization
let weatherData = null;
let currentView = 'original'; // 'original' or 'optimized'
let combinedTimeRange = null; // Shared time range for alignment

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadInitialData();
    setupEventListeners();
});

async function loadInitialData() {
    try {
        scheduleViewer.showLoading('Loading initial data...');
        
        // Load schedule
        originalSchedule = await apiClient.getSchedule();
        
        // Load weather data
        weatherData = await apiClient.getWeather();
        
        // Reset view to original
        currentView = 'original';
        activeBreakdown = null; // Reset active breakdown on initial load
        updateToggleButtons();
        renderCurrentView();

        // Load breakdown info
        await loadBreakdownInfo();
        
        // Calculate and display objective value for original schedule
        await loadOriginalObjectiveValues();

    } catch (error) {
        console.error('Error loading initial data:', error);
        scheduleViewer.showError(`Failed to load data: ${error.message}`);
    }
}

async function loadOriginalObjectiveValues() {
    try {
        // Get current penalty/cost values from inputs
        const penaltyValue = parseFloat(document.getElementById('penalty-input').value) || 3000;
        const overtimeCostValue = parseFloat(document.getElementById('overtime-cost-input').value) || 500;
        const spillOverRoutineValue = parseFloat(document.getElementById('spill-over-routine-input').value) || 5000;
        const spillOverRepairsValue = parseFloat(document.getElementById('spill-over-repairs-input').value) || 10000;
        
        originalObjectiveValues = await apiClient.calculateObjective(
            penaltyValue,
            overtimeCostValue,
            spillOverRoutineValue,
            spillOverRepairsValue
        );
        
        // Update revenue info display
        updateRevenueInfo();
    } catch (error) {
        console.error('Error calculating original objective values:', error);
    }
}

async function loadBreakdownInfo() {
    try {
        const breakdownData = await apiClient.getBreakdown();
        breakdownInfo = breakdownData;
        const breakdownDiv = document.getElementById('breakdown-info');
        
        if (!breakdownData.breakdowns || breakdownData.breakdowns.length === 0) {
            breakdownDiv.innerHTML = `
                <h3>Breakdown Information</h3>
                <p>No breakdown events found</p>
            `;
            return;
        }
        
        // Map breakdowns to their file names (first is breakdown.json, second is breakdown2.json)
        // Keep them in order: Breakdown #1 from breakdown.json, Breakdown #2 from breakdown2.json
        const breakdownFiles = ['breakdown.json', 'breakdown2.json'];
        
        // Map each breakdown to its file (keep original order, don't sort)
        const breakdownsWithFiles = breakdownData.breakdowns.map((breakdown, index) => ({
            ...breakdown,
            file: breakdownFiles[index] || `breakdown${index + 1}.json`
        }));
        
        const sortedBreakdowns = breakdownsWithFiles;
        
        // Format breakdown time
        const formatBreakdownTime = (timeString) => {
            const date = new Date(timeString);
            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        };
        
        // Generate HTML for each breakdown
        const breakdownsHtml = sortedBreakdowns.map((breakdown, index) => {
            return `
                <div class="breakdown-item" data-breakdown-file="${breakdown.file}" style="margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #f56565; position: relative;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div style="font-weight: 600; color: #5AADE0;">
                            Breakdown #${index + 1}
                        </div>
                        <button class="replan-breakdown-btn" data-breakdown-file="${breakdown.file}">
                            Re-plan with this
                        </button>
                    </div>
                    <div style="font-size: 0.95em; line-height: 1.8;">
                        <div><strong>Windmill affected:</strong> ${breakdown.windmill_id}</div>
                        <div><strong>Time of breakdown:</strong> ${formatBreakdownTime(breakdown.breakdown_time)}</div>
                        <div><strong>Description of breakdown:</strong> ${breakdown.description || 'N/A'}</div>
                        <div><strong>Repair duration:</strong> ${breakdown.estimated_repair_duration_hours} hours</div>
                    </div>
                </div>
            `;
        }).join('');
        
        breakdownDiv.innerHTML = `
            <button id="optimize-schedule-btn" class="optimize-schedule-btn">Optimize Schedule</button>
            <h3>Breakdown Information</h3>
            <div style="margin-top: 15px;">
                ${breakdownsHtml}
            </div>
        `;
        
        // Add event listener for optimize schedule button
        document.getElementById('optimize-schedule-btn').addEventListener('click', () => {
            performReplan(null);
        });
        
        // Add event listeners to replan buttons
        document.querySelectorAll('.replan-breakdown-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const breakdownFile = btn.getAttribute('data-breakdown-file');
                
                // Find the breakdown data for this file
                const breakdown = sortedBreakdowns.find(b => b.file === breakdownFile);
                if (breakdown) {
                    activeBreakdown = breakdown;
                }
                
                // Remove active state from all breakdown containers and buttons
                document.querySelectorAll('.breakdown-item').forEach(item => {
                    item.classList.remove('active');
                });
                document.querySelectorAll('.replan-breakdown-btn').forEach(button => {
                    button.classList.remove('active');
                });
                
                // Add active state to clicked breakdown container and button
                const breakdownContainer = document.querySelector(`.breakdown-item[data-breakdown-file="${breakdownFile}"]`);
                if (breakdownContainer) {
                    breakdownContainer.classList.add('active');
                }
                btn.classList.add('active');
                
                // Update the chart with the active breakdown
                renderCurrentView();
                
                await performReplanWithBreakdown(breakdownFile);
            });
        });
        
    } catch (error) {
        console.error('Error loading breakdown info:', error);
        const breakdownDiv = document.getElementById('breakdown-info');
        breakdownDiv.innerHTML = `
            <h3>Breakdown Information</h3>
            <div class="error" style="margin-top: 10px;">
                Failed to load breakdown information: ${error.message}
            </div>
        `;
    }
}

function setupEventListeners() {
    // Re-plan button
    document.getElementById('replan-btn').addEventListener('click', async () => {
        await performReplan();
    });

    // Toggle buttons
    document.getElementById('view-original-btn').addEventListener('click', () => {
        currentView = 'original';
        updateToggleButtons();
        renderCurrentView();
    });

    document.getElementById('view-optimized-btn').addEventListener('click', () => {
        currentView = 'optimized';
        updateToggleButtons();
        renderCurrentView();
    });
}

async function performReplan(breakdownFile = null) {
    // Use active breakdown file if no specific file provided
    if (!breakdownFile && activeBreakdown && activeBreakdown.file) {
        breakdownFile = activeBreakdown.file;
    } else if (!breakdownFile) {
        breakdownFile = null;
    }
    
    try {
        const penaltyInput = document.getElementById('penalty-input');
        const penaltyValue = parseFloat(penaltyInput.value) || null;
        
        const overtimeCostInput = document.getElementById('overtime-cost-input');
        const overtimeCostValue = parseFloat(overtimeCostInput.value) || 500;
        
        const spillOverRoutineInput = document.getElementById('spill-over-routine-input');
        const spillOverRoutineValue = parseFloat(spillOverRoutineInput.value) || 5000;
        
        const spillOverRepairsInput = document.getElementById('spill-over-repairs-input');
        const spillOverRepairsValue = parseFloat(spillOverRepairsInput.value) || 10000;

        scheduleViewer.showLoading('Optimizing schedule...');

        // Perform re-planning
        optimizedSchedule = await apiClient.replan(penaltyValue, overtimeCostValue, spillOverRoutineValue, spillOverRepairsValue, breakdownFile);

        // Load weather data if not already loaded
        if (!weatherData) {
            weatherData = await apiClient.getWeather();
        }

        // Switch to optimized view and render
        currentView = 'optimized';
        updateToggleButtons();
        renderCurrentView();

        // Update revenue info
        updateRevenueInfo();

        // Show success message
        showMessage('Schedule optimized successfully!', 'success');
        
        // Generate AI explanation
        await generateExplanation(penaltyValue, overtimeCostValue, spillOverRoutineValue, spillOverRepairsValue);

    } catch (error) {
        console.error('Error during replanning:', error);
        scheduleViewer.showError(`Re-planning failed: ${error.message}`);
        showMessage(`Error: ${error.message}`, 'error');
    }
}

async function generateExplanation(penaltyValue, overtimeCostValue, spillOverRoutineValue, spillOverRepairsValue) {
    // Set loading state and update UI
    currentExplanation = { loading: true };
    updateRevenueInfo();
    
    try {
        // Build cost parameters
        const costParameters = {
            overdue_penalty_per_day: penaltyValue || 3000,
            overtime_cost_per_hour: overtimeCostValue,
            spill_over_penalty_routine: spillOverRoutineValue,
            spill_over_penalty_repairs: spillOverRepairsValue
        };
        
        // Call the explanation API
        const result = await apiClient.explainOptimization(
            originalSchedule,
            optimizedSchedule,
            activeBreakdown,
            weatherData,
            costParameters
        );
        
        // Store the explanation and update UI
        currentExplanation = { text: result.explanation };
        updateRevenueInfo();
        
    } catch (error) {
        console.error('Error generating explanation:', error);
        currentExplanation = { error: error.message };
        updateRevenueInfo();
    }
}

async function performReplanWithBreakdown(breakdownFile) {
    await performReplan(breakdownFile);
}

function updateToggleButtons() {
    const originalBtn = document.getElementById('view-original-btn');
    const optimizedBtn = document.getElementById('view-optimized-btn');
    
    if (currentView === 'original') {
        originalBtn.classList.add('active');
        originalBtn.disabled = false;
        optimizedBtn.classList.remove('active');
        optimizedBtn.disabled = !optimizedSchedule;
    } else {
        optimizedBtn.classList.add('active');
        optimizedBtn.disabled = false;
        originalBtn.classList.remove('active');
        originalBtn.disabled = false;
    }
}

function calculateCombinedTimeRange() {
    if (!originalSchedule) {
        return null;
    }

    // Use planning horizon from schedule.json
    const minTime = new Date(originalSchedule.planning_horizon_start);
    const maxTime = new Date(originalSchedule.planning_horizon_end);

    return { minTime, maxTime, totalMs: maxTime - minTime };
}

function renderCurrentView() {
    // Recalculate combined time range whenever we render
    combinedTimeRange = calculateCombinedTimeRange();
    
    // Create breakdown data object with active breakdown for visualization
    // Only show breakdown line after clicking "Re-plan with this"
    const breakdownDataForView = activeBreakdown ? {
        breakdowns: [activeBreakdown],
        breakdown_event: activeBreakdown
    } : null;
    
    if (currentView === 'original' && originalSchedule) {
        scheduleViewer.renderSchedule(originalSchedule, 'Original Schedule&emsp;&emsp;&emsp;&emsp;🟩: Preventive tasks&emsp;&emsp;🟢: Corrective tasks' , weatherData, breakdownDataForView, combinedTimeRange);
    } else if (currentView === 'optimized' && optimizedSchedule) {
        scheduleViewer.renderSchedule(optimizedSchedule, 'Optimized Schedule&emsp;&emsp;&emsp;&emsp;🟩: Preventive tasks&emsp;&emsp;🟢: Corrective tasks', weatherData, breakdownDataForView, combinedTimeRange);
    }
    
    // Update revenue info to match current view
    updateRevenueInfo();
}

function updateRevenueInfo() {
    const revenueDiv = document.getElementById('revenue-info');
    
    // Determine which data source to use based on current view
    let overdueTasks = 0;
    let totalPenalties = 0;
    let objectiveValue = 'N/A';
    let revenueLost = 0;
    let downtimeCostForScheduledTasks = 0;
    let costOfOvertime = 0;
    let costOfSpillOver = 0;
    let scheduleLabel = '';
    
    if (currentView === 'optimized' && optimizedSchedule) {
        // Use optimized schedule values
        scheduleLabel = '(Optimized)';
        
        optimizedSchedule.tasks.forEach(task => {
            if (task.overdue_info) {
                totalPenalties += task.overdue_info.penalty_cost || 0;
                overdueTasks++;
            }
        });
        
        objectiveValue = optimizedSchedule.objective_value;
        revenueLost = optimizedSchedule.downtime_cost_for_breakdown || 0;
        downtimeCostForScheduledTasks = optimizedSchedule.downtime_cost_for_scheduled_tasks || 0;
        costOfOvertime = optimizedSchedule.cost_of_overtime || 0;
        costOfSpillOver = optimizedSchedule.cost_of_spill_over || 0;
        
    } else if (originalObjectiveValues) {
        // Use original schedule values from ObjectiveValueCalculator
        scheduleLabel = '(Original)';
        
        const overdueTasksObj = originalObjectiveValues.overdue_tasks || {};
        overdueTasks = Object.keys(overdueTasksObj).length;
        totalPenalties = originalObjectiveValues.total_penalties || 0;
        objectiveValue = originalObjectiveValues.objective_value;
        revenueLost = originalObjectiveValues.downtime_cost_for_breakdown || 0;
        downtimeCostForScheduledTasks = originalObjectiveValues.downtime_cost_for_scheduled_tasks || 0;
        costOfOvertime = originalObjectiveValues.cost_of_overtime?.total || 0;
        costOfSpillOver = originalObjectiveValues.cost_of_spill_over?.total || 0;
        
    } else {
        // No data available yet
        revenueDiv.innerHTML = `
            <h3>Revenue Impact</h3>
            <p>Loading...</p>
        `;
        return;
    }

    // Build explanation section HTML
    let explanationHtml = '';
    if (currentView === 'optimized' && currentExplanation) {
        if (currentExplanation.loading) {
            explanationHtml = `
                <div class="ai-explanation" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e2e8f0;">
                    <div style="font-weight: 600; color: #5AADE0; margin-bottom: 8px;">🤖 AI Reasoning</div>
                    <div class="explanation-loading" style="display: flex; flex-direction: column; align-items: center; padding: 15px 0;">
                        <img src="visuals/sentinel_orchestrator_white_bckgrnd.jpg" alt="Sentinel AI" 
                             style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; 
                                    animation: pulse 1.5s ease-in-out infinite; margin-bottom: 10px;
                                    box-shadow: 0 0 20px rgba(90, 173, 224, 0.5);">
                        <div style="color: #5AADE0; font-size: 0.9em;">Generating explanation...</div>
                    </div>
                </div>
            `;
        } else if (currentExplanation.error) {
            explanationHtml = `
                <div class="ai-explanation" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e2e8f0;">
                    <div style="font-weight: 600; color: #5AADE0; margin-bottom: 8px;">🤖 AI Reasoning</div>
                    <div class="explanation-error" style="color: #e53e3e; font-size: 0.9em;">
                        Failed to generate: ${currentExplanation.error}
                    </div>
                </div>
            `;
        } else if (currentExplanation.text) {
            // Format bullet points nicely
            const formattedText = currentExplanation.text
                .replace(/•/g, '</li><li style="margin-bottom: 4px;">')
                .replace(/<\/li><li style="margin-bottom: 4px;">/, '<li style="margin-bottom: 4px;">')  // Fix first bullet
                .replace(/The optimized schedule:/gi, '<strong>The optimized schedule:</strong><ul style="margin: 8px 0 0 0; padding-left: 20px;">');
            
            explanationHtml = `
                <div class="ai-explanation" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e2e8f0;">
                    <div style="font-weight: 600; color: #5AADE0; margin-bottom: 8px;">🤖 AI Reasoning</div>
                    <div style="font-size: 0.9em; line-height: 1.6; color: #444;">
                        ${formattedText}${formattedText.includes('<ul') ? '</li></ul>' : ''}
                    </div>
                </div>
            `;
        }
    }

    revenueDiv.innerHTML = `
        <h3>Revenue Impact <span style="color: #5AADE0; font-size: 0.85em;">${scheduleLabel}</span></h3>
        <p><strong>Overdue Tasks:</strong> ${overdueTasks}</p>
        <p><strong>Total Penalties:</strong> €${totalPenalties.toFixed(2)}</p>
        <p><strong>Objective Value:</strong> ${typeof objectiveValue === 'number' ? objectiveValue.toFixed(2) : objectiveValue}</p>
        <p><strong>Downtime cost from breakdown:</strong> €${typeof revenueLost === 'number' ? revenueLost.toFixed(2) : revenueLost}</p>
        <p><strong>Downtime cost for scheduled tasks:</strong> €${typeof downtimeCostForScheduledTasks === 'number' ? downtimeCostForScheduledTasks.toFixed(2) : downtimeCostForScheduledTasks}</p>
        <p><strong>Cost of overtime:</strong> €${typeof costOfOvertime === 'number' ? costOfOvertime.toFixed(2) : costOfOvertime}</p>
        <p><strong>Cost of spill over:</strong> €${typeof costOfSpillOver === 'number' ? costOfSpillOver.toFixed(2) : costOfSpillOver}</p>
        ${explanationHtml}
    `;
}

function showMessage(message, type = 'info') {
    // Create a temporary message element
    const messageDiv = document.createElement('div');
    messageDiv.className = type === 'error' ? 'error' : 'success';
    messageDiv.textContent = message;
    
    // Insert at the top of the container
    const container = document.querySelector('.container');
    container.insertBefore(messageDiv, container.firstChild);
    
    // Remove after 5 seconds
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}


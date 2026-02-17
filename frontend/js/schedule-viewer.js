/** Schedule visualization component with Gantt chart */
class ScheduleViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    renderSchedule(schedule, title = 'Schedule', weatherData = null, breakdownData = null, timeRange = null) {
        if (!schedule || !schedule.tasks) {
            this.container.innerHTML = '<div class="error">No schedule data available</div>';
            return;
        }

        // Use provided time range or calculate from tasks
        if (!timeRange) {
            timeRange = this.calculateTimeRange(schedule.tasks);
        }
        
        const html = `
            <h3>${title}</h3>
            <div class="gantt-container">
                ${this.renderGanttChart(schedule.tasks, timeRange, weatherData, breakdownData, schedule.spill_over_cutoff_date)}
            </div>
        `;

        this.container.innerHTML = html;
    }

    calculateTimeRange(tasks) {
        let minTime = null;
        let maxTime = null;

        tasks.forEach(task => {
            const startTime = new Date(task.start_time);
            const finishTime = new Date(task.latest_finish || task.finish_time || 
                new Date(startTime.getTime() + (task.duration_hours || 0) * 3600000));
            
            // Also check original latest_finish for overdue visualization
            const originalLatestFinish = task.original_latest_finish ? 
                new Date(task.original_latest_finish) : null;
            const latestFinish = originalLatestFinish || 
                (task.latest_finish && !task.start_time ? new Date(task.latest_finish) : null);

            if (!minTime || startTime < minTime) minTime = startTime;
            if (!maxTime || finishTime > maxTime) maxTime = finishTime;
            if (latestFinish && (!maxTime || latestFinish > maxTime)) maxTime = latestFinish;
        });

        // Add some padding
        if (minTime && maxTime) {
            const padding = (maxTime - minTime) * 0.1;
            minTime = new Date(minTime.getTime() - padding);
            maxTime = new Date(maxTime.getTime() + padding);
        }

        return { minTime, maxTime, totalMs: maxTime - minTime };
    }

    renderGanttChart(tasks, timeRange, weatherData = null, breakdownData = null, spillOverCutoffDate = null) {
        if (!timeRange.minTime || !timeRange.maxTime) {
            return '<div class="error">Invalid time range</div>';
        }

        const dayWidth = 100; // pixels per day
        const rowHeight = 50;
        
        // Group tasks by windmill_id
        const tasksByWindmill = {};
        tasks.forEach(task => {
            const windmillId = task.windmill_id || 'Unknown';
            if (!tasksByWindmill[windmillId]) {
                tasksByWindmill[windmillId] = [];
            }
            tasksByWindmill[windmillId].push(task);
        });
        
        // Sort windmill IDs (WM001, WM002, etc.)
        const sortedWindmillIds = Object.keys(tasksByWindmill).sort((a, b) => {
            // Extract numeric part for proper sorting
            const numA = parseInt(a.replace(/\D/g, '')) || 0;
            const numB = parseInt(b.replace(/\D/g, '')) || 0;
            return numA - numB;
        });
        
        // Create task rows grouped by windmill
        const taskRows = [];
        const windmillRows = []; // For rendering windmill labels
        
        sortedWindmillIds.forEach((windmillId, windmillIndex) => {
            const windmillTasks = tasksByWindmill[windmillId];
            const rowTop = (windmillIndex * rowHeight) + 80; // Add 80px offset for headers
            
            // Store windmill row info for labels
            windmillRows.push({
                windmillId,
                top: rowTop,
                taskCount: windmillTasks.length
            });
            
            // Process each task for this windmill
            windmillTasks.forEach(task => {
                const actualStartTime = new Date(task.start_time);
                const finishTime = new Date(actualStartTime.getTime() + (task.duration_hours || 0) * 3600000);
                
                const originalLatestFinish = task.original_latest_finish ? 
                    new Date(task.original_latest_finish) : null;
                const latestFinish = originalLatestFinish || 
                    (task.latest_finish ? new Date(task.latest_finish) : null);

                const left = ((actualStartTime - timeRange.minTime) / timeRange.totalMs) * 100;
                const width = ((finishTime - actualStartTime) / timeRange.totalMs) * 100;

                let statusClass = 'on-time';
                let overdueWidth = 0;
                if (latestFinish && finishTime > latestFinish) {
                    statusClass = 'overdue';
                    overdueWidth = ((finishTime - latestFinish) / timeRange.totalMs) * 100;
                }

                const taskType = task.task_type || 'maintenance';
                const isBreakdown = task.is_breakdown || task.task_type === 'breakdown_repair';
                const overdueDays = latestFinish && finishTime > latestFinish ? 
                    Math.ceil((finishTime - latestFinish) / (1000 * 60 * 60 * 24)) : 0;
                const penaltyCost = task.overdue_info?.penalty_cost || 0;

                taskRows.push({
                    task,
                    top: rowTop, // All tasks for this windmill share the same row
                    left,
                    width,
                    overdueWidth,
                    statusClass,
                    isBreakdown,
                    overdueDays,
                    penaltyCost,
                    startTime: actualStartTime,
                    finishTime,
                    latestFinish,
                    taskType,
                    windmillId
                });
            });
        });

        const chartHeight = sortedWindmillIds.length * rowHeight + 100;
        const totalDays = Math.ceil(timeRange.totalMs / (1000 * 60 * 60 * 24));
        const chartWidth = Math.max(800, totalDays * dayWidth);
        const labelWidth = 220; // Width for task labels on the left

        // Generate date headers
        const dateHeaders = this.generateDateHeaders(timeRange.minTime, timeRange.maxTime);

        // Render weather blocks (transparent red bars for impossible days)
        const weatherBlocks = weatherData ? this.renderWeatherBlocks(weatherData, timeRange, chartHeight) : '';
        // Render breakdown time marker
        let breakdownMarker = '';
        if (breakdownData) {
            const breakdown = breakdownData.breakdown_event || (breakdownData.breakdowns && breakdownData.breakdowns[0]);
            if (breakdown && breakdown.breakdown_time) {
                const breakdownTime = new Date(breakdown.breakdown_time);
                if (breakdownTime >= timeRange.minTime && breakdownTime <= timeRange.maxTime) {
                    const left = ((breakdownTime - timeRange.minTime) / timeRange.totalMs) * 100;
                    breakdownMarker = `
                        <div style="position: absolute; top: 80px; left: ${left}%; width: 2px; height: ${chartHeight - 80}px; border-left: 2px dashed #f56565; z-index: 1; pointer-events: none;"></div>
                        <div style="position: absolute; top: 82px; left: ${left}%; transform: translateX(-50%); background: #f56565; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75em; font-weight: 600; white-space: nowrap; z-index: 2; pointer-events: none;">Breakdown reported</div>
                    `;
                }
            }
        }

        // Render spill over cutoff marker
        let spillOverMarker = '';
        if (spillOverCutoffDate) {
            const spillOverTime = new Date(spillOverCutoffDate);
            if (spillOverTime >= timeRange.minTime && spillOverTime <= timeRange.maxTime) {
                const left = ((spillOverTime - timeRange.minTime) / timeRange.totalMs) * 100;
                spillOverMarker = `
                    <div style="position: absolute; top: 80px; left: ${left}%; width: 2px; height: ${chartHeight - 80}px; border-left: 2px dashed #000; z-index: 1; pointer-events: none;"></div>
                    <div style="position: absolute; top: 82px; left: ${left}%; transform: translateX(-100%); background: #000; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75em; font-weight: 600; white-space: nowrap; z-index: 2; pointer-events: none;">Spill over ➜</div>
                `;
            }
        }

        return `
            <div class="gantt-wrapper" style="width: 100%; overflow-x: auto;">
                <div class="gantt-chart" style="min-width: ${chartWidth}px; height: ${chartHeight}px; position: relative; margin-left: ${labelWidth}px;">
                    ${weatherData ? this.renderWeatherInfoRow(dateHeaders, timeRange, weatherData, spillOverCutoffDate) : ''}
                    ${this.renderDateHeaders(dateHeaders, timeRange, chartWidth, spillOverCutoffDate)}
                    ${weatherBlocks}
                    ${breakdownMarker}
                    ${spillOverMarker}
                    ${windmillRows.map(row => this.renderWindmillLabel(row, rowHeight)).join('')}
                    ${taskRows.map(row => this.renderGanttRow(row, timeRange, rowHeight)).join('')}
                </div>
            </div>
        `;
    }

    renderWindmillLabel(row, rowHeight) {
        const { windmillId, top, taskCount } = row;
        return `
            <div class="gantt-windmill-label" 
                 style="position: absolute; 
                        top: ${top}px; 
                        left: -220px; 
                        width: 200px; 
                        height: ${rowHeight - 10}px;
                        padding: 5px;
                        font-size: 0.9em;
                        text-align: right;
                        border-right: 2px solid #ddd;
                        padding-right: 10px;
                        background: white;
                        z-index: 1;
                        border-top: 1px solid #e2e8f0;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;">
                <div style="font-weight: 600; color: #5AADE0;">${windmillId}</div>
                <div style="font-size: 0.8em; color: #888;">${taskCount} task${taskCount !== 1 ? 's' : ''}</div>
            </div>
        `;
    }

    generateDateHeaders(minTime, maxTime) {
        const headers = [];
        const current = new Date(minTime);
        current.setHours(0, 0, 0, 0);
        
        while (current <= maxTime) {
            headers.push(new Date(current));
            current.setDate(current.getDate() + 1);
        }
        
        return headers;
    }

    renderWeatherInfoRow(headers, timeRange, weatherData, spillOverCutoffDate = null) {
        if (!weatherData || !weatherData.forecast) {
            return '';
        }

        // Helper function to format date as YYYY-MM-DD in local timezone
        const formatLocalDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };

        // Parse spill over cutoff date (compare at day level)
        let cutoffDayStart = null;
        if (spillOverCutoffDate) {
            cutoffDayStart = new Date(spillOverCutoffDate);
            cutoffDayStart.setHours(0, 0, 0, 0);
        }

        // Create a lookup map for weather data by date
        const weatherByDate = {};
        weatherData.forecast.forEach(fc => {
            const dateKey = fc.date; // Format: "2024-01-15"
            weatherByDate[dateKey] = fc;
        });

        const headerHeight = 40;
        
        return `
            <div class="gantt-weather-info" style="height: ${headerHeight}px; position: relative; border-bottom: 1px solid #ddd; margin-bottom: 0;">
                ${headers.map((date) => {
                    const dateKey = formatLocalDate(date); // Format: "2024-01-15" in local timezone
                    const weather = weatherByDate[dateKey];
                    const left = ((date - timeRange.minTime) / timeRange.totalMs) * 100;
                    
                    // Check if date is on or after spill over cutoff day - show blank
                    if (cutoffDayStart && date >= cutoffDayStart) {
                        return `
                            <div class="gantt-weather-marker" style="position: absolute; left: ${left}%; border-left: 1px solid #ccc; height: 100%; padding-left: 5px;">
                            </div>
                        `;
                    }
                    
                    if (!weather) {
                        return `
                            <div class="gantt-weather-marker" style="position: absolute; left: ${left}%; border-left: 1px solid #ccc; height: 100%; padding-left: 5px;">
                                <div style="font-size: 0.75em; color: #999; margin-top: 3px;">
                                    No data
                                </div>
                            </div>
                        `;
                    }
                    
                    return `
                        <div class="gantt-weather-marker" style="position: absolute; left: ${left}%; border-left: 1px solid #ccc; height: 100%; padding-left: 5px;">
                            <div style="font-size: 0.75em; color: #666; margin-top: 3px; line-height: 1.2;">
                                <div>💨: <strong>${weather.wind_speed_ms.toFixed(1)}</strong> m/s</div>
                                <div>🌊: <strong>${weather.wave_height_m.toFixed(1)}</strong> m</div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    renderWeatherBlocks(weatherData, timeRange, chartHeight) {
        if (!weatherData || !weatherData.forecast) {
            return '';
        }

        const blocks = [];
        const dayMs = 24 * 60 * 60 * 1000; // milliseconds in a day

        weatherData.forecast.forEach(forecast => {
            if (!forecast.maintenance_possible) {
                // Parse date string "2024-01-15" as local date (not UTC)
                const [year, month, day] = forecast.date.split('-').map(Number);
                const dayStart = new Date(year, month - 1, day, 0, 0, 0, 0);
                const dayEnd = new Date(dayStart.getTime() + dayMs);

                // Only render if the day is within the time range
                if (dayEnd >= timeRange.minTime && dayStart <= timeRange.maxTime) {
                    const left = Math.max(0, ((dayStart - timeRange.minTime) / timeRange.totalMs) * 100);
                    const right = Math.min(100, ((dayEnd - timeRange.minTime) / timeRange.totalMs) * 100);
                    const width = right - left;

                    // Render a transparent red bar covering the entire chart height (below headers)
                    blocks.push(`
                        <div class="weather-block" 
                             style="position: absolute; 
                                    top: 80px; 
                                    left: ${left}%; 
                                    width: ${width}%; 
                                    height: ${chartHeight - 80}px;
                                    background: rgba(239, 68, 68, 0.15);
                                    border-left: 1px solid rgba(239, 68, 68, 0.3);
                                    border-right: 1px solid rgba(239, 68, 68, 0.3);
                                    pointer-events: none;
                                    z-index: 0;"
                             title="Maintenance impossible: ${forecast.wave_height_m}m waves, ${forecast.wind_speed_ms.toFixed(1)} m/s wind">
                        </div>
                    `);
                }
            }
        });

        return blocks.join('');
    }

    renderDateHeaders(headers, timeRange, chartWidth, spillOverCutoffDate = null) {
        const headerHeight = 40;
        const dayWidth = chartWidth / (timeRange.totalMs / (1000 * 60 * 60 * 24));
        
        // Parse spill over cutoff date (compare at day level)
        let cutoffDayStart = null;
        if (spillOverCutoffDate) {
            cutoffDayStart = new Date(spillOverCutoffDate);
            cutoffDayStart.setHours(0, 0, 0, 0);
        }
        
        return `
            <div class="gantt-header" style="height: ${headerHeight}px; position: relative; border-bottom: 2px solid #ddd; margin-bottom: 10px;">
                ${headers.map((date, index) => {
                    const left = ((date - timeRange.minTime) / timeRange.totalMs) * 100;
                    
                    // Check if date is on or after spill over cutoff day - show blank
                    if (cutoffDayStart && date >= cutoffDayStart) {
                        return `
                            <div class="gantt-date-marker" style="position: absolute; left: ${left}%; border-left: 1px solid #ccc; height: 100%; padding-left: 5px;">
                            </div>
                        `;
                    }
                    
                    return `
                        <div class="gantt-date-marker" style="position: absolute; left: ${left}%; border-left: 1px solid #ccc; height: 100%; padding-left: 5px;">
                            <div style="font-size: 0.85em; color: #666; margin-top: 5px;">
                                ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    calculateOvertimeSplit(startTime, finishTime) {
        // Overtime hours are between 18:00 (6 PM) and 06:00 (6 AM)
        // Returns ordered segments to render them in the correct position
        
        let regularMs = 0;
        let overtimeMs = 0;
        const segments = []; // Array of { type: 'regular'|'overtime', ms: number }
        
        const current = new Date(startTime);
        const end = new Date(finishTime);
        
        while (current < end) {
            const hour = current.getHours();
            const isOvertime = hour >= 18 || hour < 6;
            const segmentType = isOvertime ? 'overtime' : 'regular';
            
            // Calculate time until next hour or task end
            const nextHour = new Date(current);
            nextHour.setHours(current.getHours() + 1, 0, 0, 0);
            const segmentEnd = nextHour < end ? nextHour : end;
            const segmentMs = segmentEnd - current;
            
            if (isOvertime) {
                overtimeMs += segmentMs;
            } else {
                regularMs += segmentMs;
            }
            
            // Add to segments array, merging with previous if same type
            if (segments.length > 0 && segments[segments.length - 1].type === segmentType) {
                segments[segments.length - 1].ms += segmentMs;
            } else {
                segments.push({ type: segmentType, ms: segmentMs });
            }
            
            current.setTime(segmentEnd.getTime());
        }
        
        return {
            regularMs,
            overtimeMs,
            regularHours: regularMs / (1000 * 60 * 60),
            overtimeHours: overtimeMs / (1000 * 60 * 60),
            segments // Ordered array of segments
        };
    }

    renderGanttRow(row, timeRange, rowHeight) {
        const { task, top, left, width, overdueWidth, statusClass, isBreakdown, 
                overdueDays, penaltyCost, startTime, finishTime, latestFinish, taskType } = row;

        // Calculate overdue portion
        const overdueLeft = latestFinish && finishTime > latestFinish ? 
            ((latestFinish - timeRange.minTime) / timeRange.totalMs) * 100 : left + width;

        // Calculate overtime split with ordered segments
        const overtimeSplit = this.calculateOvertimeSplit(startTime, finishTime);
        const totalMs = finishTime - startTime;

        // Determine colors
        const baseColor = isBreakdown ? '#f56565' : statusClass === 'on-time' ? '#48bb78' : '#f56565';
        const overtimeColor = '#cc5500';
        
        // Check if this is a corrective task (render as circle)
        const isCorrective = taskType === 'corrective';
        const circleSize = rowHeight - 10; // Size for circular tasks
        
        // Format times for tooltip
        const startTimeStr = this.formatTime24h(startTime);
        const endTimeStr = this.formatTime24h(finishTime);
        const taskLabel = this.formatTaskLabel(task.id);
        const tooltipBase = `${taskLabel}: ${task.description || task.id} (${taskType}) - ${startTimeStr} to ${endTimeStr} - Regular: ${overtimeSplit.regularHours.toFixed(1)}h, Overtime: ${overtimeSplit.overtimeHours.toFixed(1)}h`;
        
        // Render task bar segments in correct order
        let taskBar = '';
        
        if (isCorrective) {
            // Render corrective tasks as circles
            // Position at the center of the task duration
            const centerLeft = left + (width / 2);
            const circleLeftPx = `calc(${centerLeft}% - ${circleSize / 2}px)`;
            
            taskBar = `
                <div class="gantt-task-bar-circle corrective-task ${statusClass} ${isBreakdown ? 'breakdown-task' : ''}" 
                     style="position: absolute; top: ${top}px; left: ${circleLeftPx}; width: ${circleSize}px; height: ${circleSize}px; 
                            background: ${baseColor}; border: 2px solid ${baseColor}; border-radius: 50%; 
                            display: flex; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.2s; z-index: 2;"
                     title="${tooltipBase}">
                    <span style="font-size: 0.7em; font-weight: 700; color: #000;">${taskLabel}</span>
                </div>`;
        } else {
            // Render preventive/other tasks as rectangles
            let currentLeft = left;
            const segments = overtimeSplit.segments;
            
            // Common base styles for task bar segments
            const baseStyle = `position: absolute; top: ${top}px; height: ${rowHeight - 10}px; display: flex; align-items: center; padding: 0 8px; cursor: pointer; transition: transform 0.2s; z-index: 2;`;
            
            // Find the largest segment to place the task ID
            let largestSegmentIndex = 0;
            let largestSegmentMs = 0;
            segments.forEach((seg, i) => {
                if (seg.ms > largestSegmentMs) {
                    largestSegmentMs = seg.ms;
                    largestSegmentIndex = i;
                }
            });
            
            segments.forEach((segment, index) => {
                const segmentWidth = totalMs > 0 ? (segment.ms / totalMs) * width : 0;
                if (segmentWidth <= 0) return;
                
                const isFirst = index === 0;
                const isLast = index === segments.length - 1;
                const isRegular = segment.type === 'regular';
                const color = isRegular ? baseColor : overtimeColor;
                // Show label in the largest segment
                const showId = index === largestSegmentIndex;
                
                // Determine border radius based on position
                let borderRadius = '4px';
                if (segments.length > 1) {
                    if (isFirst) borderRadius = '4px 0 0 4px';
                    else if (isLast) borderRadius = '0 4px 4px 0';
                    else borderRadius = '0';
                }
                
                // Determine border style
                const borderLeft = isFirst ? `2px solid ${color}` : 'none';
                const borderRight = isLast ? `2px solid ${color}` : 'none';
                
                taskBar += `
                    <div class="gantt-task-bar-${segment.type} ${statusClass} ${isBreakdown ? 'breakdown-task' : ''}" 
                         style="${baseStyle} left: ${currentLeft}%; width: ${segmentWidth}%; background: ${color}; border: 2px solid ${color}; border-radius: ${borderRadius}; border-left: ${borderLeft}; border-right: ${borderRight}; justify-content: center;"
                         title="${tooltipBase}">
                        ${showId ? `<span style="font-size: 0.8em; font-weight: 700; color: #000;">${taskLabel}</span>` : ''}
                    </div>`;
                
                currentLeft += segmentWidth;
            });
        }

        // Deadline marker (skip for preventive tasks)
        const deadlineMarker = (latestFinish && taskType !== 'preventive') ? `
            <div class="gantt-deadline-marker" 
                 style="position: absolute; 
                        top: ${top - 5}px; 
                        left: ${((latestFinish - timeRange.minTime) / timeRange.totalMs) * 100}%; 
                        width: 2px; 
                        height: ${rowHeight}px;
                        background: ${finishTime > latestFinish ? '#e53e3e' : '#48bb78'};
                        z-index: 1;"
                 title="Deadline: ${this.formatDateTime(latestFinish)}">
            </div>
        ` : '';

        return taskBar + deadlineMarker;
    }

    renderComparison(originalSchedule, optimizedSchedule, weatherData = null, breakdownData = null) {
        if (!originalSchedule || !optimizedSchedule) {
            this.container.innerHTML = '<div class="error">Comparison data not available</div>';
            return;
        }

        // Merge tasks for comparison - show both original and optimized
        const allTasks = [];
        
        // Add original tasks with prefix
        originalSchedule.tasks.forEach(task => {
            allTasks.push({
                ...task,
                id: `[Original] ${task.id}`,
                original_latest_finish: task.latest_finish
            });
        });

        // Add optimized tasks with prefix and preserve original deadline
        optimizedSchedule.tasks.forEach(optTask => {
            // Find original task to get original deadline
            const originalTask = originalSchedule.tasks.find(t => t.id === optTask.id);
            allTasks.push({
                ...optTask,
                id: `[Optimized] ${optTask.id}`,
                original_latest_finish: originalTask ? originalTask.latest_finish : optTask.latest_finish
            });
        });

        // Calculate combined time range
        const timeRange = this.calculateTimeRange(allTasks);

        const html = `
            <div class="gantt-container">
                ${this.renderGanttChart(allTasks, timeRange, weatherData, breakdownData)}
            </div>
        `;

        this.container.innerHTML = html;
    }

    formatDateTime(date) {
        if (!date) return 'N/A';
        const d = new Date(date);
        return d.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatTime24h(date) {
        if (!date) return 'N/A';
        const d = new Date(date);
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    formatTaskLabel(taskId) {
        // Convert TASK001 -> T1, TASK002 -> T2, etc.
        const match = taskId.match(/TASK0*(\d+)/);
        if (match) {
            return `T${parseInt(match[1])}`;
        }
        // For breakdown or other IDs, return as-is or format differently
        if (taskId.includes('BREAKDOWN')) {
            return 'BRK';
        }
        return taskId;
    }

    showLoading(message = 'Loading...') {
        this.container.innerHTML = `<div class="loading">${message}</div>`;
    }

    showError(message) {
        this.container.innerHTML = `<div class="error">${message}</div>`;
    }
}

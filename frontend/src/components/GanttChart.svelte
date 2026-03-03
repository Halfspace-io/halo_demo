<script>
  import GanttHeader from './GanttHeader.svelte';
  import GanttWeatherRow from './GanttWeatherRow.svelte';
  import GanttWindmillRow from './GanttWindmillRow.svelte';
  import GanttMarker from './GanttMarker.svelte';
  import { formatLocalDate } from '../lib/utils.js';

  let { schedule, weatherData = null, breakdownData = null, timeRange = null } = $props();

  const DAY_WIDTH = 100;
  const ROW_HEIGHT = 50;
  const LABEL_WIDTH = 220;

  let computedTimeRange = $derived.by(() => {
    if (timeRange) return timeRange;
    if (!schedule?.tasks?.length) return null;
    const minTime = new Date(schedule.planning_horizon_start);
    const maxTime = new Date(schedule.planning_horizon_end);
    return { minTime, maxTime, totalMs: maxTime - minTime };
  });

  // Trim timeline: find the effective end date (latest of: last task end, spill-over cutoff, breakdown end)
  let effectiveTimeRange = $derived.by(() => {
    if (!computedTimeRange || !schedule?.tasks?.length) return computedTimeRange;
    const minTime = computedTimeRange.minTime;
    let maxDate = new Date(minTime);

    // Check all task end times
    for (const task of schedule.tasks) {
      const start = new Date(task.start_time);
      const end = new Date(start.getTime() + (task.duration_hours || 0) * 3600000);
      if (end > maxDate) maxDate = end;
    }

    // Check spill-over cutoff
    if (schedule.spill_over_cutoff_date) {
      const cutoff = new Date(schedule.spill_over_cutoff_date);
      if (cutoff > maxDate) maxDate = cutoff;
    }

    // Add 1 day padding after the latest event
    const padded = new Date(maxDate);
    padded.setDate(padded.getDate() + 1);
    padded.setHours(0, 0, 0, 0);

    // Don't extend beyond the original range
    const effectiveMax = padded < computedTimeRange.maxTime ? padded : computedTimeRange.maxTime;

    return { minTime, maxTime: effectiveMax, totalMs: effectiveMax - minTime };
  });

  let windmillGroups = $derived.by(() => {
    if (!schedule?.tasks) return [];
    const map = {};
    for (const task of schedule.tasks) {
      const wm = task.windmill_id || 'Unknown';
      if (!map[wm]) map[wm] = [];
      map[wm].push(task);
    }
    return Object.keys(map)
      .sort((a, b) => {
        const na = parseInt(a.replace(/\D/g, '')) || 0;
        const nb = parseInt(b.replace(/\D/g, '')) || 0;
        return na - nb;
      })
      .map((id) => ({ id, tasks: map[id] }));
  });

  let dateHeaders = $derived.by(() => {
    if (!effectiveTimeRange) return [];
    const headers = [];
    const current = new Date(effectiveTimeRange.minTime);
    current.setHours(0, 0, 0, 0);
    while (current <= effectiveTimeRange.maxTime) {
      headers.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    return headers;
  });

  let chartHeight = $derived(windmillGroups.length * ROW_HEIGHT + 100);
  let totalDays = $derived(effectiveTimeRange ? Math.ceil(effectiveTimeRange.totalMs / (1000 * 60 * 60 * 24)) : 0);
  let chartWidth = $derived(Math.max(800, totalDays * DAY_WIDTH));

  let weatherBlocks = $derived.by(() => {
    if (!weatherData?.forecast || !effectiveTimeRange) return [];
    const dayMs = 24 * 60 * 60 * 1000;
    const blocks = [];
    for (const fc of weatherData.forecast) {
      if (!fc.maintenance_possible) {
        const [y, m, d] = fc.date.split('-').map(Number);
        const dayStart = new Date(y, m - 1, d, 0, 0, 0, 0);
        const dayEnd = new Date(dayStart.getTime() + dayMs);
        if (dayEnd >= effectiveTimeRange.minTime && dayStart <= effectiveTimeRange.maxTime) {
          const left = Math.max(0, ((dayStart - effectiveTimeRange.minTime) / effectiveTimeRange.totalMs) * 100);
          const right = Math.min(100, ((dayEnd - effectiveTimeRange.minTime) / effectiveTimeRange.totalMs) * 100);
          blocks.push({ left, width: right - left, title: `Maintenance impossible: ${fc.wave_height_m}m waves, ${fc.wind_speed_ms.toFixed(1)} m/s wind` });
        }
      }
    }
    return blocks;
  });

  let breakdownMarkerData = $derived.by(() => {
    if (!breakdownData || !effectiveTimeRange) return null;
    const bd = breakdownData.breakdown_event || breakdownData.breakdowns?.[0];
    if (!bd?.breakdown_time) return null;
    const t = new Date(bd.breakdown_time);
    if (t < effectiveTimeRange.minTime || t > effectiveTimeRange.maxTime) return null;
    return { left: ((t - effectiveTimeRange.minTime) / effectiveTimeRange.totalMs) * 100 };
  });

  let spillOverMarkerData = $derived.by(() => {
    if (!schedule?.spill_over_cutoff_date || !effectiveTimeRange) return null;
    const t = new Date(schedule.spill_over_cutoff_date);
    if (t < effectiveTimeRange.minTime || t > effectiveTimeRange.maxTime) return null;
    return { left: ((t - effectiveTimeRange.minTime) / effectiveTimeRange.totalMs) * 100 };
  });
</script>

{#if effectiveTimeRange}
  <div class="w-full overflow-x-auto bg-(--color-surface) border border-(--color-border-faint) rounded-lg p-3">
    <div class="relative bg-white border border-(--color-border-faint) rounded" style:min-width="{chartWidth}px" style:height="{chartHeight}px" style:margin-left="{LABEL_WIDTH}px">
      {#if weatherData}
        <GanttWeatherRow
          headers={dateHeaders}
          timeRange={effectiveTimeRange}
          {weatherData}
          spillOverCutoffDate={schedule?.spill_over_cutoff_date}
        />
      {/if}

      <GanttHeader
        headers={dateHeaders}
        timeRange={effectiveTimeRange}
        spillOverCutoffDate={schedule?.spill_over_cutoff_date}
      />

      {#each weatherBlocks as block}
        <div
          class="absolute pointer-events-none z-0 rounded-sm"
          style:top="80px"
          style:left="{block.left}%"
          style:width="{block.width}%"
          style:height="{chartHeight - 80}px"
          style:background="rgba(220, 104, 104, 0.06)"
          style:border-left="1px solid rgba(220, 104, 104, 0.15)"
          style:border-right="1px solid rgba(220, 104, 104, 0.15)"
          title={block.title}
        ></div>
      {/each}

      {#if breakdownMarkerData}
        <GanttMarker
          left={breakdownMarkerData.left}
          height={chartHeight - 80}
          color="#dc6868"
          label="Breakdown reported"
        />
      {/if}

      {#if spillOverMarkerData}
        <GanttMarker
          left={spillOverMarkerData.left}
          height={chartHeight - 80}
          color="#444"
          label="Spill over"
          labelAlign="right"
        />
      {/if}

      {#each windmillGroups as group, i}
        <GanttWindmillRow
          windmillId={group.id}
          tasks={group.tasks}
          timeRange={effectiveTimeRange}
          rowTop={i * ROW_HEIGHT + 80}
          rowHeight={ROW_HEIGHT}
        />
      {/each}
    </div>
  </div>
{:else}
  <div class="py-10 text-center text-(--color-text-muted) text-sm">No schedule data available</div>
{/if}

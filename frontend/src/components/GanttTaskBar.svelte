<script>
  import { calculateOvertimeSplit, formatTaskLabel, formatTime24h } from '../lib/utils.js';

  let { task, timeRange, rowTop, rowHeight = 50 } = $props();

  let startTime = $derived(new Date(task.start_time));
  let finishTime = $derived(new Date(startTime.getTime() + (task.duration_hours || 0) * 3600000));
  let latestFinish = $derived.by(() => {
    if (task.original_latest_finish) return new Date(task.original_latest_finish);
    if (task.latest_finish) return new Date(task.latest_finish);
    return null;
  });

  let left = $derived(((startTime - timeRange.minTime) / timeRange.totalMs) * 100);
  let width = $derived(((finishTime - startTime) / timeRange.totalMs) * 100);

  let isBreakdown = $derived(task.is_breakdown || task.task_type === 'breakdown_repair');
  let isCorrective = $derived(task.task_type === 'corrective');
  let isOverdue = $derived(latestFinish && finishTime > latestFinish);

  // Softer colors
  let baseColor = $derived(isBreakdown ? '#dc6868' : isOverdue ? '#dc6868' : '#4ead6b');
  let baseBorder = $derived(isBreakdown ? '#c44e4e' : isOverdue ? '#c44e4e' : '#3a9457');
  let overtimeColor = '#d97a2e';
  let overtimeBorder = '#b86520';

  let overtimeSplit = $derived(calculateOvertimeSplit(startTime, finishTime));
  let totalMs = $derived(finishTime - startTime);

  // Use proper description as label, fall back to short ID
  let taskLabel = $derived(task.description || formatTaskLabel(task.id));
  let shortLabel = $derived(formatTaskLabel(task.id));

  let tooltip = $derived.by(() => {
    const st = formatTime24h(startTime);
    const et = formatTime24h(finishTime);
    return `${shortLabel}: ${task.description || task.id} (${task.task_type}) - ${st} to ${et} - Regular: ${overtimeSplit.regularHours.toFixed(1)}h, Overtime: ${overtimeSplit.overtimeHours.toFixed(1)}h`;
  });

  let largestSegIndex = $derived.by(() => {
    let idx = 0, max = 0;
    overtimeSplit.segments.forEach((s, i) => {
      if (s.ms > max) { max = s.ms; idx = i; }
    });
    return idx;
  });

  let deadlineLeft = $derived.by(() => {
    if (!latestFinish) return null;
    return ((latestFinish - timeRange.minTime) / timeRange.totalMs) * 100;
  });
  let deadlineColor = $derived(isOverdue ? '#dc6868' : '#4ead6b');
</script>

{#if isCorrective}
  {@const circleSize = rowHeight - 10}
  {@const centerLeft = left + width / 2}
  <div
    class="group absolute rounded-full border-2 flex items-center justify-center cursor-pointer transition-all duration-150 z-2 hover:scale-110 hover:z-5"
    style:top="{rowTop}px"
    style:left="calc({centerLeft}% - {circleSize / 2}px)"
    style:width="{circleSize}px"
    style:height="{circleSize}px"
    style:background={baseColor}
    style:border-color={baseBorder}
    style:box-shadow="0 2px 6px rgba(0,0,0,0.15)"
    title={tooltip}
  >
    <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1 rounded bg-gray-800 text-white text-[10px] font-semibold whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-md">{taskLabel}</span>
  </div>
{:else}
  {@const segments = overtimeSplit.segments}
  {#each segments as segment, i}
    {@const segWidth = totalMs > 0 ? (segment.ms / totalMs) * width : 0}
    {@const segLeft = (() => {
      let l = left;
      for (let j = 0; j < i; j++) l += totalMs > 0 ? (segments[j].ms / totalMs) * width : 0;
      return l;
    })()}
    {@const color = segment.type === 'regular' ? baseColor : overtimeColor}
    {@const border = segment.type === 'regular' ? baseBorder : overtimeBorder}
    {@const isFirst = i === 0}
    {@const isLast = i === segments.length - 1}
    {@const radius = segments.length === 1 ? '5px' : isFirst ? '5px 0 0 5px' : isLast ? '0 5px 5px 0' : '0'}
    {#if segWidth > 0}
      <div
        class="group absolute border flex items-center justify-center cursor-pointer transition-all duration-150 z-2 hover:-translate-y-0.5 hover:z-5"
        style:top="{rowTop}px"
        style:left="{segLeft}%"
        style:width="{segWidth}%"
        style:height="{rowHeight - 10}px"
        style:background={color}
        style:border-color={border}
        style:border-radius={radius}
        style:box-shadow="0 2px 6px rgba(0,0,0,0.12)"
        title={tooltip}
      >
        {#if i === largestSegIndex}
          <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1 rounded bg-gray-800 text-white text-[10px] font-semibold whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-md">{taskLabel}</span>
        {/if}
      </div>
    {/if}
  {/each}
{/if}

{#if deadlineLeft !== null && task.task_type !== 'preventive'}
  <div
    class="absolute w-0.5 z-1"
    style:top="{rowTop - 5}px"
    style:left="{deadlineLeft}%"
    style:height="{rowHeight}px"
    style:background={deadlineColor}
    title="Deadline: {latestFinish ? latestFinish.toLocaleString() : ''}"
  ></div>
{/if}

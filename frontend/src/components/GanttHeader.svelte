<script>
  import { formatLocalDate } from '../lib/utils.js';
  let { headers, timeRange, spillOverCutoffDate = null } = $props();

  let cutoffDayStart = $derived.by(() => {
    if (!spillOverCutoffDate) return null;
    const d = new Date(spillOverCutoffDate);
    d.setHours(0, 0, 0, 0);
    return d;
  });

  function leftPct(date) {
    return ((date - timeRange.minTime) / timeRange.totalMs) * 100;
  }

  function isPastCutoff(date) {
    return cutoffDayStart && date >= cutoffDayStart;
  }
</script>

<div class="h-10 relative border-b-2 border-(--color-border-subtle) mb-2.5">
  {#each headers as date}
    {@const left = leftPct(date)}
    <div class="absolute h-full border-l border-(--color-border-faint) pl-1.5" style:left="{left}%">
      {#if !isPastCutoff(date)}
        <span class="text-xs text-(--color-text-muted) mt-1 inline-block">
          {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </span>
      {/if}
    </div>
  {/each}
</div>

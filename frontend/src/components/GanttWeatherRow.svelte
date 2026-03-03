<script>
  import { formatLocalDate } from '../lib/utils.js';
  let { headers, timeRange, weatherData, spillOverCutoffDate = null } = $props();

  let weatherByDate = $derived.by(() => {
    const map = {};
    if (weatherData?.forecast) {
      for (const fc of weatherData.forecast) {
        map[fc.date] = fc;
      }
    }
    return map;
  });

  let cutoffDayStart = $derived.by(() => {
    if (!spillOverCutoffDate) return null;
    const d = new Date(spillOverCutoffDate);
    d.setHours(0, 0, 0, 0);
    return d;
  });

  function leftPct(date) {
    return ((date - timeRange.minTime) / timeRange.totalMs) * 100;
  }
</script>

<div class="h-10 relative border-b border-(--color-border-subtle)">
  {#each headers as date}
    {@const left = leftPct(date)}
    {@const dateKey = formatLocalDate(date)}
    {@const weather = weatherByDate[dateKey]}
    {@const pastCutoff = cutoffDayStart && date >= cutoffDayStart}
    <div class="absolute h-full border-l border-(--color-border-faint) pl-1.5" style:left="{left}%">
      {#if !pastCutoff}
        {#if weather}
          <div class="text-[11px] text-(--color-text-muted) mt-0.5 leading-tight">
            <div>Wind: <strong class="text-(--color-text-primary)">{weather.wind_speed_ms.toFixed(1)}</strong> m/s</div>
            <div>Wave: <strong class="text-(--color-text-primary)">{weather.wave_height_m.toFixed(1)}</strong> m</div>
          </div>
        {:else}
          <div class="text-[11px] text-(--color-text-muted)/50 mt-0.5">No data</div>
        {/if}
      {/if}
    </div>
  {/each}
</div>

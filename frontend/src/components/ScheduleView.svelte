<script>
  import { store } from '../lib/state.svelte.js';
  import GanttChart from './GanttChart.svelte';

  let timeRange = $derived.by(() => {
    if (!store.originalSchedule) return null;
    const minTime = new Date(store.originalSchedule.planning_horizon_start);
    const maxTime = new Date(store.originalSchedule.planning_horizon_end);
    return { minTime, maxTime, totalMs: maxTime - minTime };
  });

  let breakdownDataForView = $derived.by(() => {
    if (!store.activeBreakdown) return null;
    return { breakdowns: [store.activeBreakdown], breakdown_event: store.activeBreakdown };
  });

  let activeSchedule = $derived.by(() => {
    if (store.currentView === 'optimized' && store.optimizedSchedule) return store.optimizedSchedule;
    return store.originalSchedule;
  });

  function setView(view) {
    store.currentView = view;
  }
</script>

<section class="bg-white border border-(--color-border-faint) rounded-xl shadow-(--shadow-card) p-5">
  <div class="flex justify-between items-center flex-wrap gap-3 mb-5">
    <h2 class="text-lg font-semibold text-(--color-text-primary)">Schedule Timeline</h2>
    <div class="flex gap-4 flex-wrap text-xs text-(--color-text-muted)">
      <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-(--color-preventive)"></span> Preventive</span>
      <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-(--color-preventive)"></span> Corrective</span>
      <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-(--color-overtime)"></span> Overtime</span>
      <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-(--color-breakdown)"></span> Breakdown</span>
    </div>
    <div class="flex gap-1.5">
      <button
        class="px-4 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer {store.currentView === 'original' ? 'bg-(--color-orsted) text-white border-(--color-orsted)' : 'bg-(--color-surface) text-(--color-text-muted) border-(--color-border-subtle) hover:bg-(--color-surface-alt)'}"
        onclick={() => setView('original')}
      >
        Original
      </button>
      <button
        class="px-4 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed {store.currentView === 'optimized' ? 'bg-(--color-orsted) text-white border-(--color-orsted)' : 'bg-(--color-surface) text-(--color-text-muted) border-(--color-border-subtle) hover:bg-(--color-surface-alt)'}"
        disabled={!store.optimizedSchedule}
        onclick={() => setView('optimized')}
      >
        Optimized
      </button>
    </div>
  </div>

  {#if store.loading}
    <div class="py-12 text-center text-(--color-text-muted) text-sm">Optimizing schedule...</div>
  {:else if activeSchedule}
    <GanttChart
      schedule={activeSchedule}
      weatherData={store.weatherData}
      breakdownData={breakdownDataForView}
      {timeRange}
    />
  {:else}
    <div class="py-12 text-center text-(--color-text-muted) text-sm">No schedule data loaded</div>
  {/if}
</section>

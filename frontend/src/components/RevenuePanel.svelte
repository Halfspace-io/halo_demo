<script>
  import { store } from '../lib/state.svelte.js';

  let overdueTasks = $derived.by(() => {
    if (store.currentView === 'optimized' && store.optimizedSchedule) {
      return store.optimizedSchedule.tasks.filter((t) => t.overdue_info).length;
    }
    if (store.originalObjectiveValues?.overdue_tasks) {
      return Object.keys(store.originalObjectiveValues.overdue_tasks).length;
    }
    return 0;
  });

  let totalPenalties = $derived.by(() => {
    if (store.currentView === 'optimized' && store.optimizedSchedule) {
      return store.optimizedSchedule.tasks.reduce(
        (sum, t) => sum + (t.overdue_info?.penalty_cost || 0),
        0
      );
    }
    return store.originalObjectiveValues?.total_penalties || 0;
  });

  let objectiveValue = $derived.by(() => {
    if (store.currentView === 'optimized' && store.optimizedSchedule) {
      return store.optimizedSchedule.objective_value;
    }
    return store.originalObjectiveValues?.objective_value ?? null;
  });

  let downtimeBreakdown = $derived.by(() => {
    if (store.currentView === 'optimized' && store.optimizedSchedule) {
      return store.optimizedSchedule.downtime_cost_for_breakdown || 0;
    }
    return store.originalObjectiveValues?.downtime_cost_for_breakdown || 0;
  });

  let downtimeScheduled = $derived.by(() => {
    if (store.currentView === 'optimized' && store.optimizedSchedule) {
      return store.optimizedSchedule.downtime_cost_for_scheduled_tasks || 0;
    }
    return store.originalObjectiveValues?.downtime_cost_for_scheduled_tasks || 0;
  });

  let overtime = $derived.by(() => {
    if (store.currentView === 'optimized' && store.optimizedSchedule) {
      return store.optimizedSchedule.cost_of_overtime || 0;
    }
    return store.originalObjectiveValues?.cost_of_overtime?.total || 0;
  });

  let spillOver = $derived.by(() => {
    if (store.currentView === 'optimized' && store.optimizedSchedule) {
      return store.optimizedSchedule.cost_of_spill_over || 0;
    }
    return store.originalObjectiveValues?.cost_of_spill_over?.total || 0;
  });

  let label = $derived(store.currentView === 'optimized' && store.optimizedSchedule ? 'Optimized' : 'Original');
  let isOptimized = $derived(store.currentView === 'optimized' && store.optimizedSchedule && store.originalObjectiveValues);

  // Original values for delta calculation
  let origObjective = $derived(store.originalObjectiveValues?.objective_value ?? null);
  let origPenalties = $derived(store.originalObjectiveValues?.total_penalties || 0);
  let origDowntimeBreakdown = $derived(store.originalObjectiveValues?.downtime_cost_for_breakdown || 0);
  let origDowntimeScheduled = $derived(store.originalObjectiveValues?.downtime_cost_for_scheduled_tasks || 0);
  let origOvertime = $derived(store.originalObjectiveValues?.cost_of_overtime?.total || 0);
  let origSpillOver = $derived(store.originalObjectiveValues?.cost_of_spill_over?.total || 0);
  let origOverdueTasks = $derived.by(() => {
    if (store.originalObjectiveValues?.overdue_tasks) {
      return Object.keys(store.originalObjectiveValues.overdue_tasks).length;
    }
    return 0;
  });

  function fmt(val) {
    if (typeof val !== 'number') return 'N/A';
    return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function deltaPct(current, original) {
    if (typeof current !== 'number' || typeof original !== 'number' || original === 0) return null;
    return ((current - original) / Math.abs(original)) * 100;
  }

  function fmtDelta(pct) {
    if (pct === null) return '';
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(1)}%`;
  }

  // For costs, negative delta = good (cost went down). For objective, positive delta = good.
  function deltaClass(pct, higherIsBetter = false) {
    if (pct === null) return '';
    if (higherIsBetter) return pct >= 0 ? 'text-emerald-600' : 'text-red-500';
    return pct <= 0 ? 'text-emerald-600' : 'text-red-500';
  }

  let hasData = $derived(
    store.originalObjectiveValues !== null ||
    (store.currentView === 'optimized' && store.optimizedSchedule !== null)
  );
</script>

<section class="bg-white border border-(--color-border-faint) rounded-xl shadow-(--shadow-card) px-5 py-4">
  <div class="flex items-center gap-3 mb-4">
    <h3 class="text-base font-semibold text-(--color-text-primary)">Revenue Impact</h3>
    <span class="text-xs font-semibold text-(--color-orsted) bg-(--color-orsted-light) px-2.5 py-0.5 rounded-full">{label}</span>
  </div>

  {#if !hasData}
    <p class="text-sm text-(--color-text-muted)">Loading...</p>
  {:else}
    <div class="grid grid-cols-[repeat(auto-fit,minmax(155px,1fr))] gap-3">
      <div class="px-4 py-3 bg-(--color-orsted-50) rounded-lg border border-(--color-orsted)/20">
        <span class="block text-[11px] font-semibold text-(--color-text-muted) uppercase tracking-wide mb-1">Objective Value</span>
        <div class="flex items-baseline gap-2">
          <span class="text-base font-bold text-(--color-orsted) tabular-nums">{fmt(objectiveValue)}</span>
          {#if isOptimized}
            {@const d = deltaPct(objectiveValue, origObjective)}
            {#if d !== null}<span class="text-xs font-semibold {deltaClass(d, true)}">{fmtDelta(d)}</span>{/if}
          {/if}
        </div>
      </div>
      <div class="px-4 py-3 bg-(--color-surface) rounded-lg border border-(--color-border-faint)">
        <span class="block text-[11px] font-semibold text-(--color-text-muted) uppercase tracking-wide mb-1">Overdue Tasks</span>
        <div class="flex items-baseline gap-2">
          <span class="text-base font-bold text-(--color-text-primary) tabular-nums">{overdueTasks}</span>
          {#if isOptimized && origOverdueTasks !== overdueTasks}
            <span class="text-xs font-semibold {overdueTasks <= origOverdueTasks ? 'text-emerald-600' : 'text-red-500'}">{overdueTasks < origOverdueTasks ? '' : '+'}{overdueTasks - origOverdueTasks}</span>
          {/if}
        </div>
      </div>
      <div class="px-4 py-3 bg-(--color-surface) rounded-lg border border-(--color-border-faint)">
        <span class="block text-[11px] font-semibold text-(--color-text-muted) uppercase tracking-wide mb-1">Total Penalties</span>
        <div class="flex items-baseline gap-2">
          <span class="text-sm font-semibold text-(--color-text-primary) tabular-nums">{fmt(totalPenalties)} EUR</span>
          {#if isOptimized}
            {@const d = deltaPct(totalPenalties, origPenalties)}
            {#if d !== null}<span class="text-xs font-semibold {deltaClass(d)}">{fmtDelta(d)}</span>{/if}
          {/if}
        </div>
      </div>
      <div class="px-4 py-3 bg-(--color-surface) rounded-lg border border-(--color-border-faint)">
        <span class="block text-[11px] font-semibold text-(--color-text-muted) uppercase tracking-wide mb-1">Downtime (Breakdown)</span>
        <div class="flex items-baseline gap-2">
          <span class="text-sm font-semibold text-(--color-text-primary) tabular-nums">{fmt(downtimeBreakdown)} EUR</span>
          {#if isOptimized}
            {@const d = deltaPct(downtimeBreakdown, origDowntimeBreakdown)}
            {#if d !== null}<span class="text-xs font-semibold {deltaClass(d)}">{fmtDelta(d)}</span>{/if}
          {/if}
        </div>
      </div>
      <div class="px-4 py-3 bg-(--color-surface) rounded-lg border border-(--color-border-faint)">
        <span class="block text-[11px] font-semibold text-(--color-text-muted) uppercase tracking-wide mb-1">Downtime (Scheduled)</span>
        <div class="flex items-baseline gap-2">
          <span class="text-sm font-semibold text-(--color-text-primary) tabular-nums">{fmt(downtimeScheduled)} EUR</span>
          {#if isOptimized}
            {@const d = deltaPct(downtimeScheduled, origDowntimeScheduled)}
            {#if d !== null}<span class="text-xs font-semibold {deltaClass(d)}">{fmtDelta(d)}</span>{/if}
          {/if}
        </div>
      </div>
      <div class="px-4 py-3 bg-(--color-surface) rounded-lg border border-(--color-border-faint)">
        <span class="block text-[11px] font-semibold text-(--color-text-muted) uppercase tracking-wide mb-1">Overtime Cost</span>
        <div class="flex items-baseline gap-2">
          <span class="text-sm font-semibold text-(--color-text-primary) tabular-nums">{fmt(overtime)} EUR</span>
          {#if isOptimized}
            {@const d = deltaPct(overtime, origOvertime)}
            {#if d !== null}<span class="text-xs font-semibold {deltaClass(d)}">{fmtDelta(d)}</span>{/if}
          {/if}
        </div>
      </div>
      <div class="px-4 py-3 bg-(--color-surface) rounded-lg border border-(--color-border-faint)">
        <span class="block text-[11px] font-semibold text-(--color-text-muted) uppercase tracking-wide mb-1">Spill-over Cost</span>
        <div class="flex items-baseline gap-2">
          <span class="text-sm font-semibold text-(--color-text-primary) tabular-nums">{fmt(spillOver)} EUR</span>
          {#if isOptimized}
            {@const d = deltaPct(spillOver, origSpillOver)}
            {#if d !== null}<span class="text-xs font-semibold {deltaClass(d)}">{fmtDelta(d)}</span>{/if}
          {/if}
        </div>
      </div>
    </div>
  {/if}
</section>

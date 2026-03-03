<script>
  import { onMount } from 'svelte';
  import { store } from './lib/state.svelte.js';
  import * as api from './lib/api.js';
  import Sidebar from './components/Sidebar.svelte';
  import ScheduleView from './components/ScheduleView.svelte';
  import RevenuePanel from './components/RevenuePanel.svelte';

  onMount(() => {
    loadInitialData();
  });

  async function loadInitialData() {
    try {
      store.loading = true;
      store.originalSchedule = await api.getSchedule();
      store.weatherData = await api.getWeather();
      store.breakdownInfo = await api.getBreakdown();
      store.currentView = 'original';
      store.activeBreakdown = null;
      await loadOriginalObjectiveValues();
    } catch (e) {
      store.error = e.message;
    } finally {
      store.loading = false;
    }
  }

  async function loadOriginalObjectiveValues() {
    try {
      const c = store.config;
      store.originalObjectiveValues = await api.calculateObjective(
        c.overduePenaltyPerDay,
        c.overtimeCostPerHour,
        c.spillOverPenaltyRoutine,
        c.spillOverPenaltyRepairs
      );
    } catch (e) {
      console.error('Error calculating objective:', e);
    }
  }

  async function handleOptimize() {
    const breakdownFile = store.activeBreakdown?.file ?? null;
    await doReplan(breakdownFile);
  }

  async function handleReplanWithBreakdown(breakdownFile) {
    await doReplan(breakdownFile);
  }

  async function doReplan(breakdownFile) {
    try {
      store.loading = true;
      store.error = null;
      const c = store.config;

      store.optimizedSchedule = await api.replan(
        c.overduePenaltyPerDay,
        c.overtimeCostPerHour,
        c.spillOverPenaltyRoutine,
        c.spillOverPenaltyRepairs,
        breakdownFile
      );

      store.currentView = 'optimized';

      // Start explanation generation in background
      store.currentExplanation = { loading: true };
      store.loading = false;
      generateExplanation();
    } catch (e) {
      store.error = e.message;
      store.loading = false;
    }
  }

  async function generateExplanation() {
    try {
      const c = store.config;
      const result = await api.explainOptimization(
        store.originalSchedule,
        store.optimizedSchedule,
        store.activeBreakdown,
        store.weatherData,
        {
          overdue_penalty_per_day: c.overduePenaltyPerDay,
          overtime_cost_per_hour: c.overtimeCostPerHour,
          spill_over_penalty_routine: c.spillOverPenaltyRoutine,
          spill_over_penalty_repairs: c.spillOverPenaltyRepairs,
        }
      );
      store.currentExplanation = { text: result.explanation };
    } catch (e) {
      store.currentExplanation = { error: e.message };
    }
  }
</script>

<div class="flex min-h-screen">
  <Sidebar onOptimize={handleOptimize} onReplanWithBreakdown={handleReplanWithBreakdown} />

  <main class="flex-1 min-w-0 p-6 overflow-y-auto bg-(--color-surface) flex flex-col gap-5">
    <header>
      <h1 class="text-2xl font-bold text-(--color-text-primary) tracking-tight">Offshore Wind Re-planner</h1>
      <p class="text-sm text-(--color-text-muted) mt-0.5">Optimize maintenance schedules when breakdowns occur</p>
    </header>

    {#if store.error}
      <div class="px-4 py-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
        {store.error}
      </div>
    {/if}

    <RevenuePanel />
    <ScheduleView />
  </main>
</div>

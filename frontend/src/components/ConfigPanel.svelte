<script>
  import { store } from '../lib/state.svelte.js';

  let { onOptimize } = $props();
  let open = $state(true);
</script>

<section class="bg-white border border-(--color-border-subtle) rounded-lg p-4 shadow-(--shadow-sm)">
  <button class="flex items-center justify-between w-full cursor-pointer" onclick={() => open = !open}>
    <h3 class="text-sm font-semibold text-(--color-text-primary)">Configuration</h3>
    <svg class="w-4 h-4 text-(--color-text-muted) transition-transform duration-200 {open ? 'rotate-0' : '-rotate-90'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <path d="M19 9l-7 7-7-7" />
    </svg>
  </button>

  {#if open}
    <div class="mt-4 flex flex-col gap-3 animate-[slideDown_0.2s_ease]">
      <div>
        <label for="penalty" class="block text-xs font-medium text-(--color-text-muted) mb-1">Overdue Penalty / Day</label>
        <div class="flex items-center gap-2">
          <input id="penalty" type="number" step="100" bind:value={store.config.overduePenaltyPerDay}
            class="flex-1 px-3 py-2 border border-(--color-border-subtle) rounded-md text-sm bg-(--color-surface) text-(--color-text-primary) focus:outline-none focus:border-(--color-orsted) focus:ring-2 focus:ring-(--color-orsted)/10 transition-colors" />
          <span class="text-xs text-(--color-text-muted)">EUR</span>
        </div>
      </div>

      <div>
        <label for="overtime" class="block text-xs font-medium text-(--color-text-muted) mb-1">Overtime Cost / Hour</label>
        <div class="flex items-center gap-2">
          <input id="overtime" type="number" step="50" bind:value={store.config.overtimeCostPerHour}
            class="flex-1 px-3 py-2 border border-(--color-border-subtle) rounded-md text-sm bg-(--color-surface) text-(--color-text-primary) focus:outline-none focus:border-(--color-orsted) focus:ring-2 focus:ring-(--color-orsted)/10 transition-colors" />
          <span class="text-xs text-(--color-text-muted)">EUR</span>
        </div>
      </div>

      <div>
        <label for="spill-prev" class="block text-xs font-medium text-(--color-text-muted) mb-1">Spill-over Preventive</label>
        <div class="flex items-center gap-2">
          <input id="spill-prev" type="number" step="500" bind:value={store.config.spillOverPenaltyRoutine}
            class="flex-1 px-3 py-2 border border-(--color-border-subtle) rounded-md text-sm bg-(--color-surface) text-(--color-text-primary) focus:outline-none focus:border-(--color-orsted) focus:ring-2 focus:ring-(--color-orsted)/10 transition-colors" />
          <span class="text-xs text-(--color-text-muted)">EUR</span>
        </div>
      </div>

      <div>
        <label for="spill-corr" class="block text-xs font-medium text-(--color-text-muted) mb-1">Spill-over Corrective</label>
        <div class="flex items-center gap-2">
          <input id="spill-corr" type="number" step="500" bind:value={store.config.spillOverPenaltyRepairs}
            class="flex-1 px-3 py-2 border border-(--color-border-subtle) rounded-md text-sm bg-(--color-surface) text-(--color-text-primary) focus:outline-none focus:border-(--color-orsted) focus:ring-2 focus:ring-(--color-orsted)/10 transition-colors" />
          <span class="text-xs text-(--color-text-muted)">EUR</span>
        </div>
      </div>

      <button
        class="w-full mt-1 py-2.5 bg-(--color-orsted) text-white rounded-lg text-sm font-semibold cursor-pointer transition-colors hover:bg-(--color-orsted-dark) disabled:opacity-50 disabled:cursor-not-allowed"
        onclick={onOptimize}
        disabled={store.loading}
      >
        {store.loading ? 'Optimizing...' : 'Optimize Schedule'}
      </button>
    </div>
  {/if}
</section>

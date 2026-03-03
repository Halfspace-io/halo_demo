<script>
  import { store } from '../lib/state.svelte.js';

  let { onReplanWithBreakdown } = $props();
  let open = $state(true);

  let breakdowns = $derived.by(() => {
    if (!store.breakdownInfo?.breakdowns) return [];
    const files = ['breakdown.json', 'breakdown2.json'];
    return store.breakdownInfo.breakdowns.map((bd, i) => ({
      ...bd,
      file: files[i] || `breakdown${i + 1}.json`,
    }));
  });

  function formatTime(timeString) {
    const d = new Date(timeString);
    return d.toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function handleClick(bd) {
    store.activeBreakdown = bd;
    onReplanWithBreakdown(bd.file);
  }
</script>

<section class="bg-white border border-(--color-border-subtle) rounded-lg p-4 shadow-(--shadow-sm)">
  <button class="flex items-center justify-between w-full cursor-pointer" onclick={() => open = !open}>
    <h3 class="text-sm font-semibold text-(--color-text-primary)">Scenarios</h3>
    <svg class="w-4 h-4 text-(--color-text-muted) transition-transform duration-200 {open ? 'rotate-0' : '-rotate-90'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <path d="M19 9l-7 7-7-7" />
    </svg>
  </button>

  {#if open}
    <div class="mt-4 flex flex-col gap-3 animate-[slideDown_0.2s_ease]">
      {#if breakdowns.length === 0}
        <p class="text-sm text-(--color-text-muted)">No scenarios found</p>
      {:else}
        {#each breakdowns as bd, i}
          <div class="p-3 bg-(--color-surface) rounded-lg border-l-3 border-l-(--color-breakdown) transition-all {store.activeBreakdown?.file === bd.file ? 'ring-2 ring-(--color-breakdown) ring-offset-2' : ''}">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold text-(--color-orsted) text-sm">Scenario #{i + 1}</span>
              <button
                class="px-3 py-1.5 bg-(--color-orsted) text-white rounded-md text-xs font-semibold cursor-pointer transition-colors hover:bg-(--color-orsted-dark) disabled:opacity-50 disabled:cursor-not-allowed"
                onclick={() => handleClick(bd)}
                disabled={store.loading}
              >
                Re-plan with this
              </button>
            </div>
            <div class="text-xs leading-relaxed text-(--color-text-primary) space-y-0.5">
              <div><span class="font-medium text-(--color-text-muted)">Windmill:</span> {bd.windmill_id}</div>
              <div><span class="font-medium text-(--color-text-muted)">Time:</span> {formatTime(bd.breakdown_time)}</div>
              <div><span class="font-medium text-(--color-text-muted)">Description:</span> {bd.description || 'N/A'}</div>
              <div><span class="font-medium text-(--color-text-muted)">Repair:</span> {bd.estimated_repair_duration_hours}h</div>
            </div>
          </div>
        {/each}
      {/if}
    </div>
  {/if}
</section>

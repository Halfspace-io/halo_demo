<script>
  import ConfigPanel from './ConfigPanel.svelte';
  import BreakdownPanel from './BreakdownPanel.svelte';

  let { onOptimize, onReplanWithBreakdown } = $props();
  let collapsed = $state(false);
</script>

{#if collapsed}
  <!-- Collapsed: thin icon strip -->
  <aside class="flex flex-col h-screen bg-white border-r border-(--color-border-faint) w-14 shrink-0">
    <div class="flex items-center justify-center py-4 border-b border-(--color-border-faint)">
      <img src="/visuals/sentinel_orchestrator.png" alt="Sentinel Orchestrator" class="w-8 h-8 rounded-lg object-cover" />
    </div>
    <div class="flex flex-col items-center gap-2 pt-4">
      <!-- Config icon -->
      <button
        class="w-10 h-10 flex items-center justify-center rounded-lg text-(--color-text-muted) hover:bg-(--color-surface) hover:text-(--color-orsted) transition-colors cursor-pointer"
        title="Configuration"
        onclick={() => collapsed = false}
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
          <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
        </svg>
      </button>
      <!-- Scenarios icon -->
      <button
        class="w-10 h-10 flex items-center justify-center rounded-lg text-(--color-text-muted) hover:bg-(--color-surface) hover:text-(--color-breakdown) transition-colors cursor-pointer"
        title="Scenarios"
        onclick={() => collapsed = false}
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
        </svg>
      </button>
    </div>
  </aside>
{:else}
  <!-- Expanded sidebar -->
  <aside class="flex flex-col h-screen bg-white border-r border-(--color-border-faint) w-80 shrink-0">
    <div class="flex items-center justify-between px-5 py-4 border-b border-(--color-border-faint)">
      <div class="flex items-center gap-3">
        <img src="/visuals/sentinel_orchestrator.png" alt="Sentinel Orchestrator" class="w-9 h-9 rounded-lg object-cover" />
        <div>
          <div class="text-sm font-bold text-(--color-text-primary)">Sentinel Orchestrator</div>
          <div class="text-xs text-(--color-text-muted)">Wind Farm Maintenance</div>
        </div>
      </div>
      <button
        class="w-8 h-8 flex items-center justify-center rounded-md text-(--color-text-muted) hover:bg-(--color-surface) hover:text-(--color-text-primary) transition-colors cursor-pointer"
        title="Collapse sidebar"
        onclick={() => collapsed = true}
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      <ConfigPanel {onOptimize} />
      <BreakdownPanel {onReplanWithBreakdown} />
    </div>
  </aside>
{/if}

<script>
  import { store } from '../lib/state.svelte.js';
  import ConfigPanel from './ConfigPanel.svelte';
  import BreakdownPanel from './BreakdownPanel.svelte';
  import ExplanationPanel from './ExplanationPanel.svelte';

  let { onOptimize, onReplanWithBreakdown } = $props();

  // null = collapsed, 'config' | 'scenarios' | 'ai' = expanded showing that panel
  let activePanel = $state(null);

  let expanded = $derived(activePanel !== null);
  let aiAvailable = $derived(store.currentView === 'optimized' && store.currentExplanation !== null);
  let aiLoading = $derived(store.currentExplanation?.loading === true);

  function togglePanel(panel) {
    activePanel = activePanel === panel ? null : panel;
  }
</script>

<aside
  class="flex h-screen bg-white border-r border-(--color-border-faint) shrink-0 transition-all duration-300 ease-in-out overflow-hidden"
  style:width="{expanded ? '320px' : '56px'}"
>
  <!-- Icon strip — always visible -->
  <div class="flex flex-col w-14 shrink-0">
    <div class="flex items-center justify-center py-4 border-b border-(--color-border-faint)">
      <img src="/visuals/sentinel_orchestrator.png" alt="Sentinel Orchestrator" class="w-8 h-8 rounded-lg object-cover" />
    </div>
    <div class="flex flex-col items-center gap-2 pt-4">
      <!-- Config icon -->
      <button
        class="w-10 h-10 flex items-center justify-center rounded-lg transition-colors cursor-pointer {activePanel === 'config' ? 'bg-(--color-orsted)/10 text-(--color-orsted)' : 'text-(--color-text-muted) hover:bg-(--color-surface) hover:text-(--color-orsted)'}"
        title="Configuration"
        onclick={() => togglePanel('config')}
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
          <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
        </svg>
      </button>
      <!-- Scenarios icon -->
      <button
        class="w-10 h-10 flex items-center justify-center rounded-lg transition-colors cursor-pointer {activePanel === 'scenarios' ? 'bg-(--color-breakdown)/10 text-(--color-breakdown)' : 'text-(--color-text-muted) hover:bg-(--color-surface) hover:text-(--color-breakdown)'}"
        title="Scenarios"
        onclick={() => togglePanel('scenarios')}
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
        </svg>
      </button>
      <!-- AI Insights icon -->
      {#if aiAvailable}
        <button
          class="relative w-10 h-10 flex items-center justify-center rounded-lg transition-colors cursor-pointer {activePanel === 'ai' ? 'bg-(--color-orsted)/10 text-(--color-orsted)' : 'text-(--color-text-muted) hover:bg-(--color-surface) hover:text-(--color-orsted)'}"
          title="AI Insights"
          onclick={() => togglePanel('ai')}
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09ZM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456ZM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423Z" />
          </svg>
          {#if aiLoading}
            <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-(--color-orsted) rounded-full animate-pulse"></span>
          {/if}
        </button>
      {/if}
    </div>
  </div>

  <!-- Panel content — slides in from the right of the icon strip -->
  {#if expanded}
    <div class="flex-1 min-w-0 border-l border-(--color-border-faint) flex flex-col animate-[fadeIn_0.2s_ease]">
      <div class="flex items-center justify-between px-4 py-4 border-b border-(--color-border-faint)">
        <div>
          <div class="text-sm font-bold text-(--color-text-primary)">
            {activePanel === 'config' ? 'Configuration' : activePanel === 'scenarios' ? 'Scenarios' : 'AI Analysis'}
          </div>
          <div class="text-xs text-(--color-text-muted)">
            {activePanel === 'config' ? 'Optimization parameters' : activePanel === 'scenarios' ? 'Breakdown scenarios' : 'Optimization insights'}
          </div>
        </div>
        <button
          class="w-7 h-7 flex items-center justify-center rounded-md text-(--color-text-muted) hover:bg-(--color-surface) hover:text-(--color-text-primary) transition-colors cursor-pointer"
          title="Close panel"
          onclick={() => activePanel = null}
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4">
        {#if activePanel === 'config'}
          <ConfigPanel {onOptimize} />
        {:else if activePanel === 'scenarios'}
          <BreakdownPanel {onReplanWithBreakdown} />
        {:else if activePanel === 'ai'}
          <ExplanationPanel />
        {/if}
      </div>
    </div>
  {/if}
</aside>

<style>
  @keyframes fadeIn {
    from { opacity: 0; transform: translateX(-8px); }
    to { opacity: 1; transform: translateX(0); }
  }
</style>

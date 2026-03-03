<script>
  import { store } from '../lib/state.svelte.js';

  let open = $state(false);

  let available = $derived(store.currentView === 'optimized' && store.currentExplanation !== null);
  let isLoading = $derived(store.currentExplanation?.loading === true);

  let formattedText = $derived.by(() => {
    if (!store.currentExplanation?.text) return '';
    return store.currentExplanation.text
      .replace(/•/g, '</li><li>')
      .replace(/<\/li><li>/, '<li>')
      .replace(/The optimized schedule:/gi, '<strong>The optimized schedule:</strong><ul>')
      + (store.currentExplanation.text.includes('•') ? '</li></ul>' : '');
  });
</script>

{#if available}
  <div class="bg-white border border-(--color-border-faint) rounded-xl shadow-(--shadow-card) overflow-hidden">
    <button
      class="flex items-center justify-between w-full px-5 py-4 cursor-pointer transition-colors hover:bg-(--color-surface)"
      onclick={() => open = !open}
    >
      <span class="flex items-center gap-2 text-sm font-semibold text-(--color-text-primary)">
        {#if isLoading}
          <span class="w-3.5 h-3.5 border-2 border-(--color-border-subtle) border-t-(--color-orsted) rounded-full animate-[spin_0.8s_linear_infinite]"></span>
        {/if}
        AI Analysis
      </span>
      <svg class="w-4 h-4 text-(--color-text-muted) transition-transform duration-250 {open ? 'rotate-0' : '-rotate-90'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if open}
      <div class="px-5 pb-5 animate-[slideDown_0.25s_ease]">
        {#if store.currentExplanation.loading}
          <div class="flex items-center gap-2.5 text-(--color-orsted) text-sm py-3">
            <span class="w-4.5 h-4.5 border-2 border-(--color-border-subtle) border-t-(--color-orsted) rounded-full animate-[spin_0.8s_linear_infinite]"></span>
            <span>Generating explanation...</span>
          </div>
        {:else if store.currentExplanation.error}
          <div class="text-sm text-(--color-breakdown) p-3 bg-red-50 rounded-lg">{store.currentExplanation.error}</div>
        {:else if store.currentExplanation.text}
          <div class="explanation-text text-sm leading-7 text-(--color-text-primary)">
            {@html formattedText}
          </div>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .explanation-text :global(ul) {
    margin: 8px 0 0;
    padding-left: 18px;
  }
  .explanation-text :global(li) {
    margin-bottom: 4px;
  }
</style>

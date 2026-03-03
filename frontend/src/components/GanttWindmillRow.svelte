<script>
  import GanttTaskBar from './GanttTaskBar.svelte';

  let { windmillId, tasks, timeRange, rowTop, rowHeight = 50 } = $props();
</script>

<div
  class="absolute flex flex-col justify-center bg-white text-right border-r-2 border-(--color-border-subtle) border-t border-t-(--color-border-faint) z-1 px-2 pr-3"
  style:top="{rowTop}px"
  style:height="{rowHeight - 10}px"
  style:left="-220px"
  style:width="200px"
>
  <div class="font-semibold text-sm text-(--color-orsted)">{windmillId}</div>
  <div class="text-xs text-(--color-text-muted)">{tasks.length} task{tasks.length !== 1 ? 's' : ''}</div>
</div>

{#each tasks as task (task.id)}
  <GanttTaskBar {task} {timeRange} {rowTop} {rowHeight} />
{/each}

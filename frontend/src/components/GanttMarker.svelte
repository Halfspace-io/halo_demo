<script>
  let { left, topOffset = 80, height, color = '#f56565', label = '', labelAlign = 'center' } = $props();
</script>

<div
  class="absolute w-0.5 border-l-2 border-dashed z-3 pointer-events-none"
  style:left="{left}%"
  style:top="{topOffset}px"
  style:height="{height}px"
  style:border-left-color={color}
></div>
{#if label}
  <div
    class="absolute text-white px-2 py-1 rounded text-[11px] font-semibold whitespace-nowrap z-4 pointer-events-none {labelAlign === 'right' ? '-translate-x-full' : '-translate-x-1/2'}"
    style:left="{left}%"
    style:top="{topOffset + 2}px"
    style:background={color}
  >
    {label}
  </div>
{/if}

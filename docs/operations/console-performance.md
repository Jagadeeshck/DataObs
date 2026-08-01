# Console performance

All major capability pages are loaded through registry-owned dynamic imports. The shell, route metadata, Quick Find route index, context, and evidence primitives remain common code. Cytoscape is reachable only through the Data Flow chunk; route-only Quick Find results do not import capability modules.

`pnpm build` records entry CSS/JavaScript and route chunks. `pnpm bundle:check` enforces the existing limits without relaxation. The closure artifact retains build output and major chunk sizes. Investigate duplicate dependencies or unexpected entry growth rather than increasing the gate.

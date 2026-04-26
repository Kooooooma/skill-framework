#!/usr/bin/env node

import { build as esbuild } from 'esbuild';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEFAULT_THEME = {
  background: '#FAFAFA',
  foreground: '#1C1B1F',
  muted: '#F3EDF7',
  muted_foreground: '#49454F',
  border_strong: '#79747E',
  accent: '#6750A4',
  accent_secondary: '#7D5260',
  accent_foreground: '#FFFFFF',
  border: '#79747E',
  card: '#F3EDF7',
  ring: '#6750A4',
  error: '#B3261E',
};

const ROW_HEIGHTS = {
  skill: 50,
  state: 42,
  execution: 42,
  step: 40,
};

const WIDTH_LIMITS = {
  skill: { min: 232, max: 336 },
  state: { min: 196, max: 292 },
  execution: { min: 204, max: 308 },
  step: { min: 198, max: 300 },
};

const compactLabel = (text) => String(text ?? '').split(/\s+/).filter(Boolean).join(' ');

const detailBody = (parts) => parts.filter(Boolean).join('\n\n');

const bulletSection = (title, items) => {
  if (!items.length) {
    return '';
  }
  return `${title}\n- ${items.join('\n- ')}`;
};

const escapeHtml = (value) =>
  String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

const safeScriptJson = (value) =>
  JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');

async function readUtf8(filePath) {
  return fs.readFile(filePath, 'utf-8');
}

async function loadJson(filePath) {
  return JSON.parse(await readUtf8(filePath));
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function skillSummary(root, machine) {
  const skillPath = path.join(root, 'SKILL.md');
  if (await exists(skillPath)) {
    const text = await readUtf8(skillPath);
    const match = text.match(/^description:\s*(.+)$/m);
    if (match) {
      return compactLabel(match[1].trim().replace(/^["']|["']$/g, ''));
    }
  }

  const theoryPath = path.join(root, 'theory.md');
  if (await exists(theoryPath)) {
    const text = await readUtf8(theoryPath);
    const match = text.match(/## Purpose\s+([\s\S]+?)(?:\n## |\Z)/);
    if (match) {
      return compactLabel(match[1]);
    }
  }

  const routeState = machine.states?.route_request ?? {};
  return compactLabel(
    routeState.purpose ??
      'Select a state, execution node, or workflow step to inspect its logic.'
  );
}

async function loadTheme(root) {
  const theme = { ...DEFAULT_THEME };
  const designPath = path.join(root, 'DESIGN.md');
  if (!(await exists(designPath))) {
    return theme;
  }

  const text = await readUtf8(designPath);
  const tableTokens = {};
  for (const match of text.matchAll(/\|\s*`([^`]+)`\s*\|\s*`(#[0-9a-fA-F]{6})`\s*\|/g)) {
    tableTokens[match[1].trim()] = match[2];
  }

  const mapping = {
    background: 'background',
    foreground: 'foreground',
    muted: 'muted',
    'muted-foreground': 'muted_foreground',
    accent: 'accent',
    'accent-secondary': 'accent_secondary',
    'accent-foreground': 'accent_foreground',
    border: 'border',
    card: 'card',
    ring: 'ring',
  };

  for (const [tokenName, themeKey] of Object.entries(mapping)) {
    if (tableTokens[tokenName]) {
      theme[themeKey] = tableTokens[tokenName];
    }
  }

  const prosePatterns = {
    background: /\*\*Background\s*\(Surface\)\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    foreground: /\*\*Foreground\s*\(On Surface\)\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    accent: /\*\*Primary\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    accent_foreground: /\*\*On Primary\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    muted: /\*\*Surface Container\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    card: /\*\*Surface Container\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    border: /\*\*Outline\s*\(Border\)\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    border_strong: /\*\*Outline\s*\(Border\)\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    muted_foreground: /\*\*On Surface Variant\*\*:\s*`(#[0-9a-fA-F]{6})`/,
    accent_secondary: /\*\*Tertiary\*\*:\s*`(#[0-9a-fA-F]{6})`/,
  };

  for (const [key, pattern] of Object.entries(prosePatterns)) {
    const match = text.match(pattern);
    if (match) {
      theme[key] = match[1];
    }
  }

  if (theme.card === theme.background) {
    theme.card = theme.muted;
  }
  if (theme.ring === DEFAULT_THEME.ring) {
    theme.ring = theme.accent;
  }
  return theme;
}

function orderedStateNames(initial, states, terminal) {
  const ordered = [];
  const seen = new Set();

  const add = (stateName) => {
    if (states[stateName] && !seen.has(stateName)) {
      seen.add(stateName);
      ordered.push(stateName);
    }
  };

  if (initial && states[initial]) {
    const queue = [initial];
    while (queue.length) {
      const stateName = queue.shift();
      if (seen.has(stateName)) {
        continue;
      }
      add(stateName);
      for (const target of Object.values(states[stateName].on || {})) {
        if (states[target] && !seen.has(target)) {
          queue.push(target);
        }
      }
    }
  }

  for (const stateName of Object.keys(states)) {
    if (!terminal.has(stateName) && stateName !== 'blocked') {
      add(stateName);
    }
  }

  if (states.blocked) {
    add('blocked');
  }

  for (const stateName of Object.keys(states)) {
    if (terminal.has(stateName)) {
      add(stateName);
    }
  }

  for (const stateName of Object.keys(states)) {
    add(stateName);
  }

  return ordered;
}

function topoOrder(nodes) {
  const remaining = new Map(
    Object.entries(nodes).map(([name, spec]) => [name, new Set(spec.depends_on || [])])
  );
  const ordered = [];
  const ready = Array.from(remaining.entries())
    .filter(([, deps]) => deps.size === 0)
    .map(([name]) => name)
    .sort();

  while (ready.length) {
    const nodeName = ready.shift();
    ordered.push(nodeName);
    for (const [otherName, deps] of remaining.entries()) {
      if (deps.has(nodeName)) {
        deps.delete(nodeName);
        if (deps.size === 0 && !ordered.includes(otherName) && !ready.includes(otherName)) {
          ready.push(otherName);
        }
      }
    }
    ready.sort();
  }

  for (const nodeName of Object.keys(nodes)) {
    if (!ordered.includes(nodeName)) {
      ordered.push(nodeName);
    }
  }

  return ordered;
}

function estimateNodeSize(kind, treeLabel, name) {
  const limits = WIDTH_LIMITS[kind] || WIDTH_LIMITS.step;
  const text = `${treeLabel} ${name}`.trim();
  const estimated = 72 + Math.ceil(text.length * 7.8);
  return [Math.max(limits.min, Math.min(limits.max, estimated)), ROW_HEIGHTS[kind] || ROW_HEIGHTS.step];
}

function buildStepModel(stateName, nodeName, step) {
  const stepName = String(step.name || '').trim() || `step_${step.step ?? '?'}`;
  const title = `${step.step ?? '?'}. ${stepName}`;
  const detailParts = [compactLabel(step.action || '')];
  if (step.done_when) {
    detailParts.push(`Done when: ${compactLabel(step.done_when)}`);
  }
  if (step.stop_if) {
    detailParts.push(`Stop if: ${compactLabel(step.stop_if)}`);
  }

  return {
    id: `step::${stateName}::${nodeName}::${step.step ?? 0}`,
    name: stepName,
    kind: 'step',
    tree_label: 'Step',
    detail_title: title,
    detail_type: 'Workflow Step',
    detail_body: detailBody(detailParts),
    size: estimateNodeSize('step', 'Step', stepName),
    collapsed: false,
    classes: [],
    children: [],
  };
}

function buildNodeModel(stateName, nodeName, contract, dependencies) {
  const steps = (contract.workflow || []).map((step) => buildStepModel(stateName, nodeName, step));
  const detailParts = [contract.purpose || '', contract.instruction || ''];
  if (dependencies.length) {
    detailParts.push(bulletSection('Depends on', dependencies));
  }
  if (steps.length) {
    detailParts.push(bulletSection('Workflow', steps.map((step) => step.detail_title)));
  }

  return {
    id: `exec::${stateName}::${nodeName}`,
    name: nodeName,
    kind: 'execution',
    tree_label: 'Node',
    detail_title: nodeName,
    detail_type: 'Execution Node',
    detail_body: detailBody(detailParts),
    dependencies,
    size: estimateNodeSize('execution', 'Node', nodeName),
    collapsed: false,
    classes: [],
    children: steps,
  };
}

function buildStateModel(stateName, spec, nodeContracts, graphNodes, initial, terminal) {
  const orderedNodes = topoOrder(graphNodes);
  const nodes = orderedNodes.map((nodeName) =>
    buildNodeModel(
      stateName,
      nodeName,
      nodeContracts[nodeName] || {},
      [...(graphNodes[nodeName]?.depends_on || [])]
    )
  );

  const transitionNotes = Object.entries(spec.on || {}).map(([eventName, target]) => `${eventName} -> ${target}`);
  const detailParts = [spec.purpose || ''];
  if (nodes.length) {
    detailParts.push(bulletSection('Execution nodes', nodes.map((node) => node.name)));
  }
  if (transitionNotes.length) {
    detailParts.push(bulletSection('Transitions', transitionNotes));
  }

  const classes = [];
  if (stateName === initial) {
    classes.push('initial');
  }
  if (terminal.has(stateName)) {
    classes.push('terminal');
  }
  if (stateName === 'blocked') {
    classes.push('blocked');
  }

  return {
    id: `state::${stateName}`,
    name: stateName,
    kind: 'state',
    tree_label: 'State',
    detail_title: stateName,
    detail_type: 'State',
    detail_body: detailBody(detailParts),
    transition_notes: transitionNotes,
    classes,
    size: estimateNodeSize('state', 'State', stateName),
    collapsed: false,
    children: nodes,
  };
}

async function buildPayload(root) {
  const machineDoc = await loadJson(path.join(root, 'skill.machine.json'));
  const graphDoc = await loadJson(path.join(root, 'node.graph.json'));
  const contractsDoc = await loadJson(path.join(root, 'contracts', 'nodes.json'));

  const machine = machineDoc.machine || {};
  const states = machine.states || {};
  const graphs = graphDoc.graphs || {};
  const nodeContracts = contractsDoc.nodes || {};
  const initial = machine.initial || null;
  const terminal = new Set(machine.terminal || []);
  const theme = await loadTheme(root);
  const summary = await skillSummary(root, machine);

  const orderedStates = orderedStateNames(initial, states, terminal);
  const stateModels = orderedStates.map((stateName) => {
    const spec = states[stateName];
    const graphId = spec.graph;
    const graphNodes = graphId ? graphs[graphId]?.nodes || {} : {};
    return buildStateModel(stateName, spec, nodeContracts, graphNodes, initial, terminal);
  });

  const rootDetailParts = [summary];
  if (initial) {
    rootDetailParts.push(`Initial state: ${initial}`);
  }
  if (stateModels.length) {
    rootDetailParts.push(bulletSection('States', stateModels.map((state) => state.name)));
  }
  if (terminal.size) {
    rootDetailParts.push(bulletSection('Terminal states', [...terminal]));
  }

  return {
    skill_name: path.basename(root),
    skill_summary: summary,
    theme: {
      ...theme,
      link: theme.border_strong,
    },
    root: {
      id: `skill::${path.basename(root)}`,
      name: path.basename(root),
      kind: 'skill',
      tree_label: 'Skill',
      detail_title: path.basename(root),
      detail_type: 'Skill',
      detail_body: detailBody(rootDetailParts),
      size: estimateNodeSize('skill', 'Skill', path.basename(root)),
      collapsed: false,
      classes: ['skill-root'],
      children: stateModels,
    },
  };
}

async function bundleClientScript() {
  const result = await esbuild({
    entryPoints: [path.join(__dirname, 'render_skill_client.js')],
    bundle: true,
    format: 'iife',
    platform: 'browser',
    target: ['es2020'],
    write: false,
    minify: false,
  });
  return result.outputFiles[0].text;
}

function htmlDocument(payload, bundledClient) {
  const payloadJson = safeScriptJson(payload);
  const theme = payload.theme;
  const title = `${payload.skill_name} Flow Diagram`;

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(title)}</title>
  <style>
    :root {
      --bg: ${theme.background};
      --fg: ${theme.foreground};
      --muted: ${theme.muted};
      --muted-fg: ${theme.muted_foreground};
      --border: ${theme.border};
      --border-strong: ${theme.border_strong};
      --accent: ${theme.accent};
      --accent-secondary: ${theme.accent_secondary};
      --accent-fg: ${theme.accent_foreground};
      --card: ${theme.card};
      --ring: ${theme.ring};
      --error: ${theme.error};
      --link: ${theme.link};
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      padding: 0;
      min-height: 100%;
      background: var(--bg);
      color: var(--fg);
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      overflow-x: auto;
    }
    body {
      min-width: 1140px;
    }
    .page {
      padding: 16px 428px 40px 20px;
      width: max-content;
      min-width: 100%;
    }
    .flow-shell {
      width: max-content;
      min-width: 100%;
    }
    .graph-panel {
      width: max-content;
      min-width: 780px;
    }
    .details-panel {
      background: var(--bg);
      width: 360px;
      padding-left: 24px;
      border-left: 1px solid color-mix(in srgb, var(--border) 72%, white);
      position: fixed;
      top: 16px;
      right: 28px;
      bottom: 24px;
      overflow: auto;
    }
    .panel-heading {
      display: grid;
      gap: 8px;
      margin-bottom: 18px;
    }
    .eyebrow {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted-fg);
    }
    .panel-title {
      margin: 0;
      font-size: 18px;
      line-height: 1.3;
    }
    .panel-copy {
      margin: 0;
      font-size: 12px;
      line-height: 1.7;
      color: var(--muted-fg);
      max-width: 70ch;
    }
    .details-section {
      padding-top: 18px;
      border-top: 1px solid color-mix(in srgb, var(--border) 72%, white);
    }
    .graph-stage {
      width: max-content;
      padding-right: 18px;
    }
    #graph-container {
      min-width: 860px;
      min-height: 680px;
    }
    .g6-node-row {
      display: inline-flex;
      align-items: center;
      gap: 11px;
      padding: 8px 13px;
      border: 1px solid color-mix(in srgb, var(--border-strong) 66%, white);
      border-radius: 999px;
      background: color-mix(in srgb, var(--bg) 86%, white);
      color: var(--fg);
      min-height: 100%;
    }
    .g6-node-row.selected {
      border-color: var(--ring);
      background: color-mix(in srgb, var(--ring) 10%, white);
    }
    .g6-node-row.initial {
      border-color: var(--ring);
    }
    .g6-node-row.terminal {
      border-color: color-mix(in srgb, var(--accent) 58%, var(--border-strong));
      color: var(--accent);
    }
    .g6-node-row.blocked {
      border-color: var(--error);
      color: var(--error);
    }
    .g6-node-row.execution-row {
      border-color: color-mix(in srgb, var(--accent) 38%, var(--border-strong));
    }
    .g6-node-row.skill-row,
    .g6-node-row.skill-root {
      border-color: color-mix(in srgb, var(--accent-secondary) 52%, var(--border-strong));
      background: color-mix(in srgb, var(--card) 36%, white);
    }
    .g6-node-kind {
      font-size: 11px;
      line-height: 1;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted-fg);
      padding: 4px 8px;
      border-radius: 999px;
      background: color-mix(in srgb, var(--muted) 74%, white);
    }
    .g6-node-row.terminal .g6-node-kind,
    .g6-node-row.blocked .g6-node-kind {
      color: currentColor;
      background: color-mix(in srgb, currentColor 10%, white);
    }
    .g6-node-name {
      font-size: 13px;
      line-height: 1.25;
      font-weight: 500;
      white-space: nowrap;
    }
    .details-type {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted-fg);
      margin-bottom: 8px;
    }
    .details-title {
      margin: 0 0 12px;
      font-size: 20px;
      line-height: 1.35;
    }
    .details-body {
      white-space: pre-wrap;
      font-size: 12px;
      line-height: 1.75;
      color: var(--fg);
    }
    @media (max-width: 1080px) {
      .page {
        padding-top: 16px;
        padding-left: 20px;
        padding-right: 28px;
        width: 100%;
      }
      .flow-shell {
        min-width: 100%;
        width: 100%;
      }
      .graph-panel,
      .details-panel {
        width: 100%;
        min-width: 0;
      }
      .graph-stage {
        width: 100%;
        padding-right: 0;
      }
      #graph-container {
        min-width: 820px;
      }
      .details-panel {
        position: static;
        right: auto;
        bottom: auto;
        overflow: visible;
        background: transparent;
        padding-left: 0;
        padding-top: 20px;
        border-left: 0;
        border-top: 1px solid color-mix(in srgb, var(--border) 72%, white);
      }
    }
  </style>
</head>
<body data-renderer="antv-g6">
  <div class="page">
    <div class="flow-shell">
      <main class="graph-panel" data-layout="indented">
        <div class="graph-stage">
          <div id="graph-container"></div>
        </div>
      </main>
      <aside class="details-panel">
        <div class="panel-heading">
          <div class="eyebrow">Skill</div>
          <h2 class="panel-title">${escapeHtml(payload.skill_name)}</h2>
          <p class="panel-copy">${escapeHtml(payload.skill_summary)}</p>
        </div>
        <div class="details-section">
          <div id="details-type" class="details-type">Overview</div>
          <h3 id="details-title" class="details-title">${escapeHtml(payload.skill_name)}</h3>
          <div id="details-body" class="details-body">${escapeHtml(payload.skill_summary)}</div>
        </div>
      </aside>
    </div>
  </div>
  <script>
    window.__SKILL_GRAPH_PAYLOAD__ = ${payloadJson};
  </script>
  <script>
${bundledClient}
  </script>
</body>
</html>
`;
}

function parseArgs(argv) {
  const args = [...argv];
  const result = { skillPath: null, output: null };

  while (args.length) {
    const token = args.shift();
    if (!result.skillPath && !token.startsWith('-')) {
      result.skillPath = token;
      continue;
    }
    if (token === '-o' || token === '--output') {
      result.output = args.shift() || null;
      continue;
    }
    throw new Error(`Unknown argument: ${token}`);
  }

  if (!result.skillPath) {
    throw new Error('Usage: node scripts/render_skill_html.mjs <skill-path> [-o output.html]');
  }

  return result;
}

async function main() {
  const { skillPath, output } = parseArgs(process.argv.slice(2));
  const root = path.resolve(skillPath);
  const payload = await buildPayload(root);
  const bundledClient = await bundleClientScript();
  const html = htmlDocument(payload, bundledClient);

  if (output) {
    await fs.writeFile(path.resolve(output), html, 'utf-8');
  } else {
    process.stdout.write(html);
  }
}

main().catch((error) => {
  console.error(`ERROR: ${error.message}`);
  process.exitCode = 1;
});

import { Graph, NodeEvent, Polyline, register, treeToGraphData } from '@antv/g6';

const INDENT = 168;
const MIN_GRAPH_WIDTH = 920;
const MIN_GRAPH_HEIGHT = 680;
const TREE_PADDING_X = 72;
const TREE_PADDING_Y = 56;
const ESTIMATED_ROW_PITCH = 78;
const EXTRA_BRANCH_WIDTH = 320;

const escapeHtml = (value) =>
  String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

const buildNodeMarkup = (item) => {
  const classes = ['g6-node-row', `${item.kind}-row`, ...(item.classes || [])];
  return `
    <div class="${classes.join(' ')}" data-node-id="${escapeHtml(item.id)}">
      <span class="g6-node-kind">${escapeHtml(item.tree_label)}</span>
      <span class="g6-node-name">${escapeHtml(item.name)}</span>
    </div>
  `;
};

class IndentedTreeEdge extends Polyline {
  getPoints() {
    const [sourceX, sourceY] = this.sourceNode.getCenter();
    const [targetX, targetY] = this.targetNode.getCenter();

    if (Math.abs(sourceY - targetY) <= 0.5) {
      return [
        [sourceX, sourceY],
        [targetX, targetY],
      ];
    }

    return [
      [sourceX, sourceY],
      [sourceX, targetY],
      [targetX, targetY],
    ];
  }
}

register('edge', 'indented-tree-edge', IndentedTreeEdge);

const indexTree = (root) => {
  const items = new Map();
  const walk = (node, parentId = null) => {
    items.set(node.id, { ...node, parent_id: parentId });
    (node.children || []).forEach((child) => walk(child, node.id));
  };
  walk(root);
  return items;
};

const buildGraphData = (tree) =>
  treeToGraphData(tree, {
    getNodeData: (node, depth) => {
      const [width, height] = node.size;
      return {
        id: node.id,
        depth,
        kind: node.kind,
        size: node.size,
        data: node,
        type: 'html',
        style: {
          size: node.size,
          dx: -width / 2,
          dy: -height / 2,
          innerHTML: buildNodeMarkup(node),
          cursor: 'pointer',
        },
      };
    },
    getEdgeData: (source, target) => ({
      id: `edge::${source.id}::${target.id}`,
      source: source.id,
      target: target.id,
    }),
  });

const createDetailsRenderer = (payload, itemIndex) => {
  const detailsType = document.getElementById('details-type');
  const detailsTitle = document.getElementById('details-title');
  const detailsBody = document.getElementById('details-body');

  return (selectedId) => {
    const item = selectedId ? itemIndex.get(selectedId) : null;
    if (!item) {
      detailsType.textContent = 'Overview';
      detailsTitle.textContent = payload.skill_name;
      detailsBody.textContent = payload.skill_summary;
      return;
    }
    detailsType.textContent = item.detail_type || item.kind || 'Item';
    detailsTitle.textContent = item.detail_title || item.name || item.id;
    detailsBody.textContent = item.detail_body || 'No additional details available.';
  };
};

const measureGraphPanelWidth = (graphContainer) => {
  const graphPanel = graphContainer.closest('.graph-panel');
  return Math.max(
    MIN_GRAPH_WIDTH,
    Math.floor(graphPanel?.clientWidth || graphContainer.clientWidth || MIN_GRAPH_WIDTH)
  );
};

const measureVisibleTree = (node, isCollapsed, depth = 0) => {
  let visibleCount = 1;
  let maxDepth = depth;
  if (!isCollapsed(node) && node.children?.length) {
    node.children.forEach((child) => {
      const childMetrics = measureVisibleTree(child, isCollapsed, depth + 1);
      visibleCount += childMetrics.visibleCount;
      maxDepth = Math.max(maxDepth, childMetrics.maxDepth);
    });
  }
  return { visibleCount, maxDepth };
};

const collectVisibleNodeIds = (node, isCollapsed, ids = []) => {
  ids.push(node.id);
  if (!isCollapsed(node) && node.children?.length) {
    node.children.forEach((child) => {
      collectVisibleNodeIds(child, isCollapsed, ids);
    });
  }
  return ids;
};

const estimateTreeSize = (root, graphContainer, isCollapsed) => {
  const panelWidth = measureGraphPanelWidth(graphContainer);
  const metrics = measureVisibleTree(root, isCollapsed);
  return {
    width: Math.max(panelWidth, (TREE_PADDING_X * 2) + (metrics.maxDepth * INDENT) + EXTRA_BRANCH_WIDTH),
    height: Math.max(MIN_GRAPH_HEIGHT, (TREE_PADDING_Y * 2) + (metrics.visibleCount * ESTIMATED_ROW_PITCH)),
  };
};

const measureRenderedTreeBounds = (root, graph) => {
  const visibleIds = collectVisibleNodeIds(
    root,
    () => false
  );

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  visibleIds.forEach((nodeId) => {
    if (graph.getElementVisibility(nodeId) === 'hidden') {
      return;
    }

    const nodeData = graph.getNodeData(nodeId);
    const [width, height] = nodeData?.size || nodeData?.style?.size || [196, 40];
    const [x, y] = graph.getElementPosition(nodeId);

    minX = Math.min(minX, x - (width / 2));
    minY = Math.min(minY, y - (height / 2));
    maxX = Math.max(maxX, x + (width / 2));
    maxY = Math.max(maxY, y + (height / 2));
  });

  if (!Number.isFinite(minX) || !Number.isFinite(minY)) {
    return null;
  }

  return { minX, minY, maxX, maxY };
};

const measureRenderedTreeSize = (root, graph, graphContainer) => {
  const panelWidth = measureGraphPanelWidth(graphContainer);
  const bounds = measureRenderedTreeBounds(root, graph);

  if (!bounds) {
    return estimateTreeSize(root, graphContainer, () => false);
  }

  return {
    width: Math.max(panelWidth, Math.ceil((bounds.maxX - bounds.minX) + (TREE_PADDING_X * 2))),
    height: Math.max(MIN_GRAPH_HEIGHT, Math.ceil((bounds.maxY - bounds.minY) + (TREE_PADDING_Y * 2))),
  };
};

const alignRenderedTree = async (root, graph) => {
  const bounds = measureRenderedTreeBounds(root, graph);
  if (!bounds) {
    return false;
  }

  const targetX = TREE_PADDING_X - bounds.minX;
  const targetY = TREE_PADDING_Y - bounds.minY;
  const [currentX, currentY] = graph.getPosition();

  if (Math.abs(targetX - currentX) <= 1 && Math.abs(targetY - currentY) <= 1) {
    return false;
  }

  await graph.translateTo([targetX, targetY], false);
  return true;
};

const applyGraphSize = (graphContainer, graph, nextSize) => {
  graphContainer.style.width = `${nextSize.width}px`;
  graphContainer.style.height = `${nextSize.height}px`;

  const [currentWidth, currentHeight] = graph.getSize();
  if (Math.abs(currentWidth - nextSize.width) <= 1 && Math.abs(currentHeight - nextSize.height) <= 1) {
    return false;
  }

  graph.resize(nextSize.width, nextSize.height);
  return true;
};

const syncHtmlNodes = (graph, itemIndex, selectedId) => {
  document.querySelectorAll('.g6-node-row[data-node-id]').forEach((row) => {
    const nodeId = row.getAttribute('data-node-id');
    if (!nodeId) {
      return;
    }

    row.classList.toggle('selected', nodeId === selectedId);
  });
};

export function renderSkillGraph(payload) {
  const graphContainer = document.getElementById('graph-container');
  if (!graphContainer) {
    throw new Error('Missing #graph-container');
  }

  const itemIndex = indexTree(payload.root);
  const renderDetails = createDetailsRenderer(payload, itemIndex);
  let selectedId = payload.root.id;
  const data = buildGraphData(payload.root);
  const initialSize = estimateTreeSize(
    payload.root,
    graphContainer,
    () => false
  );

  graphContainer.style.width = `${initialSize.width}px`;
  graphContainer.style.height = `${initialSize.height}px`;

  let sizeSyncQueued = false;

  const graph = new Graph({
    container: graphContainer,
    width: initialSize.width,
    height: initialSize.height,
    autoResize: false,
    animation: false,
    data,
    behaviors: [
      {
        type: 'click-select',
        enable: (event) => event.targetType === 'node',
        degree: 0,
        animation: false,
      },
    ],
    layout: {
      type: 'indented',
      direction: 'LR',
      fixedRoot: false,
      indent: INDENT,
      dropCap: true,
      getHGap: () => 18,
      getVGap: () => 18,
      getWidth: (datum) => datum.size?.[0] || 196,
      getHeight: (datum) => datum.size?.[1] || 36,
    },
    node: {
      type: 'html',
    },
    edge: {
      type: 'indented-tree-edge',
      style: {
        lineWidth: 1.35,
        stroke: payload.theme.link,
        strokeOpacity: 1,
        radius: 14,
      },
    },
  });

  const syncGraphSize = () => {
    if (sizeSyncQueued) {
      return;
    }

    sizeSyncQueued = true;
    window.requestAnimationFrame(async () => {
      sizeSyncQueued = false;
      const nextSize = measureRenderedTreeSize(payload.root, graph, graphContainer);
      applyGraphSize(graphContainer, graph, nextSize);
      await alignRenderedTree(payload.root, graph);
      const settledSize = measureRenderedTreeSize(payload.root, graph, graphContainer);
      applyGraphSize(graphContainer, graph, settledSize);
      syncHtmlNodes(graph, itemIndex, selectedId);
    });
  };

  graph.on(NodeEvent.CLICK, (event) => {
    const targetId = event?.target?.id;
    if (!targetId) {
      return;
    }

    const item = itemIndex.get(targetId);
    if (!item) {
      return;
    }

    selectedId = item.id;
    renderDetails(selectedId);
  });

  renderDetails(selectedId);

  graph
    .render()
    .then(() => {
      syncHtmlNodes(graph, itemIndex, selectedId);
      syncGraphSize();
    })
    .catch((error) => {
      throw error;
    });

  window.addEventListener('resize', () => {
    syncGraphSize();
  });
}

renderSkillGraph(window.__SKILL_GRAPH_PAYLOAD__);

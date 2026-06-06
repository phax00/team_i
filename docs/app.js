const DATASETS = {
  core: {
    name: "Basic Graph",
    url: "./data/knowledge_graph_core_normalized.json"
  },
  school: {
    name: "Detailed Graph",
    url: "./data/knowledge_graph_school_mvp_normalized.json"
  }
};

const LABEL_COLORS = {
  Person: "#7B3AED",
  Role: "#0F766E",
  Skill: "#F59E0B",
  Topic: "#EC4899",
  System: "#10B981",
  JobDescription: "#DDD6FE",
  Department: "#EF4444",
  Team: "#06B6D4",
  Site: "#84CC16",
  Country: "#F97316",
  Repository: "#2563EB",
  Commit: "#64748B",
  PullRequest: "#14B8A6",
  JiraIssue: "#DC2626",
  Project: "#8B5CF6"
};

const LABEL_PRIORITY = {
  Person: 0,
  Role: 1,
  Team: 2,
  Department: 3,
  Site: 4,
  Country: 5,
  JobDescription: 6,
  Skill: 7,
  System: 8,
  Topic: 9,
  Repository: 10,
  Project: 11,
  JiraIssue: 12,
  PullRequest: 13,
  Commit: 14
};

const PRESETS = {
  org: {
    name: "Org View",
    labels: ["Person", "Role", "Team", "Country", "Site", "Department"],
    relationships: ["HAS_ROLE", "MEMBER_OF", "LOCATED_IN", "AT_SITE", "REPORTS_TO", "BELONGS_TO_DEPARTMENT", "IN_COUNTRY"]
  },
  skills: {
    name: "Skills View",
    labels: ["Person", "Skill", "Topic", "System", "Role"],
    relationships: ["HAS_SKILL", "OWNS_TOPIC", "KNOWS_SYSTEM", "HAS_ROLE", "REPORTS_TO"]
  },
  job: {
    name: "JD View",
    labels: ["JobDescription", "Role", "Department", "Skill", "Country", "Site"],
    relationships: ["DESCRIBED_BY", "SCOPES_TO_DEPARTMENT", "BELONGS_TO_DEPARTMENT", "REQUIRES_SKILL", "APPLIES_TO_SITE", "APPLIES_TO_COUNTRY", "IN_COUNTRY", "LINKED_TO_JD"]
  },
  activity: {
    name: "Activity View",
    labels: ["Person", "Repository", "Commit", "PullRequest", "JiraIssue", "Project", "Skill", "System", "Topic"],
    relationships: [
      "CONTRIBUTED_TO_REPOSITORY",
      "AUTHORED_COMMIT",
      "OPENED_PULL_REQUEST",
      "WORKED_ON_TICKET",
      "REPORTED_TICKET",
      "COMMENTED_ON_TICKET",
      "IN_REPOSITORY",
      "BELONGS_TO_PROJECT",
      "IMPACTS_SYSTEM",
      "EVIDENCES_SKILL",
      "TAGGED_WITH_TOPIC",
      "USES_TECHNOLOGY"
    ]
  },
  full: {
    name: "Full Graph",
    labels: null,
    relationships: null
  }
};

const SEARCHABLE_LABELS = new Set(["Person", "Role", "Repository", "JiraIssue", "Project", "Skill"]);
const BROWSE_LABEL_ORDER = ["Person", "Role", "Skill", "Topic", "System", "Department", "Team", "Country", "Site", "JobDescription", "Repository", "JiraIssue", "Project"];

const state = {
  datasetKey: "school",
  graphCache: {},
  raw: null,
  nodeMap: new Map(),
  adjacency: new Map(),
  labelCounts: new Map(),
  relationshipCounts: new Map(),
  activePreset: "org",
  labelFilter: new Set(),
  relationshipFilter: new Set(),
  searchTerm: "",
  selectedNodeId: null,
  browseLabel: "Person",
  depth: 2,
  defaultFocusNodeId: null,
  manualNetworkHeight: null,
  appliedNetworkHeight: null,
  programmaticHeightSync: false,
  postLoadRenderTimer: null,
  resizeObserver: null,
  network: null,
  networkFrameKey: null,
  visNodes: null,
  visEdges: null
};

const el = {};

document.addEventListener("DOMContentLoaded", async () => {
  cacheElements();
  bindUI();
  await loadDataset(state.datasetKey);
  schedulePostLoadRender();
});

function cacheElements() {
  el.metaDataset = document.getElementById("meta-dataset");
  el.metaSource = document.getElementById("meta-source");
  el.metaScope = document.getElementById("meta-scope");
  el.searchInput = document.getElementById("search-input");
  el.depthSelect = document.getElementById("depth-select");
  el.resetView = document.getElementById("reset-view");
  el.clearFilters = document.getElementById("clear-filters");
  el.datasetRow = document.getElementById("dataset-row");
  el.presetRow = document.getElementById("preset-row");
  el.labelFilters = document.getElementById("label-filters");
  el.relationshipFilters = document.getElementById("relationship-filters");
  el.browseLabel = document.getElementById("browse-label");
  el.browseNode = document.getElementById("browse-node");
  el.quickPicks = document.getElementById("quick-picks");
  el.graphCaption = document.getElementById("graph-caption");
  el.legend = document.getElementById("legend");
  el.networkWrap = document.getElementById("graph-network-wrap");
  el.network = document.getElementById("graph-network");
  el.graphResizeHandle = document.getElementById("graph-resize-handle");
  el.resetGraphSize = document.getElementById("reset-graph-size");
  el.statNodes = document.getElementById("stat-nodes");
  el.statRelationships = document.getElementById("stat-relationships");
  el.statRenderedNodes = document.getElementById("stat-rendered-nodes");
  el.statRenderedRelationships = document.getElementById("stat-rendered-relationships");
  el.selectionEmpty = document.getElementById("selection-empty");
  el.selectionDetails = document.getElementById("selection-details");
  el.detailsBody = document.getElementById("details-body");
  applyGraphResizeHandleStyles();
}

function bindUI() {
  window.addEventListener("resize", debounce(() => {
    if (state.raw) {
      state.manualNetworkHeight = null;
      syncNetworkSize();
      render();
    }
  }, 120));

  el.searchInput.addEventListener("input", () => {
    state.searchTerm = el.searchInput.value.trim().toLowerCase();
    if (!state.searchTerm) {
      state.selectedNodeId = state.defaultFocusNodeId;
    } else {
      const bestMatch = findBestSearchMatch(state.searchTerm);
      if (bestMatch) {
        state.selectedNodeId = bestMatch.id;
      }
    }
    render();
  });

  el.depthSelect.addEventListener("change", () => {
    state.depth = Number(el.depthSelect.value);
    render();
  });

  el.resetView.addEventListener("click", () => {
    state.searchTerm = "";
    el.searchInput.value = "";
    state.selectedNodeId = state.defaultFocusNodeId;
    state.depth = 2;
    el.depthSelect.value = "2";
    applyPreset("org");
  });

  el.clearFilters.addEventListener("click", () => {
    applyPreset(state.activePreset);
  });

  el.resetGraphSize.addEventListener("click", () => {
    state.manualNetworkHeight = null;
    render();
  });

  el.browseLabel.addEventListener("change", () => {
    state.browseLabel = el.browseLabel.value;
    buildBrowseControls();
  });

  el.browseNode.addEventListener("change", () => {
    const nextId = el.browseNode.value;
    if (!nextId) {
      return;
    }
    state.selectedNodeId = nextId;
    state.searchTerm = "";
    el.searchInput.value = "";
    render();
  });

  el.datasetRow.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-dataset]");
    if (!button || button.dataset.dataset === state.datasetKey) {
      return;
    }
    await loadDataset(button.dataset.dataset);
  });

  el.presetRow.addEventListener("click", (event) => {
    const button = event.target.closest("[data-preset]");
    if (!button || button.disabled) {
      return;
    }
    applyPreset(button.dataset.preset);
  });

  el.quickPicks.addEventListener("click", (event) => {
    const button = event.target.closest("[data-node-id]");
    if (!button) {
      return;
    }
    state.selectedNodeId = button.dataset.nodeId;
    render();
  });

  el.detailsBody.addEventListener("click", (event) => {
    const action = event.target.closest("[data-action]");
    if (!action) {
      return;
    }
    if (action.dataset.action === "focus-selection") {
      state.searchTerm = "";
      el.searchInput.value = "";
      render();
    }
    if (action.dataset.action === "jump-node" && action.dataset.nodeId) {
      state.selectedNodeId = action.dataset.nodeId;
      render();
    }
  });

  setupNetworkResizeObserver();
  setupGraphResizeHandle();
}

function createNetwork() {
  const width = Math.max(320, Math.round(el.network.clientWidth || 0));
  const height = Math.max(260, Math.round(el.network.clientHeight || 0));
  state.visNodes = new vis.DataSet([]);
  state.visEdges = new vis.DataSet([]);

  state.network = new vis.Network(
    el.network,
    { nodes: state.visNodes, edges: state.visEdges },
    {
      width: `${width}px`,
      height: `${height}px`,
      autoResize: true,
      interaction: {
        hover: true,
        navigationButtons: true,
        keyboard: true
      },
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -80,
          centralGravity: 0.02,
          springLength: 170,
          springConstant: 0.05,
          damping: 0.7,
          avoidOverlap: 0.9
        },
        stabilization: {
          enabled: true,
          iterations: 220,
          fit: true
        }
      },
      nodes: {
        shape: "dot",
        borderWidth: 1.5,
        font: {
          face: "Space Grotesk",
          size: 14,
          color: "#183247"
        }
      },
      edges: {
        width: 1.4,
        color: {
          color: "rgba(24, 50, 71, 0.16)",
          highlight: "#145f74"
        },
        smooth: {
          type: "dynamic"
        }
      }
    }
  );

  state.network.on("click", (params) => {
    if (!params.nodes.length) {
      return;
    }
    state.selectedNodeId = params.nodes[0];
    render();
  });

  syncNetworkSize();
}

function destroyNetwork() {
  if (state.network) {
    state.network.destroy();
  }
  state.network = null;
  state.visNodes = null;
  state.visEdges = null;
}

function ensureNetwork() {
  const width = Math.max(320, Math.round(el.network.clientWidth || 0));
  const height = Math.max(260, Math.round(el.network.clientHeight || 0));
  const frameKey = `${width}x${height}`;

  if (!state.network || state.networkFrameKey !== frameKey) {
    destroyNetwork();
    state.networkFrameKey = frameKey;
    createNetwork();
  }
}

async function loadDataset(datasetKey) {
  state.datasetKey = datasetKey;
  if (!state.graphCache[datasetKey]) {
    const response = await fetch(DATASETS[datasetKey].url);
    if (!response.ok) {
      throw new Error(`Failed to load ${DATASETS[datasetKey].url}: HTTP ${response.status}`);
    }
    state.graphCache[datasetKey] = await response.json();
  }

  state.raw = state.graphCache[datasetKey];
  reindexGraph();
  state.defaultFocusNodeId = findDefaultFocusNodeId();
  state.selectedNodeId = state.defaultFocusNodeId;
  state.searchTerm = "";
  el.searchInput.value = "";

  if (datasetKey === "core" && state.activePreset === "activity") {
    state.activePreset = "org";
  }

  updateDatasetButtons();
  updatePresetButtons();
  applyPreset(state.activePreset);
  schedulePostLoadRender();
}

function schedulePostLoadRender() {
  if (state.postLoadRenderTimer) {
    window.clearTimeout(state.postLoadRenderTimer);
  }
  state.postLoadRenderTimer = window.setTimeout(() => {
    if (!state.raw) {
      return;
    }
    syncNetworkSize();
    render();
    state.postLoadRenderTimer = null;
  }, 80);
}

function reindexGraph() {
  state.nodeMap = new Map();
  state.adjacency = new Map();
  state.labelCounts = new Map();
  state.relationshipCounts = new Map();

  for (const node of state.raw.nodes) {
    state.nodeMap.set(node.id, node);
    state.adjacency.set(node.id, []);
    state.labelCounts.set(node.label, (state.labelCounts.get(node.label) || 0) + 1);
  }

  for (const rel of state.raw.relationships) {
    state.relationshipCounts.set(rel.type, (state.relationshipCounts.get(rel.type) || 0) + 1);
    state.adjacency.get(rel.start)?.push({ ...rel, direction: "out" });
    state.adjacency.get(rel.end)?.push({ ...rel, direction: "in" });
  }

  const sources = state.raw.meta.generated_from.map((value) => value.split("/").pop()).join(" + ");
  if (el.metaDataset) el.metaDataset.textContent = DATASETS[state.datasetKey].name;
  if (el.metaSource) el.metaSource.textContent = sources;
  if (el.metaScope) el.metaScope.textContent = state.raw.meta.graph_scope;
  if (el.statNodes) el.statNodes.textContent = state.raw.meta.node_count;
  if (el.statRelationships) el.statRelationships.textContent = state.raw.meta.relationship_count;
}

function updateDatasetButtons() {
  for (const button of el.datasetRow.querySelectorAll("[data-dataset]")) {
    button.classList.toggle("active", button.dataset.dataset === state.datasetKey);
  }
}

function updatePresetButtons() {
  const activityAllowed = state.datasetKey === "school";
  for (const button of el.presetRow.querySelectorAll("[data-preset]")) {
    const presetKey = button.dataset.preset;
    const shouldHide = presetKey === "activity" && !activityAllowed;
    button.classList.toggle("hidden", shouldHide);
    button.disabled = shouldHide;
    button.classList.toggle("active", presetKey === state.activePreset);
  }
}

function applyPreset(presetKey) {
  state.activePreset = presetKey;
  const preset = PRESETS[presetKey];
  const labels = preset.labels || [...state.labelCounts.keys()];
  const relationships = preset.relationships || [...state.relationshipCounts.keys()];

  state.labelFilter = new Set(labels.filter((value) => state.labelCounts.has(value)));
  state.relationshipFilter = new Set(relationships.filter((value) => state.relationshipCounts.has(value)));

  if (!state.selectedNodeId || !nodeMatchesActivePreset(state.selectedNodeId)) {
    state.selectedNodeId = findBestFocusNodeIdForPreset(presetKey) || state.defaultFocusNodeId;
  }

  buildFilterControls();
  buildBrowseControls();
  buildLegend();
  buildQuickPicks();
  updatePresetButtons();
  render();
}

function buildFilterControls() {
  el.labelFilters.innerHTML = "";
  for (const [label, count] of [...state.labelCounts.entries()].sort(sortByCountThenName)) {
    el.labelFilters.appendChild(
      buildToggleCard(label, count, state.labelFilter.has(label), (checked) => {
        toggleSetValue(state.labelFilter, label, checked);
        render();
      })
    );
  }

  el.relationshipFilters.innerHTML = "";
  for (const [relType, count] of [...state.relationshipCounts.entries()].sort(sortByCountThenName)) {
    el.relationshipFilters.appendChild(
      buildToggleCard(relType, count, state.relationshipFilter.has(relType), (checked) => {
        toggleSetValue(state.relationshipFilter, relType, checked);
        render();
      })
    );
  }
}

function buildBrowseControls() {
  const availableLabels = BROWSE_LABEL_ORDER.filter((label) => state.labelCounts.has(label));
  if (!availableLabels.length) {
    el.browseLabel.innerHTML = "";
    el.browseNode.innerHTML = "";
    return;
  }

  if (!availableLabels.includes(state.browseLabel)) {
    state.browseLabel = availableLabels[0];
  }

  el.browseLabel.innerHTML = availableLabels
    .map((label) => `<option value="${escapeHtml(label)}"${label === state.browseLabel ? " selected" : ""}>${escapeHtml(label)}</option>`)
    .join("");

  const valueNodes = state.raw.nodes
    .filter((node) => node.label === state.browseLabel)
    .sort((a, b) => a.name.localeCompare(b.name));

  const selectedNode = state.nodeMap.get(state.selectedNodeId);
  const shouldSelectCurrent = selectedNode?.label === state.browseLabel;
  const currentValue = shouldSelectCurrent ? selectedNode.id : "";

  el.browseNode.innerHTML = [
    `<option value="">Select ${escapeHtml(state.browseLabel)}</option>`,
    ...valueNodes.map((node) => `<option value="${escapeHtml(node.id)}"${node.id === currentValue ? " selected" : ""}>${escapeHtml(node.name)}</option>`)
  ].join("");
}

function buildToggleCard(name, count, checked, onChange) {
  const wrapper = document.createElement("label");
  wrapper.className = "toggle-card";

  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = checked;
  input.addEventListener("change", () => onChange(input.checked));

  const body = document.createElement("span");
  body.className = "toggle-body";
  body.innerHTML = `<strong>${name}</strong><span class="badge">${count}</span>`;

  wrapper.append(input, body);
  return wrapper;
}

function buildLegend() {
  el.legend.innerHTML = "";
  const labels = [...state.labelFilter].sort((a, b) => (LABEL_PRIORITY[a] ?? 99) - (LABEL_PRIORITY[b] ?? 99) || a.localeCompare(b));
  for (const label of labels) {
    const count = state.labelCounts.get(label) || 0;
    const item = document.createElement("span");
    item.className = "legend-item";
    item.innerHTML = `<span class="legend-swatch" style="background:${getColor(label)}"></span>${label}<span class="badge">${count}</span>`;
    el.legend.appendChild(item);
  }
}

function buildQuickPicks() {
  let candidates = [];
  if (state.datasetKey === "school") {
    const pick = (label, count) => state.raw.nodes
      .filter((node) => node.label === label)
      .sort((a, b) => a.name.localeCompare(b.name))
      .slice(0, count);

    candidates = [
      ...pick("Person", 10),
      ...pick("Role", 4),
      ...pick("Repository", 3),
      ...pick("JiraIssue", 3)
    ];
  } else {
    candidates = state.raw.nodes
      .filter((node) => ["Person", "Role", "JobDescription"].includes(node.label))
      .sort((a, b) => (LABEL_PRIORITY[a.label] ?? 99) - (LABEL_PRIORITY[b.label] ?? 99) || a.name.localeCompare(b.name))
      .slice(0, 18);
  }

  el.quickPicks.innerHTML = "";
  for (const node of candidates) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-pick";
    if (node.id === state.selectedNodeId) {
      button.classList.add("active");
    }
    button.dataset.nodeId = node.id;
    button.textContent = node.name;
    el.quickPicks.appendChild(button);
  }
}

function render() {
  if (!state.raw) {
    return;
  }

  const filtered = buildVisibleSubgraph();
  applyAdaptiveCanvasHeight(filtered.nodes.length);
  ensureNetwork();
  syncNetworkSize();
  state.visNodes.clear();
  state.visEdges.clear();
  state.visNodes.add(filtered.nodes);
  state.visEdges.add(filtered.edges);

  state.network.setOptions({
    physics: {
      enabled: true,
      solver: "forceAtlas2Based",
      forceAtlas2Based: {
        gravitationalConstant: filtered.nodes.length <= 18 ? -120 : -80,
        centralGravity: 0.02,
        springLength: filtered.nodes.length <= 18 ? 210 : 170,
        springConstant: 0.05,
        damping: 0.7,
        avoidOverlap: 1
      },
      stabilization: {
        enabled: true,
        iterations: 220,
        fit: true
      }
    }
  });

  state.network.stabilize(220);
  requestAnimationFrame(() => {
    syncNetworkSize();
    state.network.fit({
      animation: {
        duration: 350,
        easingFunction: "easeInOutQuad"
      }
    });
  });

  el.statRenderedNodes.textContent = filtered.nodes.length;
  el.statRenderedRelationships.textContent = filtered.edges.length;
  el.graphCaption.textContent = `${PRESETS[state.activePreset].name} - ${filtered.nodes.length} nodes - ${filtered.edges.length} relationships`;

  buildBrowseControls();
  buildQuickPicks();

  if (state.selectedNodeId && state.nodeMap.has(state.selectedNodeId)) {
    renderDetails(state.selectedNodeId);
  } else {
    renderEmptyDetails();
  }
}

function findBestSearchMatch(term) {
  if (!term) {
    return null;
  }

  let bestNode = null;
  let bestScore = -1;

  for (const node of state.raw.nodes) {
    const haystack = JSON.stringify(node).toLowerCase();
    const name = node.name.toLowerCase();
    const labelBonus = SEARCHABLE_LABELS.has(node.label) ? 20 : 0;
    let score = -1;

    if (name === term) {
      score = 500 + labelBonus;
    } else if (name.startsWith(term)) {
      score = 400 + labelBonus;
    } else if (name.includes(term)) {
      score = 300 + labelBonus;
    } else if (haystack.includes(term)) {
      score = 160 + labelBonus;
    }

    if (score > bestScore) {
      bestScore = score;
      bestNode = node;
    }
  }

  return bestNode;
}

function buildVisibleSubgraph() {
  const visibleNodeIds = new Set();
  const visibleEdges = [];

  const allowedNode = (nodeId) => {
    const node = state.nodeMap.get(nodeId);
    return node && state.labelFilter.has(node.label);
  };
  const allowedEdge = (rel) => state.relationshipFilter.has(rel.type);
  const matchesSearch = (node) => !state.searchTerm || JSON.stringify(node).toLowerCase().includes(state.searchTerm);

  const rootIds = [];
  if (state.selectedNodeId) {
    rootIds.push(state.selectedNodeId);
  } else {
    for (const node of state.raw.nodes) {
      if (allowedNode(node.id) && matchesSearch(node)) {
        rootIds.push(node.id);
      }
    }
  }

  if (!rootIds.length) {
    return { nodes: [], edges: [], useFocusedLayout: false };
  }

  const queue = rootIds.slice(0, 16).map((id) => ({ id, depth: 0 }));
  const seenDepth = new Map();

  while (queue.length) {
    const current = queue.shift();
    if (!current || !allowedNode(current.id)) {
      continue;
    }

    const knownDepth = seenDepth.get(current.id);
    if (knownDepth !== undefined && knownDepth <= current.depth) {
      continue;
    }
    seenDepth.set(current.id, current.depth);
    visibleNodeIds.add(current.id);

    if (current.depth >= state.depth) {
      continue;
    }

    const adjacent = state.adjacency.get(current.id) || [];
    for (const rel of adjacent) {
      if (!allowedEdge(rel)) {
        continue;
      }
      const nextId = rel.start === current.id ? rel.end : rel.start;
      if (!allowedNode(nextId)) {
        continue;
      }
      visibleEdges.push(rel);
      queue.push({ id: nextId, depth: current.depth + 1 });
    }
  }

  const dedupedEdges = dedupeEdges(visibleEdges).filter((rel) => visibleNodeIds.has(rel.start) && visibleNodeIds.has(rel.end));
  const nodes = [...visibleNodeIds]
    .map((id) => decorateNode(state.nodeMap.get(id)))
    .sort((a, b) => a.label.localeCompare(b.label));
  const edges = dedupedEdges.map(decorateEdge);

  return { nodes, edges };
}

function decorateNode(node) {
  const isSelected = node.id === state.selectedNodeId;
  const color = getColor(node.label);
  return {
    id: node.id,
    label: node.name,
    title: `${node.label}: ${node.name}`,
    shape: node.label === "JobDescription" ? "box" : "dot",
    color: {
      background: color,
      border: isSelected ? "#183247" : "#fffaf2",
      highlight: {
        background: color,
        border: "#183247"
      },
      hover: {
        background: color,
        border: "#183247"
      }
    },
    size: isSelected ? 28 : getNodeSize(node.label),
    font: {
      face: "Space Grotesk",
      size: isSelected ? 16 : 13,
      color: "#141414"
    },
    physics: true
  };
}

function decorateEdge(rel) {
  return {
    id: `${rel.start}-${rel.type}-${rel.end}`,
    from: rel.start,
    to: rel.end,
    title: rel.type,
    arrows: "to"
  };
}

function renderDetails(nodeId) {
  const node = state.nodeMap.get(nodeId);
  if (!node) {
    renderEmptyDetails();
    return;
  }

  const context = buildNodeContext(nodeId);
  const heroSubtitle = buildHeroSubtitle(node, context);
  const chips = buildHeroChips(node, context);
  const sections = buildDetailSections(node, context);

  el.selectionEmpty.classList.add("hidden");
  el.selectionDetails.classList.remove("hidden");
  el.detailsBody.innerHTML = `
    <div class="detail-card">
      <section class="detail-hero">
        <p class="detail-label">${node.label}</p>
        <div class="detail-title-row">
          <div>
            <h3>${escapeHtml(node.name)}</h3>
            <p class="detail-subtitle">${escapeHtml(heroSubtitle)}</p>
          </div>
          <button class="ghost-button" data-action="focus-selection">Focus Node</button>
        </div>
        ${chips.length ? `<div class="detail-chip-row">${chips.map(renderChip).join("")}</div>` : ""}
      </section>
      <div class="detail-grid">
        ${sections.join("")}
      </div>
    </div>
  `;
}

function buildNodeContext(nodeId) {
  const adjacent = state.adjacency.get(nodeId) || [];
  const related = adjacent.map((rel) => {
    const otherId = rel.start === nodeId ? rel.end : rel.start;
    return {
      rel,
      other: state.nodeMap.get(otherId)
    };
  }).filter((item) => item.other);

  return {
    related,
    outgoing(type) {
      return related.filter((item) => item.rel.type === type && item.rel.start === nodeId).map((item) => item.other);
    },
    incoming(type) {
      return related.filter((item) => item.rel.type === type && item.rel.end === nodeId).map((item) => item.other);
    },
    both(type) {
      return related.filter((item) => item.rel.type === type).map((item) => item.other);
    },
    groupedByType() {
      const grouped = new Map();
      for (const item of related) {
        if (!grouped.has(item.rel.type)) {
          grouped.set(item.rel.type, []);
        }
        grouped.get(item.rel.type).push(item.other);
      }
      return grouped;
    }
  };
}

function buildHeroSubtitle(node, context) {
  if (node.label === "Person") {
    const role = context.outgoing("HAS_ROLE")[0]?.name;
    const team = context.outgoing("MEMBER_OF")[0]?.name;
    const country = context.outgoing("LOCATED_IN")[0]?.name;
    return [role, team, country].filter(Boolean).join(" | ") || "Person profile";
  }
  if (node.label === "Role") {
    const department = context.outgoing("BELONGS_TO_DEPARTMENT")[0]?.name;
    return department || "Organizational role";
  }
  if (node.label === "Repository") {
    return node.language || "Public GitHub repository";
  }
  if (node.label === "JiraIssue") {
    return `${node.issue_type || "Issue"} | ${node.status || "Unknown status"} | ${node.priority || "Unknown priority"}`;
  }
  if (node.label === "JobDescription") {
    return node.department || node.role_name || "Job description";
  }
  return "Knowledge graph node";
}

function buildHeroChips(node, context) {
  const chips = [];
  if (node.label === "Person") {
    const manager = context.outgoing("REPORTS_TO")[0]?.name;
    const site = context.outgoing("AT_SITE")[0]?.name;
    const jd = context.outgoing("LINKED_TO_JD")[0]?.name;
    if (manager) {
      chips.push({ label: "Manager", value: manager });
    }
    if (site) {
      chips.push({ label: "Site", value: site });
    }
    if (jd) {
      chips.push({ label: "JD", value: jd });
    }
    if (node.seniority) {
      chips.push({ label: "Seniority", value: node.seniority });
    }
  } else if (node.label === "Role") {
    const jd = context.outgoing("DESCRIBED_BY")[0]?.name;
    const peopleCount = context.incoming("HAS_ROLE").length;
    if (jd) {
      chips.push({ label: "JD", value: jd });
    }
    chips.push({ label: "People", value: String(peopleCount) });
  } else if (node.label === "Repository") {
    if (node.language) {
      chips.push({ label: "Language", value: node.language });
    }
    if (node.topics?.length) {
      chips.push({ label: "Topics", value: String(node.topics.length) });
    }
  } else if (node.label === "JiraIssue") {
    chips.push({ label: "Project", value: node.project_key || "N/A" });
    if (node.country) {
      chips.push({ label: "Country", value: node.country });
    }
  }
  return chips.slice(0, 4);
}

function buildDetailSections(node, context) {
  if (node.label === "Person") {
    return buildPersonSections(node, context);
  }
  if (node.label === "Role") {
    return buildRoleSections(node, context);
  }
  if (node.label === "Repository") {
    return buildRepositorySections(node, context);
  }
  if (node.label === "JiraIssue") {
    return buildJiraSections(node, context);
  }
  return buildGenericSections(node, context);
}

function buildPersonSections(node, context) {
  const role = context.outgoing("HAS_ROLE")[0]?.name || "N/A";
  const team = context.outgoing("MEMBER_OF")[0]?.name || "N/A";
  const country = context.outgoing("LOCATED_IN")[0]?.name || "N/A";
  const manager = context.outgoing("REPORTS_TO")[0]?.name || "N/A";
  const directReports = uniqueNodes(context.incoming("REPORTS_TO"));
  const jd = context.outgoing("LINKED_TO_JD")[0]?.name || "N/A";
  const skills = uniqueNodes(context.outgoing("HAS_SKILL"));
  const topics = uniqueNodes(context.outgoing("OWNS_TOPIC"));
  const systems = uniqueNodes(context.outgoing("KNOWS_SYSTEM"));
  const repos = uniqueNodes(context.outgoing("CONTRIBUTED_TO_REPOSITORY"));
  const tickets = uniqueNodes(context.outgoing("WORKED_ON_TICKET"));
  const prs = uniqueNodes(context.outgoing("OPENED_PULL_REQUEST"));

  return [
    renderKvSection("Profile Snapshot", [
      { label: "Role", value: role },
      { label: "Team", value: team },
      { label: "Country", value: country },
      { label: "Manager", value: manager },
      { label: "Job Description", value: jd },
      { label: "Direct Reports", value: String(directReports.length) }
    ]),
    renderTokenSection("Skill Focus", skills.map((item) => item.name)),
    renderTokenSection("Topics Owned", topics.map((item) => item.name)),
    renderTokenSection("Systems Known", systems.map((item) => item.name)),
    renderTokenSection("School MVP Activity", [
      ...repos.map((item) => `Repo: ${item.name}`),
      ...prs.map((item) => `PR: ${item.name}`),
      ...tickets.map((item) => `Ticket: ${item.name}`)
    ]),
    renderNeighborSection("Connected Nodes", context.related)
  ];
}

function buildRoleSections(node, context) {
  const department = context.outgoing("BELONGS_TO_DEPARTMENT")[0]?.name || "N/A";
  const jd = context.outgoing("DESCRIBED_BY")[0];
  const people = uniqueNodes(context.incoming("HAS_ROLE"));
  const jdSkills = jd ? uniqueNodes(buildNodeContext(jd.id).outgoing("REQUIRES_SKILL")) : [];

  return [
    renderKvSection("Role Snapshot", [
      { label: "Department", value: department },
      { label: "Assigned People", value: String(people.length) },
      { label: "Job Description", value: jd?.name || "N/A" }
    ]),
    renderTokenSection("People In Role", people.map((item) => item.name)),
    renderTokenSection("Baseline Skills", jdSkills.map((item) => item.name)),
    renderNeighborSection("Connected Nodes", context.related)
  ];
}

function buildRepositorySections(node, context) {
  const contributors = uniqueNodes(context.incoming("CONTRIBUTED_TO_REPOSITORY"));
  const commits = uniqueNodes(context.incoming("IN_REPOSITORY").filter((item) => item.label === "Commit"));
  const prs = uniqueNodes(context.incoming("IN_REPOSITORY").filter((item) => item.label === "PullRequest"));
  const technologies = uniqueNodes(context.outgoing("USES_TECHNOLOGY"));

  return [
    renderKvSection("Repository Snapshot", [
      { label: "Language", value: node.language || "N/A" },
      { label: "Stars", value: String(node.stars || 0) },
      { label: "Forks", value: String(node.forks || 0) },
      { label: "Contributors", value: String(contributors.length) }
    ]),
    renderTokenSection("Contributors", contributors.map((item) => item.name)),
    renderTokenSection("Technology Hints", technologies.map((item) => item.name)),
    renderTokenSection("Activity Sample", [
      ...prs.slice(0, 6).map((item) => item.name),
      ...commits.slice(0, 6).map((item) => item.name)
    ]),
    renderNeighborSection("Connected Nodes", context.related)
  ];
}

function buildJiraSections(node, context) {
  const assignees = uniqueNodes(context.incoming("WORKED_ON_TICKET"));
  const reporters = uniqueNodes(context.incoming("REPORTED_TICKET"));
  const commenters = uniqueNodes(context.incoming("COMMENTED_ON_TICKET"));
  const systems = uniqueNodes(context.outgoing("IMPACTS_SYSTEM"));
  const topics = uniqueNodes(context.outgoing("TAGGED_WITH_TOPIC"));
  const skills = uniqueNodes(context.outgoing("REQUIRES_SKILL"));
  const project = context.outgoing("BELONGS_TO_PROJECT")[0]?.name || "N/A";

  return [
    renderKvSection("Issue Snapshot", [
      { label: "Project", value: project },
      { label: "Status", value: node.status || "N/A" },
      { label: "Priority", value: node.priority || "N/A" },
      { label: "Country", value: node.country || "N/A" }
    ]),
    renderTokenSection("Assignee / Reporter", [
      ...assignees.map((item) => `Assignee: ${item.name}`),
      ...reporters.map((item) => `Reporter: ${item.name}`),
      ...commenters.map((item) => `Commenter: ${item.name}`)
    ]),
    renderTokenSection("Linked Systems", systems.map((item) => item.name)),
    renderTokenSection("Tags and Skills", [...topics.map((item) => item.name), ...skills.map((item) => item.name)]),
    renderNeighborSection("Connected Nodes", context.related)
  ];
}

function buildGenericSections(node, context) {
  const fields = Object.entries(node)
    .filter(([key]) => !["id", "label", "name"].includes(key))
    .map(([key, value]) => ({ label: formatKey(key), value: formatValue(value) }));

  return [
    renderKvSection("Node Snapshot", fields.length ? fields : [{ label: "Info", value: "No additional properties" }]),
    renderNeighborSection("Connected Nodes", context.related)
  ];
}

function renderKvSection(title, items) {
  return `
    <section class="detail-section">
      <h3 class="detail-section-title">${escapeHtml(title)}</h3>
      <div class="kv-grid">
        ${items.map((item) => `
          <div class="kv-card">
            <span>${escapeHtml(item.label)}</span>
            <strong>${escapeHtml(item.value)}</strong>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function renderTokenSection(title, values) {
  const cleanValues = values.filter(Boolean).slice(0, 16);
  if (!cleanValues.length) {
    return "";
  }
  return `
    <section class="detail-section">
      <h3 class="detail-section-title">${escapeHtml(title)}</h3>
      <ul class="token-list">
        ${cleanValues.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}
      </ul>
    </section>
  `;
}

function renderNeighborSection(title, related) {
  const rows = related
    .slice()
    .sort((a, b) => a.rel.type.localeCompare(b.rel.type) || a.other.name.localeCompare(b.other.name))
    .slice(0, 18);

  if (!rows.length) {
    return "";
  }

  return `
    <section class="detail-section">
      <h3 class="detail-section-title">${escapeHtml(title)}</h3>
      <ul class="neighbors">
        ${rows.map((item) => `
          <li>
            <span class="neighbor-type">${escapeHtml(item.rel.type)}</span>
            <button class="text-button" data-action="jump-node" data-node-id="${escapeHtml(item.other.id)}">${escapeHtml(item.other.name)}</button>
            <span class="neighbor-label">(${escapeHtml(item.other.label)})</span>
          </li>
        `).join("")}
      </ul>
    </section>
  `;
}

function renderChip(chip) {
  return `<span class="detail-chip">${escapeHtml(chip.label)}: ${escapeHtml(chip.value)}</span>`;
}

function renderEmptyDetails() {
  el.selectionEmpty.classList.remove("hidden");
  el.selectionDetails.classList.add("hidden");
  el.detailsBody.innerHTML = "";
}

function applyAdaptiveCanvasHeight(nodeCount) {
  state.programmaticHeightSync = true;

  if (state.manualNetworkHeight) {
    const nextHeight = clampGraphHeight(state.manualNetworkHeight);
    state.appliedNetworkHeight = nextHeight;
    if (el.networkWrap) {
      el.networkWrap.style.flex = "0 0 auto";
      el.networkWrap.style.height = `${nextHeight}px`;
    }
    el.network.style.height = `${nextHeight}px`;
  } else {
    state.appliedNetworkHeight = null;
    if (el.networkWrap) {
      el.networkWrap.style.flex = "";
      el.networkWrap.style.height = "";
    }
    el.network.style.height = "";
  }
  requestAnimationFrame(() => {
    state.programmaticHeightSync = false;
  });
}

function setupNetworkResizeObserver() {
  if (!("ResizeObserver" in window) || !el.networkWrap) {
    return;
  }

  const onResize = debounce((entries) => {
    const entry = entries[0];
    if (!entry) {
      return;
    }
    const nextHeight = Math.round(entry.contentRect.height);
    if (!state.programmaticHeightSync && Math.abs(nextHeight - (state.appliedNetworkHeight ?? nextHeight)) > 6) {
      state.manualNetworkHeight = nextHeight;
    }
    syncNetworkSize();
  }, 80);

  state.resizeObserver?.disconnect?.();
  state.resizeObserver = new ResizeObserver(onResize);
  state.resizeObserver.observe(el.networkWrap);
}

function setupGraphResizeHandle() {
  if (!el.graphResizeHandle || !el.network) {
    return;
  }

  el.graphResizeHandle.addEventListener("pointerdown", (event) => {
    event.preventDefault();

    const startY = event.clientY;
    const startHeight = el.network.getBoundingClientRect().height;
    document.body.classList.add("is-resizing-graph");
    el.graphResizeHandle.setPointerCapture?.(event.pointerId);

    const onPointerMove = (moveEvent) => {
      const delta = moveEvent.clientY - startY;
      const nextHeight = clampGraphHeight(startHeight + delta);
      state.manualNetworkHeight = nextHeight;
      state.appliedNetworkHeight = nextHeight;
      state.programmaticHeightSync = true;
      if (el.networkWrap) {
        el.networkWrap.style.flex = "0 0 auto";
        el.networkWrap.style.height = `${nextHeight}px`;
      }
      el.network.style.height = `${nextHeight}px`;
      syncNetworkSize();
    };

    const stopResize = () => {
      document.body.classList.remove("is-resizing-graph");
      state.programmaticHeightSync = false;
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopResize);
      window.removeEventListener("pointercancel", stopResize);
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopResize);
    window.addEventListener("pointercancel", stopResize);
  });
}

function clampGraphHeight(height) {
  const minHeight = 290;
  const maxHeight = Math.max(minHeight, Math.round(window.innerHeight * 0.92));
  return Math.min(maxHeight, Math.max(minHeight, Math.round(height)));
}

function applyGraphResizeHandleStyles() {
  if (!el.graphResizeHandle) {
    return;
  }

  Object.assign(el.graphResizeHandle.style, {
    position: "absolute",
    right: "10px",
    bottom: "10px",
    width: "24px",
    height: "24px",
    borderRadius: "8px",
    background: "linear-gradient(135deg, transparent 0 44%, rgba(20, 95, 116, 0.28) 44% 52%, transparent 52% 100%), linear-gradient(135deg, transparent 0 64%, rgba(20, 95, 116, 0.48) 64% 72%, transparent 72% 100%), rgba(255, 250, 242, 0.92)",
    boxShadow: "0 4px 12px rgba(24, 50, 71, 0.16)",
    cursor: "ns-resize",
    zIndex: "8",
    touchAction: "none",
    display: "block"
  });
}

function syncNetworkSize() {
  if (!state.network || !el.network) {
    return;
  }
  const width = Math.max(320, Math.round(el.network.clientWidth || 0));
  const height = Math.max(260, Math.round(el.network.clientHeight || 0));
  state.network.setOptions({
    width: `${width}px`,
    height: `${height}px`
  });
  state.network.setSize(`${width}px`, `${height}px`);
  forceCanvasDimensions(width, height);
  state.network.redraw();
}

function forceCanvasDimensions(width, height) {
  const wrapper = el.network.querySelector(".vis-network");
  const canvas = el.network.querySelector("canvas");
  const dpr = window.devicePixelRatio || 1;

  if (wrapper) {
    wrapper.style.width = `${width}px`;
    wrapper.style.height = `${height}px`;
    wrapper.style.minHeight = `${height}px`;
  }

  if (canvas) {
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    canvas.style.minHeight = `${height}px`;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
  }
}

function findDefaultFocusNodeId() {
  const people = state.raw.nodes.filter((node) => node.label === "Person");
  if (!people.length) {
    return state.raw.nodes[0]?.id || null;
  }

  const outgoingReporters = new Set(
    state.raw.relationships
      .filter((rel) => rel.type === "REPORTS_TO")
      .map((rel) => rel.start)
  );

  const rootExecutive = people.find((node) => !outgoingReporters.has(node.id));
  return rootExecutive?.id || people[0].id;
}

function findBestFocusNodeIdForPreset(presetKey) {
  const preset = PRESETS[presetKey];
  const allowedLabels = new Set(preset.labels || [...state.labelCounts.keys()]);
  const allowedRelationships = new Set(preset.relationships || [...state.relationshipCounts.keys()]);
  let bestId = null;
  let bestScore = -1;

  for (const node of state.raw.nodes) {
    if (!allowedLabels.has(node.label)) {
      continue;
    }
    const score = countPresetConnections(node.id, allowedLabels, allowedRelationships);
    if (score > bestScore) {
      bestId = node.id;
      bestScore = score;
    }
  }
  return bestId;
}

function nodeMatchesActivePreset(nodeId) {
  const node = state.nodeMap.get(nodeId);
  if (!node || !state.labelFilter.has(node.label)) {
    return false;
  }
  return countPresetConnections(nodeId, state.labelFilter, state.relationshipFilter) > 0 || state.activePreset === "full";
}

function countPresetConnections(nodeId, allowedLabels, allowedRelationships) {
  let score = 0;
  const adjacent = state.adjacency.get(nodeId) || [];
  for (const rel of adjacent) {
    if (!allowedRelationships.has(rel.type)) {
      continue;
    }
    const otherId = rel.start === nodeId ? rel.end : rel.start;
    const other = state.nodeMap.get(otherId);
    if (other && allowedLabels.has(other.label)) {
      score += 1;
    }
  }
  return score;
}

function getColor(label) {
  return LABEL_COLORS[label] || "#78909c";
}

function getNodeSize(label) {
  switch (label) {
    case "Person":
      return 22;
    case "Role":
      return 20;
    case "Repository":
    case "JiraIssue":
      return 18;
    case "Commit":
    case "PullRequest":
      return 15;
    case "Skill":
    case "Topic":
    case "System":
      return 16;
    default:
      return 15;
  }
}

function toggleSetValue(set, value, shouldInclude) {
  if (shouldInclude) {
    set.add(value);
  } else {
    set.delete(value);
  }
}

function uniqueNodes(items) {
  const seen = new Map();
  for (const item of items) {
    if (item && !seen.has(item.id)) {
      seen.set(item.id, item);
    }
  }
  return [...seen.values()];
}

function dedupeEdges(edges) {
  const seen = new Set();
  const result = [];
  for (const rel of edges) {
    const key = `${rel.start}|${rel.type}|${rel.end}`;
    if (!seen.has(key)) {
      seen.add(key);
      result.push(rel);
    }
  }
  return result;
}

function sortByCountThenName(a, b) {
  if (b[1] !== a[1]) {
    return b[1] - a[1];
  }
  return a[0].localeCompare(b[0]);
}

function formatKey(value) {
  return value.replaceAll("_", " ");
}

function formatValue(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  return String(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function debounce(fn, waitMs) {
  let timeoutId = null;
  return (...args) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => fn(...args), waitMs);
  };
}

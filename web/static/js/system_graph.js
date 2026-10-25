/**
 * Shomei Connected-System Interactive Topology Canvas
 * Single authoritative source of truth for the 7 distributed store nodes:
 * 1. Primary Database (primary_db)
 * 2. Database Replicas (replicas)
 * 3. Cache (cache)
 * 4. Search Index (search_index)
 * 5. Support Systems (support_systems)
 * 6. Logs (logs)
 * 7. Exports & Backups (exports_backups)
 *
 * Features:
 * - Real interactive canvas: hover/click highlights node & connected edges, docks details into inspector.
 * - Dynamic store count calculated from authoritative dataset.
 * - Filter bar highlights target store and incident edges, dims unconnected elements, and resets cleanly.
 * - Docked inspector with useful empty state before a node is selected.
 * - Guided deletion request flow through Discovery → Investigation → Remediation → Verification.
 * - Responsive layout, touch support, and prefers-reduced-motion compliance.
 */

(function () {
  const canvas = document.getElementById('system-graph-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const inspectorEl = document.getElementById('system-inspector-card');
  const emptyStateEl = document.getElementById('inspector-empty-state');
  const detailsStateEl = document.getElementById('inspector-details-state');

  const inspectorTitle = document.getElementById('inspector-title');
  const inspectorType = document.getElementById('inspector-type');
  const inspectorStatus = document.getElementById('inspector-status');
  const inspectorFinding = document.getElementById('inspector-finding');
  const inspectorRelation = document.getElementById('inspector-relation');
  const inspectorAction = document.getElementById('inspector-action');
  const btnTracePlay = document.getElementById('btn-trace-play');
  const tracePhaseBtns = document.querySelectorAll('.trace-phase-btn');
  const traceStageText = document.getElementById('trace-stage-text');
  const tracePacketIndicator = document.getElementById('trace-packet-indicator');

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let width = 0;
  let height = 0;
  let dpr = window.devicePixelRatio || 1;
  let hoveredNode = null;
  let selectedNode = null;
  let activeFilterId = null; // null or store id (e.g. 'logs', 'exports_backups')
  let animFrameId = null;

  // Guided Deletion Request Simulation State
  let isPlayingTrace = false;
  let currentTracePhase = 1; // 1: Discovery, 2: Investigation, 3: Remediation, 4: Verification
  let traceTimer = null;
  let tracePacket = {
    active: true,
    progress: 0,
    fromNode: 'primary_db',
    toNode: 'replicas',
    speed: 0.012
  };

  // Single Authoritative List of the 7 System Stores
  const nodes = [
    {
      id: 'primary_db',
      label: 'Primary Database',
      short: 'Primary Database',
      category: 'PostgreSQL / Aurora Core',
      xRatio: 0.15,
      yRatio: 0.44,
      radius: 26,
      status: 'VERIFIED_ABSENT',
      statusText: 'PURGED ON REQUEST',
      finding: 'Primary account record acc_05 and credentials deleted at requested_at.',
      relation: 'Initial deletion target where application cascade or soft-delete flag executes.',
      action: 'Rule 1: Primary erasure verified via in-memory SQLite schema snapshot.',
      color: '#15803D'
    },
    {
      id: 'replicas',
      label: 'Database Replicas',
      short: 'Database Replicas',
      category: 'Multi-Region Read Replica',
      xRatio: 0.38,
      yRatio: 0.18,
      radius: 26,
      status: 'REPLICATION_DRIFT',
      statusText: 'REPLICATION DRIFT',
      finding: 'Asynchronous binlog lag of 340s caused deletion transaction to miss failover snapshot.',
      relation: 'Stale read queries continue to serve deleted customer PII to active regional services.',
      action: 'Rule 2: Direct tombstone sync required across all read-replicas before completion.',
      color: '#DC2626'
    },
    {
      id: 'cache',
      label: 'Cache',
      short: 'Cache',
      category: 'Redis / Memcached In-Memory',
      xRatio: 0.20,
      yRatio: 0.78,
      radius: 26,
      status: 'GHOST_SESSION',
      statusText: 'SESSION GHOST',
      finding: 'Serialized user session token and JWT claims persist until 24h TTL expiration.',
      relation: 'Cached credentials allow unauthorized post-deletion session hijacking if un-evicted.',
      action: 'Rule 3: Deterministic pattern key purge (user:acc_05:*) executed.',
      color: '#EA580C'
    },
    {
      id: 'search_index',
      label: 'Search Index',
      short: 'Search Index',
      category: 'Elasticsearch / OpenSearch Cluster',
      xRatio: 0.46,
      yRatio: 0.48,
      radius: 26,
      status: 'GHOST_RECORD',
      statusText: 'AUTOCOMPLETE LEAK',
      finding: 'User email, telephone, and full name continue to match inverted index prefixes.',
      relation: 'Public directory searches still return deleted customer identifiers.',
      action: 'Rule 4: Inverted index document eviction and cluster sync enforced.',
      color: '#DC2626'
    },
    {
      id: 'support_systems',
      label: 'Support Systems',
      short: 'Support Systems',
      category: 'Zendesk / Salesforce CRM',
      xRatio: 0.48,
      yRatio: 0.80,
      radius: 26,
      status: 'ORPHAN_TICKETS',
      statusText: 'ORPHAN TICKETS PERSIST',
      finding: 'Historical customer service transcripts and file attachments remain in CRM storage.',
      relation: 'Third-party SaaS integrations frequently escape internal database deletion cascades.',
      action: 'Rule 11: Webhook dispatch to CRM API to purge ticket threads and customer profiles.',
      color: '#EA580C'
    },
    {
      id: 'logs',
      label: 'Logs',
      short: 'Logs',
      category: 'CloudWatch / Datadog Audit Trail',
      xRatio: 0.76,
      yRatio: 0.22,
      radius: 26,
      status: 'UNMASKED_PII',
      statusText: 'UNMASKED PII IN LOGS',
      finding: 'Raw query parameters and API payloads retain plain-text customer phone and IP.',
      relation: 'Statutory compliance requires preserving access audit trails while redacting PII.',
      action: 'Rule 8: Irreversible cryptographic pseudonymization applied to audit events.',
      color: '#D97706'
    },
    {
      id: 'exports_backups',
      label: 'Exports & Backups',
      short: 'Exports & Backups',
      category: 'S3 Glacier Immutable Archive',
      xRatio: 0.78,
      yRatio: 0.66,
      radius: 26,
      status: 'RESTORE_HAZARD',
      statusText: 'RESTORE HAZARD',
      finding: 'Immutable disaster recovery snapshots contain un-tombstoned user row copies.',
      relation: 'Routine database recovery would restore purged accounts without automated restore blocks.',
      action: 'Rule 14: Differential mask and automated restore-block registered in registry.',
      color: '#D97706'
    }
  ];

  // Interconnected Topology Edges
  const edges = [
    { from: 'primary_db', to: 'replicas', label: 'Replication Stream', phase: 1 },
    { from: 'primary_db', to: 'cache', label: 'Cache Invalidation', phase: 1 },
    { from: 'primary_db', to: 'search_index', label: 'CDC Pipeline', phase: 2 },
    { from: 'primary_db', to: 'logs', label: 'Audit Trail', phase: 2 },
    { from: 'cache', to: 'support_systems', label: 'Session Context', phase: 3 },
    { from: 'search_index', to: 'support_systems', label: 'Customer Index', phase: 3 },
    { from: 'primary_db', to: 'exports_backups', label: 'Nightly Snapshot', phase: 4 },
    { from: 'replicas', to: 'search_index', label: 'Failover Sync', phase: 4 }
  ];

  // Guided Stage Definitions
  const traceStages = {
    1: {
      name: 'Discovery',
      banner: 'Phase 1 · Discovery: Scanning Primary database, Replicas, and Cache for user identifier graph.',
      fromNode: 'primary_db',
      toNode: 'replicas',
      inspectorNode: 'replicas',
      indicator: '● DISCOVERY: Identifiers mapped across SQL and memory'
    },
    2: {
      name: 'Investigation',
      banner: 'Phase 2 · Investigation: Probing Search index, Logs, and Support systems for residual PII.',
      fromNode: 'primary_db',
      toNode: 'logs',
      inspectorNode: 'search_index',
      indicator: '● INVESTIGATION: Ghost autocomplete and unmasked logs detected'
    },
    3: {
      name: 'Remediation',
      banner: 'Phase 3 · Remediation: Formulating ordered sequence (Pause ETL ➔ Evict Cache & Index ➔ Redact CRM).',
      fromNode: 'search_index',
      toNode: 'support_systems',
      inspectorNode: 'support_systems',
      indicator: '● REMEDIATION: Synthesizing atomic purge sequence'
    },
    4: {
      name: 'Verification',
      banner: 'Phase 4 · Verification: Cross-verifying all stores, establishing restore-blocks on Backups.',
      fromNode: 'primary_db',
      toNode: 'exports_backups',
      inspectorNode: 'exports_backups',
      indicator: '● VERIFICATION: Mathematical proof of absence registered'
    }
  };

  // Sync dynamic node counts
  const storeCountEl = document.getElementById('topology-store-count');
  if (storeCountEl) storeCountEl.textContent = nodes.length;

  const inspectorCountBadge = document.getElementById('inspector-store-count-badge');
  if (inspectorCountBadge) inspectorCountBadge.textContent = nodes.length;

  const allStoresBtn = document.querySelector('.system-node-btn[data-node-id="all"]');
  if (allStoresBtn) allStoresBtn.textContent = `All Stores (${nodes.length})`;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
  }

  function getNodePos(node) {
    return {
      x: node.xRatio * width,
      y: node.yRatio * height
    };
  }

  function getNodeById(id) {
    return nodes.find((n) => n.id === id);
  }

  function isEdgeConnectedToNode(edge, nodeId) {
    return edge.from === nodeId || edge.to === nodeId;
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    // 1. Draw Connection Lines (Edges)
    edges.forEach((edge) => {
      const fromNode = getNodeById(edge.from);
      const toNode = getNodeById(edge.to);
      if (!fromNode || !toNode) return;

      const p1 = getNodePos(fromNode);
      const p2 = getNodePos(toNode);

      const isConnectedToHovered =
        hoveredNode && (hoveredNode.id === edge.from || hoveredNode.id === edge.to);
      const isConnectedToSelected =
        selectedNode && (selectedNode.id === edge.from || selectedNode.id === edge.to);
      const isConnectedToFilter =
        activeFilterId && (activeFilterId === edge.from || activeFilterId === edge.to);
      const isPhaseEdge = isPlayingTrace && edge.phase === currentTracePhase;

      const isHighlighted = isConnectedToHovered || isConnectedToSelected || isConnectedToFilter || isPhaseEdge;

      // Dim edges that are not connected when a filter or selection is active
      let strokeColor = isDark ? 'rgba(255, 255, 255, 0.16)' : 'rgba(215, 212, 205, 0.55)';
      let lineWidth = 1.4;

      if (isHighlighted) {
        strokeColor = isPhaseEdge
          ? (isDark ? 'rgba(74, 222, 128, 0.95)' : 'rgba(34, 197, 94, 0.95)')
          : (isDark ? 'rgba(74, 222, 128, 0.9)' : 'rgba(22, 163, 74, 0.85)');
        lineWidth = isPhaseEdge ? 3.0 : 2.4;
        ctx.setLineDash(isPhaseEdge ? [6, 4] : []);
        ctx.shadowColor = 'rgba(74, 222, 128, 0.7)';
        ctx.shadowBlur = 8;
      } else if (activeFilterId) {
        strokeColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(215, 212, 205, 0.18)';
        lineWidth = 1.0;
        ctx.setLineDash([]);
        ctx.shadowBlur = 0;
      } else {
        ctx.setLineDash([]);
        ctx.shadowBlur = 0;
      }

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = lineWidth;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.shadowBlur = 0;
    });

    // 2. Draw Moving Trace Packet (Guided Deletion Request Token)
    if (tracePacket.active) {
      const fromN = getNodeById(tracePacket.fromNode);
      const toN = getNodeById(tracePacket.toNode);
      if (fromN && toN) {
        const p1 = getNodePos(fromN);
        const p2 = getNodePos(toN);
        const px = p1.x + (p2.x - p1.x) * tracePacket.progress;
        const py = p1.y + (p2.y - p1.y) * tracePacket.progress;

        // Radiant glow
        const glow = ctx.createRadialGradient(px, py, 0, px, py, 14);
        glow.addColorStop(0, 'rgba(255, 255, 255, 1)');
        glow.addColorStop(0.3, 'rgba(74, 222, 128, 0.9)');
        glow.addColorStop(1, 'rgba(22, 163, 74, 0)');
        ctx.beginPath();
        ctx.arc(px, py, 14, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        // Packet core
        ctx.beginPath();
        ctx.arc(px, py, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = '#FFFFFF';
        ctx.shadowColor = '#15803D';
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;

        if (!prefersReducedMotion) {
          tracePacket.progress += tracePacket.speed;
          if (tracePacket.progress >= 1) {
            tracePacket.progress = 0;
            if (isPlayingTrace) {
              advancePacketHop();
            }
          }
        }
      }
    }

    // 3. Draw Nodes (All 7 Stores)
    nodes.forEach((node) => {
      const pos = getNodePos(node);
      const isHovered = hoveredNode && hoveredNode.id === node.id;
      const isSelected = selectedNode && selectedNode.id === node.id;
      const isFilterTarget = activeFilterId && activeFilterId === node.id;
      const isFilterNeighbor =
        activeFilterId &&
        edges.some((e) => (e.from === activeFilterId && e.to === node.id) || (e.to === activeFilterId && e.from === node.id));
      const isPhaseTarget = isPlayingTrace && traceStages[currentTracePhase]?.inspectorNode === node.id;

      const active = isHovered || isSelected || isFilterTarget || isPhaseTarget;

      // Handle opacity when a filter is active
      let nodeAlpha = 1.0;
      if (activeFilterId && !isFilterTarget && !isFilterNeighbor) {
        nodeAlpha = 0.32;
      }
      ctx.globalAlpha = nodeAlpha;

      // Glow halo if active
      if (active) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, node.radius + 12, 0, Math.PI * 2);
        ctx.fillStyle = node.status === 'VERIFIED_ABSENT' ? 'rgba(22, 163, 74, 0.20)' : 'rgba(220, 38, 38, 0.20)';
        ctx.fill();
      }

      // Outer circle (adapts cleanly to light/dark surfaces)
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, node.radius, 0, Math.PI * 2);
      ctx.fillStyle = isDark ? '#1C1C1A' : '#FFFFFF';
      ctx.shadowColor = active ? (isDark ? 'rgba(0, 0, 0, 0.5)' : 'rgba(0, 0, 0, 0.18)') : (isDark ? 'rgba(0, 0, 0, 0.3)' : 'rgba(0, 0, 0, 0.06)');
      ctx.shadowBlur = active ? 14 : 6;
      ctx.shadowOffsetY = 3;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.shadowOffsetY = 0;

      // Border ring
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, node.radius, 0, Math.PI * 2);
      ctx.strokeStyle = active ? node.color : (isDark ? 'rgba(255, 255, 255, 0.16)' : '#E5E2DC');
      ctx.lineWidth = active ? 3.2 : 1.8;
      ctx.stroke();

      // Status indicator pip inside
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, active ? 8.5 : 6.5, 0, Math.PI * 2);
      ctx.fillStyle = isDark && node.status === 'VERIFIED_ABSENT' ? '#4ADE80' : node.color;
      ctx.fill();

      // Node label
      ctx.font = active ? '600 12.5px "Plus Jakarta Sans", sans-serif' : '500 12px "Plus Jakarta Sans", sans-serif';
      ctx.fillStyle = active ? (isDark ? '#F5F5F3' : '#181816') : (isDark ? '#B4B3AC' : '#575753');
      ctx.textAlign = 'center';
      ctx.fillText(node.short, pos.x, pos.y + node.radius + 17);

      // Node status subtext
      ctx.font = '700 8.5px "JetBrains Mono", monospace';
      ctx.fillStyle = node.status === 'VERIFIED_ABSENT' ? (isDark ? '#4ADE80' : '#15803D') : (isDark ? '#F87171' : '#991B1B');
      ctx.fillText(node.statusText, pos.x, pos.y + node.radius + 29);

      ctx.globalAlpha = 1.0;
    });

    animFrameId = requestAnimationFrame(draw);
  }

  function advancePacketHop() {
    const stage = traceStages[currentTracePhase];
    if (stage) {
      tracePacket.fromNode = stage.fromNode;
      tracePacket.toNode = stage.toNode;
    }
  }

  function updateInspector(node) {
    if (!inspectorEl) return;

    if (!node) {
      if (emptyStateEl) emptyStateEl.style.display = 'flex';
      if (detailsStateEl) detailsStateEl.style.display = 'none';
      return;
    }

    if (emptyStateEl) emptyStateEl.style.display = 'none';
    if (detailsStateEl) detailsStateEl.style.display = 'block';

    if (inspectorTitle) inspectorTitle.textContent = node.label;
    if (inspectorType) inspectorType.textContent = node.category;
    if (inspectorStatus) {
      inspectorStatus.textContent = node.statusText;
      inspectorStatus.className = node.status === 'VERIFIED_ABSENT' ? 'status-pill-ok' : 'status-pill-alert';
    }
    if (inspectorFinding) inspectorFinding.textContent = node.finding;
    if (inspectorRelation) inspectorRelation.textContent = node.relation;
    if (inspectorAction) inspectorAction.textContent = node.action;
  }

  // Update filter buttons UI active state
  function updateFilterButtonsUI() {
    const filterBtns = document.querySelectorAll('#topology-filter-bar .system-node-btn');
    filterBtns.forEach((btn) => {
      const btnId = btn.dataset.nodeId;
      if (!activeFilterId || activeFilterId === 'all') {
        btn.classList.toggle('active', btnId === 'all');
      } else {
        btn.classList.toggle('active', btnId === activeFilterId);
      }
    });
  }

  // Set filter by store ID (or 'all' / reset)
  function setStoreFilter(storeId) {
    if (storeId === 'all' || !storeId || (activeFilterId === storeId && selectedNode?.id === storeId)) {
      activeFilterId = null;
      selectedNode = null;
      updateInspector(null);
    } else {
      activeFilterId = storeId;
      const target = getNodeById(storeId);
      selectedNode = target;
      updateInspector(target);
      if (isPlayingTrace) toggleTracePlay();
    }
    updateFilterButtonsUI();
  }

  // Set Guided Phase
  function setTracePhase(phaseNum) {
    currentTracePhase = phaseNum;
    const info = traceStages[phaseNum];
    if (!info) return;

    tracePhaseBtns.forEach((btn) => {
      btn.classList.toggle('active', parseInt(btn.dataset.phase, 10) === phaseNum);
      if (parseInt(btn.dataset.phase, 10) === phaseNum) {
        btn.style.background = 'var(--text-primary)';
        btn.style.color = '#FFF';
      } else {
        btn.style.background = 'transparent';
        btn.style.color = 'var(--text-primary)';
      }
    });

    if (traceStageText) {
      traceStageText.innerHTML = `<strong style="color: var(--text-primary); font-family: var(--font-mono);">${info.name.toUpperCase()}:</strong> ${info.banner}`;
    }
    if (tracePacketIndicator) {
      tracePacketIndicator.textContent = info.indicator;
    }

    tracePacket.fromNode = info.fromNode;
    tracePacket.toNode = info.toNode;
    tracePacket.progress = 0;

    const targetNode = getNodeById(info.inspectorNode);
    if (targetNode) {
      selectedNode = targetNode;
      activeFilterId = null;
      updateFilterButtonsUI();
      updateInspector(targetNode);
    }
  }

  // Play / Pause Guided Animation
  function toggleTracePlay() {
    isPlayingTrace = !isPlayingTrace;
    if (isPlayingTrace) {
      if (btnTracePlay) btnTracePlay.textContent = '⏸ Pause Trace';
      runTraceCycle();
    } else {
      if (btnTracePlay) btnTracePlay.textContent = '▶ Run Guided Trace';
      if (traceTimer) clearInterval(traceTimer);
    }
  }

  function runTraceCycle() {
    if (traceTimer) clearInterval(traceTimer);
    traceTimer = setInterval(() => {
      if (!isPlayingTrace) return;
      currentTracePhase = (currentTracePhase % 4) + 1;
      setTracePhase(currentTracePhase);
    }, 4500);
  }

  // Mouse Interaction on Canvas
  function getCanvasCoords(e) {
    const rect = canvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: clientX - rect.left,
      y: clientY - rect.top
    };
  }

  function findHitNode(x, y) {
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const pos = getNodePos(node);
      const dist = Math.hypot(x - pos.x, y - pos.y);
      if (dist <= node.radius + 12) {
        return node;
      }
    }
    return null;
  }

  canvas.addEventListener('mousemove', (e) => {
    const coords = getCanvasCoords(e);
    const hit = findHitNode(coords.x, coords.y);

    if (hit !== hoveredNode) {
      hoveredNode = hit;
      canvas.style.cursor = hit ? 'pointer' : 'default';
      if (hit) {
        updateInspector(hit);
      } else if (selectedNode) {
        updateInspector(selectedNode);
      } else {
        updateInspector(null);
      }
    }
  });

  canvas.addEventListener('mouseleave', () => {
    hoveredNode = null;
    canvas.style.cursor = 'default';
    if (selectedNode) {
      updateInspector(selectedNode);
    } else {
      updateInspector(null);
    }
  });

  canvas.addEventListener('click', (e) => {
    const coords = getCanvasCoords(e);
    const hit = findHitNode(coords.x, coords.y);
    if (hit) {
      setStoreFilter(hit.id);
    } else if (!hoveredNode && selectedNode) {
      // Clicked on empty canvas: deselect and reset to empty state
      setStoreFilter('all');
    }
  });

  // Buttons: Play Trace
  if (btnTracePlay) {
    btnTracePlay.addEventListener('click', toggleTracePlay);
  }

  // Buttons: Trace Steps (1, 2, 3, 4)
  tracePhaseBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (isPlayingTrace) toggleTracePlay();
      setTracePhase(parseInt(btn.dataset.phase, 10));
    });
  });

  // Filter Buttons below Canvas
  const filterBtns = document.querySelectorAll('#topology-filter-bar .system-node-btn');
  filterBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const nid = btn.dataset.nodeId;
      setStoreFilter(nid);
    });
  });

  // Initialize
  window.addEventListener('resize', resize);
  resize();

  // Show empty state before a node is selected, with filter UI reset
  selectedNode = null;
  activeFilterId = null;
  updateInspector(null);
  updateFilterButtonsUI();

  draw();
})();

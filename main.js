/**
 * NEXUS — main.js
 * Simple, dependency-free UI logic. Every rendered value flows through
 * api.js — nothing here invents an operational number.
 */
(function () {
  "use strict";

  /* ------------------------------------------------------------------
   * Small inline icon set (original abstract marks, not vendor logos)
   * ------------------------------------------------------------------ */
  const ICONS = {
    github: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 2C6.48 2 2 6.58 2 12.25c0 4.53 2.87 8.37 6.84 9.73.5.1.68-.22.68-.5 0-.24-.01-1.04-.01-1.88-2.78.62-3.37-1.22-3.37-1.22-.46-1.19-1.11-1.51-1.11-1.51-.91-.64.07-.63.07-.63 1 .07 1.53 1.05 1.53 1.05.89 1.57 2.34 1.12 2.91.85.09-.66.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.06 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.31.1-2.72 0 0 .84-.28 2.75 1.05a9.36 9.36 0 0 1 5 0c1.91-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.46.1 2.72.64.72 1.03 1.63 1.03 2.75 0 3.93-2.35 4.79-4.58 5.05.36.32.68.94.68 1.9 0 1.37-.01 2.47-.01 2.81 0 .28.18.61.69.5A10.26 10.26 0 0 0 22 12.25C22 6.58 17.52 2 12 2Z"/></svg>',
    aws: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M4 15.5c3 2.4 13 2.7 16 0 .3-.3-.1-.7-.4-.5-3.4 2-11.8 1.8-15.1-.2-.3-.2-.7.4-.5.7Zm14.7-.9c.3-1-.7-1.4-1.4-1.1l.1-.2c.3-.5.3-1.1-.7-1.2-.9-.1-2.2.4-3 1v-.4c0-1.4-1.2-1.9-3.1-1.9-1 0-2 .2-2.8.6v1c.9-.4 1.9-.6 2.7-.6 1.1 0 1.7.3 1.7 1v.5c-2.5.3-4.2 1.2-4.2 2.7 0 1.2 1 1.9 2.4 1.9 1 0 1.9-.4 2.5-1 .1.4.3.7.6.9l1.1-.6a1.7 1.7 0 0 1-.3-1v-1.6c.7-.5 1.6-.9 2.3-.8.4 0 .4.3.2.6l-.2.3c-.5.9.4 1.7 1.4 1.2.5-.2.8-.6.7-1.3ZM10.4 15c0 .8-.6 1.4-1.6 1.4-.6 0-1-.3-1-.9 0-.8 1-1.3 2.6-1.5V15Z"/></svg>',
    terraform: '<svg viewBox="0 0 24 24" width="20" height="20"><g fill="currentColor"><path d="M4 4.6 8.8 7.3v5.4L4 10z"/><path d="M9.6 7.3 14.4 4.6v5.4L9.6 12.7z"/><path d="M15.2 10 20 12.7v5.4L15.2 15.4z"/><path d="M9.6 13.3 14.4 16v5.4L9.6 18.7z"/></g></svg>',
    docker: '<svg viewBox="0 0 24 24" width="20" height="20"><g fill="currentColor"><rect x="3" y="11" width="3" height="3" rx="0.5"/><rect x="6.6" y="11" width="3" height="3" rx="0.5"/><rect x="10.2" y="11" width="3" height="3" rx="0.5"/><rect x="6.6" y="7.4" width="3" height="3" rx="0.5"/><rect x="10.2" y="7.4" width="3" height="3" rx="0.5"/><rect x="10.2" y="3.8" width="3" height="3" rx="0.5"/><path d="M2.4 13.6c0 3.6 2.6 5.6 7.4 5.6 5.5 0 9.2-2.6 10.6-7.4.9.1 2.1-.2 2.7-1.1-.7-.8-1.9-.9-2.7-.6-.2-.4-.5-.7-.8-1-1 .6-1.6 1.7-1.5 2.9-2.6 1.1-11.8 1.1-15.7 1.6Z"/></g></svg>',
    kubernetes: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="m12 1.6 8.5 3.1 1.4 9L16 21.4l-8-.1-5.9-7.6 1.4-9L12 1.6Zm0 2.1L5.6 6l-1.1 7 4.7 6h5.6l4.7-6-1.1-7L12 3.7Zm0 3.2 3.6 4.5-1.5 5.4h-4.2l-1.5-5.4L12 6.9Z"/></svg>',
    argocd: '<svg viewBox="0 0 24 24" width="20" height="20"><g fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8.4"/><path d="M12 6.2a5.8 5.8 0 0 1 5.8 5.8" stroke-linecap="round"/><path d="M12 17.8A5.8 5.8 0 0 1 6.2 12" stroke-linecap="round"/></g><circle cx="17.8" cy="12" r="1.3" fill="currentColor"/><circle cx="6.2" cy="12" r="1.3" fill="currentColor"/></svg>',
    prometheus: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 2c-.6 1.8-2.4 3-2.4 5.4 0 1.2.7 2 1.4 2.7-1-.2-2.6-1.4-2.9-3.3C6.6 8.2 6 10 6 11.8 6 16 8.7 19 12 19s6-3 6-7.2c0-2-.7-3.9-2-5.3.1 1.6-.8 2.9-1.7 3.5.5-.9.9-1.9.9-3 0-2.2-1.6-3.4-2.2-5Zm0 9.4c1 0 1.8.8 1.8 1.8 0 .7-.4 1.3-1 1.6.3.3.5.8.5 1.3 0 .9-.8 1.7-1.7 1.7s-1.7-.8-1.7-1.7c0-.5.2-1 .5-1.3-.6-.3-1-.9-1-1.6 0-1 .8-1.8 1.6-1.8Z"/></svg>',
    grafana: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M19.8 10.4a4.6 4.6 0 0 0-.2-1.3 3.9 3.9 0 0 0 .9-3.4 4 4 0 0 0-3.4.9 4.6 4.6 0 0 0-2.4-1 3.9 3.9 0 0 0-2.2-2.9 3.9 3.9 0 0 0-2.2 2.9 4.6 4.6 0 0 0-2.4 1 4 4 0 0 0-3.4-.9 3.9 3.9 0 0 0 .9 3.4 4.6 4.6 0 0 0-.7 2.5c0 4 3.2 7.6 7.3 7.6s7.3-3.4 7.3-7.5a4.6 4.6 0 0 0-.5-1.3Zm-7.3 6.4a5.2 5.2 0 1 1 0-10.4 5.2 5.2 0 0 1 0 10.4Z"/><circle cx="12.5" cy="11.4" r="2.4" fill="currentColor"/></svg>',
    security: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 2 4 5v6c0 5 3.4 8.8 8 10 4.6-1.2 8-5 8-10V5l-8-3Zm0 2.2 6 2.2v4.6c0 3.9-2.6 7-6 8-3.4-1-6-4.1-6-8V6.4l6-2.2Zm-1.1 9.9 4.5-4.5-1.3-1.3-3.2 3.2-1.4-1.4-1.3 1.3 2.7 2.7Z"/></svg>',
    registry: '<svg viewBox="0 0 24 24" width="20" height="20"><g fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="4" width="16" height="5.2" rx="1.2"/><rect x="4" y="10.4" width="16" height="5.2" rx="1.2"/><rect x="4" y="16.8" width="16" height="3.2" rx="1.2"/></g><circle cx="7.2" cy="6.6" r="0.7" fill="currentColor"/><circle cx="7.2" cy="13" r="0.7" fill="currentColor"/></svg>',
    cluster: '<svg viewBox="0 0 24 24" width="18" height="18"><g fill="currentColor"><circle cx="6" cy="6" r="2.4"/><circle cx="18" cy="6" r="2.4"/><circle cx="12" cy="18" r="2.4"/><path d="M6.9 8 11 16l-1.4.9L5.5 8.9Zm10.2 0-3.7 8.9 1.4.9L18.5 8.9Z"/></g></svg>',
    box: '<svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M12 2 20 6.5v11L12 22 4 17.5v-11L12 2Zm0 2.3L6 7.6l6 3.2 6-3.2-6-3.3Zm-7 5.2v8l6 3.4v-8l-6-3.4Zm14 0-6 3.4v8l6-3.4v-8Z"/></svg>',
    pulse: '<svg viewBox="0 0 24 24" width="18" height="18"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M3 12h4l2 7 4-14 2 7h6"/></svg>',
    clock: '<svg viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="8.4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 7.4V12l3.2 2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    grid: '<svg viewBox="0 0 24 24" width="18" height="18"><g fill="currentColor"><rect x="3.5" y="3.5" width="7" height="7" rx="1.4"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.4"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.4"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.4"/></g></svg>',
  };

  function icon(name) { return ICONS[name] || ""; }

  /* ------------------------------------------------------------------
   * Utilities
   * ------------------------------------------------------------------ */
  function el(tag, attrs, html) {
    const node = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach((k) => node.setAttribute(k, attrs[k]));
    if (html !== undefined) node.innerHTML = html;
    return node;
  }

  function timeAgo(iso) {
    const diff = Math.max(0, Date.now() - new Date(iso).getTime());
    const s = Math.floor(diff / 1000);
    if (s < 60) return `${s}s ago`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    return `${h}h ago`;
  }

  function fmtTime(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  }

  function fmtDuration(sec) {
    if (sec < 60) return `${sec}s`;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}m ${s}s`;
  }

  function modePillHtml(mode) {
    const map = {
      demo: ["DEMO DATA", "mode-pill--demo"],
      live: ["LIVE", "mode-pill--live"],
      unavailable: ["UNAVAILABLE", "mode-pill--unavailable"],
      error: ["ERROR", "mode-pill--unavailable"],
    };
    const [label, cls] = map[mode] || map.unavailable;
    return `<span class="mode-pill ${cls}">${label}</span>`;
  }

  function sourceLine(result) {
    const source = result.source || "NEXUS API";
    const updated = result.updatedAt ? ` · Updated ${timeAgo(result.updatedAt)}` : "";
    return `${modePillHtml(result.mode)} <span>${source}</span>${updated}`;
  }

  function renderSource(elementId, result) {
    const node = document.getElementById(elementId);
    if (!node) return;
    node.innerHTML = sourceLine(result);
  }

  const STATUS_TONE = {
    SUCCESS: "green", HEALTHY: "green", SYNCED: "green", RUNNING: "blue",
    QUEUED: "gray", SYNCING: "blue", DEGRADED: "amber", "OUT OF SYNC": "amber",
    WARNING: "amber", MISSING: "amber", FAILED: "red", BLOCKED: "red",
    "ROLLED BACK": "red", CANCELLED: "gray", UNKNOWN: "gray", PASSED: "green",
  };
  function badge(status) {
    const tone = STATUS_TONE[status] || "gray";
    return `<span class="badge badge--${tone}"><span class="status-dot status-dot--${tone}"></span>${status}</span>`;
  }
  const SEV_TONE = { CRITICAL: "red", HIGH: "red", MEDIUM: "amber", LOW: "blue" };
  function sevBadge(sev) {
    const tone = SEV_TONE[sev] || "gray";
    return `<span class="badge badge--${tone}">${sev}</span>`;
  }

  /* ------------------------------------------------------------------
   * Navigation: mobile toggle, smooth scroll, active section highlight
   * ------------------------------------------------------------------ */
  function initNav() {
    const toggle = document.getElementById("nav-toggle");
    const nav = document.getElementById("main-nav");
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    nav.querySelectorAll("a").forEach((a) =>
      a.addEventListener("click", () => {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      })
    );

    const links = Array.from(document.querySelectorAll(".nav-link"));
    const sections = links
      .map((l) => document.getElementById(l.getAttribute("href").slice(1)))
      .filter(Boolean);

    if ("IntersectionObserver" in window && sections.length) {
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            links.forEach((l) => l.classList.remove("is-active"));
            const match = links.find((l) => l.getAttribute("href") === `#${entry.target.id}`);
            if (match) match.classList.add("is-active");
          });
        },
        { rootMargin: "-45% 0px -50% 0px", threshold: 0 }
      );
      sections.forEach((s) => io.observe(s));
    }
  }

  /* ------------------------------------------------------------------
   * Reveal-on-scroll
   * ------------------------------------------------------------------ */
  function initReveal() {
    const items = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      items.forEach((i) => i.classList.add("is-visible"));
      return;
    }
    const io = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    items.forEach((i) => io.observe(i));
  }

  /* ------------------------------------------------------------------
   * Hero architecture graph — SVG topology with slow particle motion
   * ------------------------------------------------------------------ */
  function renderHeroGraph() {
    const host = document.getElementById("hero-graph");
    const W = 560, H = 460, CX = 280, CY = 240;

    const nodes = [
      { key: "aws", label: "AWS", x: CX, y: 46, icon: "aws", tone: "amber" },
      { key: "github", label: "GitHub", x: 96, y: 128, icon: "github", tone: "navy" },
      { key: "terraform", label: "Terraform", x: 464, y: 128, icon: "terraform", tone: "violet" },
      { key: "security", label: "Security", x: 78, y: 260, icon: "security", tone: "blue" },
      { key: "argocd", label: "Argo CD", x: 482, y: 260, icon: "argocd", tone: "cyan" },
      { key: "docker", label: "Docker", x: 118, y: 372, icon: "docker", tone: "blue" },
      { key: "grafana", label: "Grafana", x: 300, y: 420, icon: "grafana", tone: "amber" },
      { key: "prometheus", label: "Prometheus", x: 452, y: 372, icon: "prometheus", tone: "red" },
    ];

    const toneColor = {
      blue: "#2563EB", violet: "#7C3AED", cyan: "#06AED4", green: "#12B76A",
      amber: "#D97706", red: "#E5484D", navy: "#0B1526",
    };

    const edges = nodes.map((n) => ({ from: n, color: toneColor[n.tone] || "#2563EB" }));

    let svg = `<svg class="arch-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="NEXUS topology: GitHub, Terraform, Security, Argo CD, Docker, Grafana, Prometheus connected through Kubernetes to AWS">`;

    // edges (curved paths from each node to center)
    edges.forEach((e, i) => {
      const midX = (e.from.x + CX) / 2 + (i % 2 === 0 ? -18 : 18);
      const midY = (e.from.y + CY) / 2;
      svg += `<path class="arch-edge" id="edge-${e.from.key}" d="M ${e.from.x} ${e.from.y} Q ${midX} ${midY} ${CX} ${CY}" stroke="${e.color}"></path>`;
    });

    // particles (animated along each edge via SMIL)
    edges.forEach((e, i) => {
      const dur = 3.4 + (i % 4) * 0.6;
      svg += `<circle class="arch-particle" fill="${e.color}"><animateMotion dur="${dur}s" repeatCount="indefinite" begin="${i * 0.4}s"><mpath href="#edge-${e.from.key}"/></animateMotion></circle>`;
    });

    // outer nodes
    nodes.forEach((n) => {
      svg += `
        <g transform="translate(${n.x - 34}, ${n.y - 34})">
          <rect class="arch-node-card" x="0" y="0" width="68" height="68" rx="16"></rect>
          <g transform="translate(24,14)" style="color:${toneColor[n.tone]}">${icon(n.icon)}</g>
          <text class="arch-node-label" x="34" y="86" text-anchor="middle">${n.label}</text>
        </g>`;
    });

    // center node — Kubernetes
    svg += `
      <g transform="translate(${CX - 46}, ${CY - 46})">
        <rect class="arch-node-core" x="0" y="0" width="92" height="92" rx="22"></rect>
        <g transform="translate(31,20)" style="color:#fff">${icon("kubernetes")}</g>
        <text class="arch-node-core-label" x="46" y="76" text-anchor="middle">EKS</text>
      </g>`;

    svg += `</svg>`;
    host.innerHTML = svg;
  }

  /* ------------------------------------------------------------------
   * Platform metrics strip
   * ------------------------------------------------------------------ */
  async function renderMetrics() {
    const result = await NexusAPI.getPlatformMetrics();
    const modeEl = document.getElementById("metrics-mode");
    const grid = document.getElementById("metrics-grid");
    const map = { demo: "DEMO DATA", live: "LIVE", unavailable: "UNAVAILABLE", error: "ERROR" };
    modeEl.textContent = map[result.mode] || "UNAVAILABLE";
    modeEl.className = `mode-pill ${result.mode === "live" ? "mode-pill--live" : result.mode === "demo" ? "mode-pill--demo" : "mode-pill--unavailable"}`;

    if (!result.data) {
      grid.innerHTML = `<p class="panel-empty-sub">No platform metrics available.</p>`;
      return;
    }

    const icons = ["pulse", "clock", "clock", "grid"];
    grid.innerHTML = result.data
      .map(
        (m, i) => `
      <div class="metric-item">
        <span class="metric-icon">${icon(icons[i] || "pulse")}</span>
        <div>
          <p class="metric-value" data-countup>${m.value}</p>
          <p class="metric-label">${m.label}</p>
        </div>
      </div>`
      )
      .join("");
  }

  /* ------------------------------------------------------------------
   * Delivery pipeline (static structural content — this describes the
   * platform's own path, not a specific run)
   * ------------------------------------------------------------------ */
  function renderPipelineSteps() {
    const steps = [
      { n: "01", title: "Source", desc: "GitHub — code is committed and reviewed.", tone: "blue" },
      { n: "02", title: "Build", desc: "GitHub Actions compiles and assembles artifacts.", tone: "violet" },
      { n: "03", title: "Test", desc: "Automated test suites run against every change.", tone: "violet" },
      { n: "04", title: "Secure", desc: "Trivy, SAST, dependency and secret scanning gate the build.", tone: "red" },
      { n: "05", title: "Package", desc: "Docker images are built and pushed to Amazon ECR.", tone: "cyan" },
      { n: "06", title: "Provision", desc: "Terraform plans and applies infrastructure on AWS.", tone: "blue" },
      { n: "07", title: "Deploy", desc: "Workloads roll out to Kubernetes on Amazon EKS.", tone: "blue" },
      { n: "08", title: "Sync", desc: "Argo CD reconciles the cluster to the desired Git state.", tone: "green" },
      { n: "09", title: "Observe", desc: "Prometheus, Grafana and Loki watch the running system.", tone: "green" },
    ];
    const host = document.getElementById("pipeline-list");
    host.innerHTML = steps
      .map(
        (s) => `
      <div class="pipe-step" data-tone="${s.tone}">
        <div class="pipe-num">${s.n}</div>
        <div class="pipe-body">
          <p class="pipe-title">${s.title}</p>
          <p class="pipe-desc">${s.desc}</p>
        </div>
      </div>`
      )
      .join("");
  }

  /* ------------------------------------------------------------------
   * Full architecture layer diagram
   * ------------------------------------------------------------------ */
  function renderArchFlow() {
    const layers = [
      { name: "Developer", items: "commit · pull request", ic: "github" },
      { name: "CI/CD", items: "GitHub Actions", ic: "github" },
      { name: "Testing", items: "automated test suites", ic: "pulse" },
      { name: "Security", items: "SAST · Trivy · dependency & secret scan", ic: "security" },
      { name: "Container", items: "Docker build", ic: "docker" },
      { name: "Registry", items: "Amazon ECR", ic: "registry" },
      { name: "Infrastructure", items: "Terraform → AWS", ic: "terraform" },
      { name: "Orchestration", items: "Kubernetes · Amazon EKS", ic: "kubernetes" },
      { name: "GitOps", items: "Argo CD sync", ic: "argocd" },
      { name: "Observability", items: "Prometheus · Grafana · Loki", ic: "prometheus" },
      { name: "Production", items: "running workload", ic: "cluster" },
    ];
    const arrow = `<svg width="16" height="20" viewBox="0 0 16 20"><path d="M8 0v14m0 0-5-5m5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

    const host = document.getElementById("arch-flow");
    host.innerHTML = layers
      .map(
        (l, i) => `
      <div class="arch-layer">
        <span class="arch-layer-dot">${icon(l.ic)}</span>
        <div style="flex:1">
          <p class="arch-layer-name">${l.name}</p>
          <p class="arch-layer-items">${l.items}</p>
        </div>
      </div>
      ${i < layers.length - 1 ? `<div class="arch-connector">${arrow}</div>` : ""}`
      )
      .join("");
  }

  /* ------------------------------------------------------------------
   * Deployments
   * ------------------------------------------------------------------ */
  async function renderDeployments() {
    const result = await NexusAPI.getDeployments();
    renderSource("deployments-source", result);
    const body = document.getElementById("deployments-body");
    const empty = document.getElementById("deployments-empty");
    const table = document.getElementById("deployments-table");

    if (!result.data || !result.data.length) {
      table.hidden = true;
      empty.hidden = false;
      empty.innerHTML = `<p class="panel-empty-title">NO LIVE DEPLOYMENT DATA</p><p class="panel-empty-sub">Connect GitHub Actions and Argo CD to see real deployments here.</p>`;
      return;
    }

    body.innerHTML = result.data
      .map(
        (d) => `
      <tr>
        <td><strong>${d.app}</strong></td>
        <td>${d.env}</td>
        <td class="mono">${d.version}</td>
        <td class="mono">${d.commit}</td>
        <td class="mono">${d.branch}</td>
        <td>${d.author}</td>
        <td class="mono">${fmtDuration(d.durationSec)}</td>
        <td>${badge(d.status)}</td>
        <td>${badge(d.health)}</td>
      </tr>`
      )
      .join("");
  }

  /* ------------------------------------------------------------------
   * CI/CD pipeline run
   * ------------------------------------------------------------------ */
  async function renderPipelineRun() {
    const result = await NexusAPI.getPipelineRun();
    renderSource("cicd-source", result);
    const host = document.getElementById("cicd-panel");

    if (!result.data) {
      host.innerHTML = `<div class="panel-empty"><p class="panel-empty-title">NO LIVE PIPELINE DATA</p><p class="panel-empty-sub">Connect the GitHub Actions API to stream pipeline runs.</p></div>`;
      return;
    }

    const p = result.data;
    host.innerHTML = `
      <div class="cost-summary">
        <div>
          <p class="cost-total-label mono">${p.pipeline}</p>
          <p class="cost-total-value" style="font-size:20px">${badge(p.status)}</p>
        </div>
        <div class="data-source">
          <span>Branch <strong class="mono">${p.branch}</strong></span>
          <span>·</span>
          <span>Commit <strong class="mono">${p.commit}</strong></span>
          <span>·</span>
          <span>Triggered by ${p.triggeredBy}</span>
          <span>·</span>
          <span>${fmtDuration(p.durationSec)} total</span>
        </div>
      </div>
      <div class="scan-flow" style="padding:24px 26px">
        ${p.stages
          .map(
            (s, i) => `
          <span class="scan-step">${badge(s.status)} ${s.name} <span class="mono" style="color:var(--muted)">${fmtDuration(s.durationSec)}</span></span>
          ${i < p.stages.length - 1 ? '<span class="scan-arrow">→</span>' : ""}`
          )
          .join("")}
      </div>`;
  }

  /* ------------------------------------------------------------------
   * Kubernetes
   * ------------------------------------------------------------------ */
  async function renderKubernetes() {
    const result = await NexusAPI.getKubernetes();
    renderSource("k8s-source", result);
    const grid = document.getElementById("k8s-grid");

    if (!result.data) {
      grid.innerHTML = `<div class="panel-empty" style="grid-column:1/-1"><p class="panel-empty-title">KUBERNETES DATA UNAVAILABLE</p><p class="panel-empty-sub">Unable to reach cluster metrics.</p></div>`;
      return;
    }

    const k = result.data;
    const cards = [
      { title: "Cluster status", value: badge(k.clusterStatus), sub: "EKS" },
      { title: "Nodes", value: `${k.nodes.ready} / ${k.nodes.total}`, sub: "ready" },
      { title: "Pods", value: `${k.pods.running} / ${k.pods.total}`, sub: `${k.pods.pending} pending · ${k.pods.failed} failed` },
      { title: "Deployments", value: `${k.deployments.available} / ${k.deployments.total}`, sub: "available" },
      { title: "Namespaces", value: k.namespaces, sub: "active" },
      { title: "CPU utilization", value: `${k.cpuUsedPct}%`, sub: "cluster-wide" },
      { title: "Memory utilization", value: `${k.memUsedPct}%`, sub: "cluster-wide" },
      { title: "Restarts (24h)", value: k.restarts24h, sub: "across all pods" },
    ];
    grid.innerHTML = cards
      .map(
        (c) => `
      <div class="stat-card">
        <div class="stat-top"><span class="stat-title">${c.title}</span></div>
        <p class="stat-value">${c.value}</p>
        <p class="stat-sub">${c.sub}</p>
      </div>`
      )
      .join("");
  }

  /* ------------------------------------------------------------------
   * Observability
   * ------------------------------------------------------------------ */
  function renderObservabilityStatus(result) {
    const grid = document.getElementById("obs-grid");
    if (!result.data) {
      grid.innerHTML = `<div class="panel-empty" style="grid-column:1/-1">
        <p class="panel-empty-title">NO LIVE TELEMETRY</p>
        <p class="panel-empty-sub">Connect Prometheus to populate real metrics. NEXUS does not generate replacement values.</p>
      </div>`;
    }
  }

  async function renderObservability() {
    const result = await NexusAPI.getObservability();
    renderSource("obs-source", result);
    const grid = document.getElementById("obs-grid");

    if (!result.data || !Array.isArray(result.data.panels)) {
      renderObservabilityStatus(result);
      return;
    }

    grid.innerHTML = result.data.panels
      .map((p) => `
        <div class="dash-card">
          <p class="dash-label">${p.label}</p>
          <p class="dash-value">${p.value ?? "N/A"}</p>
          <p class="stat-sub">${p.source || result.source || "LIVE DATA"}</p>
        </div>`)
      .join("");
  }

  async function renderLogs(filter) {
    const result = await NexusAPI.getLogs();
    const host = document.getElementById("logs-console");
    if (!result.data || !result.data.length) {
      host.innerHTML = `<div class="panel-empty"><p class="panel-empty-title">NO LIVE LOG STREAM</p><p class="panel-empty-sub">Connect Loki to stream logs here.</p></div>`;
      return;
    }
    const rows = result.data.filter((l) => !filter || filter === "ALL" || l.level === filter);
    host.innerHTML =
      rows
        .map(
          (l) => `
      <div class="log-line">
        <span class="log-ts">${l.ts}</span>
        <span class="log-level log-level--${l.level}">${l.level}</span>
        <span class="log-svc">${l.service}</span>
        <span class="log-msg">${l.msg}</span>
      </div>`
        )
        .join("") || `<div class="panel-empty-sub" style="padding:20px 0">No log lines match this filter.</div>`;
  }

  function initLogFilters() {
    const wrap = document.getElementById("log-filters");
    wrap.addEventListener("click", (e) => {
      const btn = e.target.closest(".chip");
      if (!btn) return;
      wrap.querySelectorAll(".chip").forEach((c) => c.classList.remove("is-active"));
      btn.classList.add("is-active");
      renderLogs(btn.dataset.level);
    });
  }

  /* ------------------------------------------------------------------
   * GitOps
   * ------------------------------------------------------------------ */
  async function renderGitOps() {
    const result = await NexusAPI.getGitOps();
    renderSource("gitops-source", result);
    const grid = document.getElementById("gitops-grid");

    if (!result.data || !result.data.length) {
      grid.innerHTML = `<div class="panel-empty" style="grid-column:1/-1"><p class="panel-empty-title">NO LIVE GITOPS DATA</p><p class="panel-empty-sub">Connect Argo CD to see sync and health status.</p></div>`;
      return;
    }

    grid.innerHTML = result.data
      .map(
        (g) => `
      <div class="gitops-card">
        <div class="gitops-card-head">
          <div>
            <p class="gitops-app">${g.app}</p>
            <p class="gitops-repo">${g.repo}</p>
          </div>
          ${badge(g.sync)}
        </div>
        <div class="gitops-row"><span>Health</span>${badge(g.health)}</div>
        <div class="gitops-row"><span>Target revision</span><span class="mono">${g.targetRevision}</span></div>
        <div class="gitops-row"><span>Desired / live</span><span class="mono">${g.desired} / ${g.live}</span></div>
        <div class="gitops-row"><span>Last sync</span><span class="mono">${fmtTime(g.lastSync)}</span></div>
      </div>`
      )
      .join("");
  }

  /* ------------------------------------------------------------------
   * Security
   * ------------------------------------------------------------------ */
  function renderScanFlow() {
    const steps = ["Source", "SAST", "Dependency scan", "Secret scan", "Container scan", "Security gate", "Deploy"];
    const host = document.getElementById("scan-flow");
    host.innerHTML = steps
      .map((s, i) => `<span class="scan-step">${s}</span>${i < steps.length - 1 ? '<span class="scan-arrow">→</span>' : ""}`)
      .join("");
  }

  async function renderSecurity() {
    const result = await NexusAPI.getSecurity();
    renderSource("security-source", result);
    const body = document.getElementById("security-body");
    const empty = document.getElementById("security-empty");
    const table = document.getElementById("security-table");

    if (!result.data || !result.data.length) {
      table.hidden = true;
      empty.hidden = false;
      empty.innerHTML = `<p class="panel-empty-title">NO LIVE SECURITY RESULTS</p><p class="panel-empty-sub">Connect Trivy and scanner outputs to populate findings.</p>`;
      return;
    }

    body.innerHTML = result.data
      .map(
        (f) => `
      <tr>
        <td>${sevBadge(f.severity)}</td>
        <td>${f.scanner}</td>
        <td class="mono">${f.target}</td>
        <td class="mono">${f.ref}</td>
        <td>${badge(f.status)}</td>
        <td class="mono">${fmtTime(f.detected)}</td>
      </tr>`
      )
      .join("");
  }

  /* ------------------------------------------------------------------
   * Infrastructure
   * ------------------------------------------------------------------ */
  async function renderInfrastructure() {
    const result = await NexusAPI.getInfrastructure();
    renderSource("infra-source", result);
    const grid = document.getElementById("infra-grid");
    const stack = document.getElementById("aws-stack");

    if (!result.data) {
      grid.innerHTML = `<div class="panel-empty" style="grid-column:1/-1"><p class="panel-empty-title">INFRASTRUCTURE DATA UNAVAILABLE</p><p class="panel-empty-sub">Connect Terraform state to show plan and apply history.</p></div>`;
      stack.innerHTML = "";
      return;
    }

    const i = result.data;
    const cards = [
      { title: "State status", value: badge(i.stateStatus), sub: "Terraform" },
      { title: "Last plan", value: fmtTime(i.lastPlan), sub: new Date(i.lastPlan).toDateString() },
      { title: "Last apply", value: fmtTime(i.lastApply), sub: new Date(i.lastApply).toDateString() },
      { title: "Resources changed", value: i.resourcesChanged, sub: `${i.resourcesCreated} created · ${i.resourcesDestroyed} destroyed` },
      { title: "Drift detected", value: i.driftDetected ? badge("WARNING") : badge("PASSED"), sub: i.driftDetected ? "review required" : "none" },
    ];
    grid.innerHTML = cards
      .map(
        (c) => `
      <div class="stat-card">
        <div class="stat-top"><span class="stat-title">${c.title}</span></div>
        <p class="stat-value" style="font-size:20px">${c.value}</p>
        <p class="stat-sub">${c.sub}</p>
      </div>`
      )
      .join("");

    stack.innerHTML = i.awsResources
      .map(
        (r) => `
      <div class="aws-item">
        <span class="aws-item-icon">${icon("aws")}</span>
        <div>
          <p class="aws-item-name">${r.name}</p>
          <p class="aws-item-detail">${r.detail}</p>
        </div>
      </div>`
      )
      .join("");
  }

  /* ------------------------------------------------------------------
   * FinOps
   * ------------------------------------------------------------------ */
  async function renderCosts() {
    const result = await NexusAPI.getCosts();
    renderSource("cost-source", result);
    const host = document.getElementById("cost-panel");

    if (!result.data) {
      host.innerHTML = `<div class="panel-empty"><p class="panel-empty-title">COST DATA NOT CONNECTED</p><p class="panel-empty-sub">Connect AWS Cost Explorer to show real spend.</p></div>`;
      return;
    }

    const c = result.data;
    const max = Math.max(...c.breakdown.map((b) => b.value));
    host.innerHTML = `
      <div class="cost-summary">
        <div>
          <p class="cost-total-label">Month to date</p>
          <p class="cost-total-value">$${c.monthToDate.toFixed(2)}</p>
        </div>
        <span class="cost-trend" style="color:${c.trendPct >= 0 ? "var(--red)" : "var(--green)"}">${c.trendPct >= 0 ? "↑" : "↓"} ${Math.abs(c.trendPct)}% vs last month</span>
      </div>
      <div class="cost-rows">
        ${c.breakdown
          .map(
            (b) => `
          <div class="cost-row">
            <span class="cost-row-label">${b.label}</span>
            <span class="cost-row-bar"><span style="width:${(b.value / max) * 100}%"></span></span>
            <span class="cost-row-value">$${b.value.toFixed(2)}</span>
          </div>`
          )
          .join("")}
      </div>`;
  }

  /* ------------------------------------------------------------------
   * Deploy panel — upload a zip, watch the pipeline run live
   * ------------------------------------------------------------------ */
  const STEP_LABELS = {
    upload: "Upload", inspect: "Inspect", build: "Build", security: "Security gate",
    publish: "Publish", deploy: "Deploy", verify: "Verify",
  };
  const STEP_STATE_LABELS = {
    pending: "Waiting", running: "Running", success: "Complete",
    failed: "Blocked", skipped: "Skipped",
  };

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  function initDeployPanel() {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("deploy-file-input");
    const fileNameEl = document.getElementById("dropzone-file-name");
    const appNameInput = document.getElementById("deploy-app-name");
    const submitBtn = document.getElementById("deploy-submit");
    const form = document.getElementById("deploy-form");
    const progressWrap = document.getElementById("deploy-progress");
    const liveDetails = document.getElementById("deploy-live-details");
    const stepsWrap = document.getElementById("deploy-steps");
    const resultEl = document.getElementById("deploy-result");
    const consoleEl = document.getElementById("deploy-console");
    const apiKeyInput = document.getElementById("deploy-access-key");

    if (!dropzone || !form) return;

    let selectedFile = null;

    function setFile(file) {
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".zip")) {
        fileNameEl.textContent = "Please choose a .zip file.";
        return;
      }
      selectedFile = file;
      dropzone.classList.add("has-file");
      const kb = (file.size / 1024).toFixed(0);
      fileNameEl.textContent = `${file.name} (${kb} KB)`;
      submitBtn.disabled = false;
    }

    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
    });
    fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

    ["dragenter", "dragover"].forEach((evt) =>
      dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("is-dragover"); })
    );
    ["dragleave", "drop"].forEach((evt) =>
      dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("is-dragover"); })
    );
    dropzone.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      setFile(file);
    });

    function resetSteps() {
      stepsWrap.querySelectorAll(".deploy-step").forEach((li) => {
        li.dataset.status = "pending";
        const state = li.querySelector("small");
        if (state) state.textContent = STEP_STATE_LABELS.pending;
      });
    }

    function applyStepStatuses(steps) {
      Object.keys(steps || {}).forEach((key) => {
        const li = stepsWrap.querySelector(`[data-step="${key}"]`);
        if (li) {
          li.dataset.status = steps[key];
          const state = li.querySelector("small");
          if (state) state.textContent = STEP_STATE_LABELS[steps[key]] || "Waiting";
        }
      });
    }

    function appendLogs(lines) {
      if (!lines || !lines.length) return;
      const atBottom = consoleEl.scrollTop + consoleEl.clientHeight >= consoleEl.scrollHeight - 12;
      lines.forEach((l) => {
        const cls = l.level && l.level !== "info" ? ` class="log-${l.level}"` : "";
        consoleEl.insertAdjacentHTML("beforeend", `<span${cls}>${escapeHtml(l.text)}</span>\n`);
      });
      if (atBottom) consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    function showResult(detail) {
      resultEl.hidden = false;
      if (detail.status === "success") {
        resultEl.className = "deploy-result deploy-result--success";
        const link = detail.previewUrl
          ? `<a class="btn btn--sm btn--secondary" href="${detail.previewUrl}" target="_blank" rel="noopener">Open preview</a>`
          : "";
        const gitopsPending = detail.mode === "gitops" && detail.steps && detail.steps.verify === "skipped";
        const message = gitopsPending
          ? "GitOps release submitted — Argo CD verification is still pending."
          : `Release complete via ${detail.mode} mode.`;
        resultEl.innerHTML = `<span>✅ ${message}${detail.imageTag ? ` <span class="mono">${escapeHtml(detail.imageTag)}</span>` : ""}</span>${link}`;
      } else {
        resultEl.className = "deploy-result deploy-result--failed";
        resultEl.innerHTML = `<span>❌ ${escapeHtml(detail.error || "Deploy failed")}</span>`;
      }
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!selectedFile) return;

      submitBtn.disabled = true;
      progressWrap.hidden = false;
      liveDetails.hidden = false;
      resultEl.hidden = true;
      consoleEl.innerHTML = "";
      resetSteps();

      const started = await NexusAPI.deployUpload(
        selectedFile,
        appNameInput.value.trim(),
        apiKeyInput ? apiKeyInput.value : ""
      );

      if (started.mode === "error" || started.mode === "unavailable" || !started.data) {
        resultEl.hidden = false;
        resultEl.className = "deploy-result deploy-result--failed";
        resultEl.innerHTML = `<span>❌ ${escapeHtml(started.error || "Couldn't start the deploy.")}</span>`;
        submitBtn.disabled = false;
        return;
      }

      const jobId = started.data.jobId;
      if (!appNameInput.value.trim() && started.data.app) {
        appNameInput.placeholder = `NEXUS selected: ${started.data.app}`;
      }

      NexusAPI.streamDeployJob(
        jobId,
        (detail) => {
          applyStepStatuses(detail.steps);
          appendLogs(detail.logs);
          if (detail.status === "success" || detail.status === "failed") {
            showResult(detail);
          }
        },
        () => {
          submitBtn.disabled = false;
          renderDeployJobs();
        }
      );
    });
  }

  async function renderDeployJobs() {
    const result = await NexusAPI.getDeployJobs();
    const body = document.getElementById("deploy-jobs-body");
    const empty = document.getElementById("deploy-jobs-empty");
    const table = document.getElementById("deploy-jobs-table");
    if (!body) return;

    if (!result.data || !result.data.length) {
      table.hidden = true;
      empty.hidden = false;
      empty.innerHTML = `<p class="panel-empty-title">NO DEPLOYS YET</p><p class="panel-empty-sub">Upload a .zip above to run your first automated deploy.</p>`;
      return;
    }

    table.hidden = false;
    empty.hidden = true;

    const STATUS_MAP = { success: "SUCCESS", failed: "FAILED", running: "RUNNING", queued: "QUEUED" };

    body.innerHTML = result.data
      .map((j) => `
      <tr>
        <td><strong>${escapeHtml(j.app)}</strong>${j.project ? `<br><span class="table-sub">${escapeHtml(j.project.framework || j.project.kind || "")}</span>` : ""}</td>
        <td>${j.mode ? `<span class="tag-pill">${j.mode}</span>` : "—"}</td>
        <td>${badge(STATUS_MAP[j.status] || "UNKNOWN")}</td>
        <td class="mono">${j.imageTag ? escapeHtml(j.imageTag) : "—"}</td>
        <td>${timeAgo(new Date(j.createdAt * 1000).toISOString())}</td>
        <td>${j.previewUrl ? `<a class="btn btn--sm btn--ghost" href="${j.previewUrl}" target="_blank" rel="noopener">Open</a>` : ""}</td>
      </tr>`)
      .join("");
  }

  async function renderDeployModeIndicator() {
    const node = document.getElementById("deploy-mode-indicator");
    if (!node) return;
    const result = await NexusAPI.getDeployConfig();
    const config = result.data;
    if (!config) {
      node.textContent = "Deployment target status unavailable";
      return;
    }
    node.textContent = config.detail || config.label;
    const accessWrap = document.getElementById("deploy-access-key-wrap");
    const accessInput = document.getElementById("deploy-access-key");
    if (accessWrap && config.requiresApiKey) {
      accessWrap.hidden = false;
      if (accessInput) accessInput.required = true;
    }
  }

  /* ------------------------------------------------------------------
   * Header / platform health
   * ------------------------------------------------------------------ */
  async function renderHeaderHealth() {
    const result = await NexusAPI.getHealth();
    const host = document.getElementById("header-status");
    if (!host) return;

    let label = "Not connected";
    let tone = "gray";

    if (result.data && result.data.status) {
      label = result.data.status;
      tone = result.data.status === "CONNECTED" ? "green" :
             result.data.status === "DEGRADED" ? "amber" : "gray";
    }

    host.innerHTML = `<span class="status-dot status-dot--${tone}" aria-hidden="true"></span><span>${label}</span>`;
  }

  /* ------------------------------------------------------------------
   * Boot
   * ------------------------------------------------------------------ */
  document.addEventListener("DOMContentLoaded", () => {
    initNav();
    renderPipelineSteps();
    renderArchFlow();
    renderScanFlow();
    initLogFilters();
    initReveal();
    initDeployPanel();

    renderHeaderHealth();
    renderDeployModeIndicator();
    renderDeployJobs();
    renderDeployments();
    renderPipelineRun();
    renderKubernetes();
    renderObservability();
    renderLogs("ALL");
    renderGitOps();
    renderSecurity();
    renderInfrastructure();
    renderCosts();

    // Refresh health and live telemetry without fabricating values.
    setInterval(function () {
      renderHeaderHealth();
      renderObservability();
    }, 15000);
  });
})();

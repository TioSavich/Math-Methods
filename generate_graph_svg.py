#!/usr/bin/env python3
"""
Generate a print-ready SVG of the E343 alignment graph.
Uses the same color scheme as visualization.html but with darker edge strokes.
"""

import json
import math
import random

# ─── Config ──────────────────────────────────────────────────────────────────
WIDTH = 2400
HEIGHT = 1800
PADDING = 80
NODE_BASE_R = 4
NODE_SCALE = 0.5       # extra radius per connection (capped)
EDGE_COLOR = "#5a6070"  # dark gray — visible when printed
EDGE_OPACITY = 0.45
EDGE_WIDTH = 0.6
FONT_SIZE = 7
LABEL_THRESHOLD = 6     # only label nodes with >= this many connections
BG_COLOR = "#ffffff"

TYPE_COLORS = {
    "lesson_plan":       "#2e7d6f",
    "indiana_standard":  "#c05621",
    "topic":             "#6b46c1",
    "vdw_section":       "#2563eb",
    "im_unit":           "#d63384",
    "im_lesson":         "#e8457a",
    "five_practice":     "#059669",
    "fp_chapter":        "#059669",
    "cdm_chapter":       "#0891b2",
    "cdm_video":         "#0ea5e9",
    "cdm_lesson":        "#06b6d4",
    "assignment":        "#b45309",
    "quiz":              "#7c3aed",
    "process_standard":  "#475569",
    "learning_component":"#e11d48",
    "canvas_resource":   "#64748b",
    "canvas_folder":     "#78909c",
    "canvas_video":      "#546e7a",
    "im_field_placement":"#f472b6",
}
DEFAULT_COLOR = "#94a3b8"

TYPE_LABELS = {
    "lesson_plan":       "Lesson Plans",
    "indiana_standard":  "Indiana Standards",
    "topic":             "Topics",
    "vdw_section":       "Van de Walle",
    "im_unit":           "IM Units",
    "im_lesson":         "IM Lessons",
    "five_practice":     "Five Practices",
    "fp_chapter":        "Five Practices Ch.",
    "cdm_chapter":       "CDM Chapters",
    "cdm_video":         "CDM Videos",
    "cdm_lesson":        "CDM Lessons",
    "assignment":        "Assignments",
    "quiz":              "Quizzes",
    "process_standard":  "Process Standards",
    "learning_component":"Learning Components",
    "canvas_resource":   "Canvas Resources",
}

# ─── Load data ───────────────────────────────────────────────────────────────
with open("e343_alignment_graph.json") as f:
    data = json.load(f)

nodes = []
node_map = {}
for cat, node_list in data["nodes"].items():
    for n in node_list:
        title = n.get("title") or n.get("name") or n.get("label") or n.get("code") or n["id"]
        entry = {"id": n["id"], "type": n["type"], "title": title}
        nodes.append(entry)
        node_map[n["id"]] = entry

edges = []
for e in data["edges"]:
    if e["from"] in node_map and e["to"] in node_map:
        edges.append((e["from"], e["to"], e.get("type", "")))

# Build adjacency for connection counts
adj = {n["id"]: 0 for n in nodes}
for fr, to, _ in edges:
    adj[fr] = adj.get(fr, 0) + 1
    adj[to] = adj.get(to, 0) + 1

# ─── Force-directed layout ───────────────────────────────────────────────────
random.seed(42)

# Initial positions: cluster by type
type_list = list(dict.fromkeys(n["type"] for n in nodes))
type_groups = {}
for n in nodes:
    type_groups.setdefault(n["type"], []).append(n["id"])

pos = {}
cx, cy = WIDTH / 2, HEIGHT / 2
for ti, t in enumerate(type_list):
    angle = (ti / len(type_list)) * 2 * math.pi - math.pi / 2
    cluster_r = min(WIDTH, HEIGHT) * 0.3
    ccx = cx + math.cos(angle) * cluster_r
    ccy = cy + math.sin(angle) * cluster_r
    group = type_groups[t]
    for gi, nid in enumerate(group):
        inner_angle = (gi / max(len(group), 1)) * 2 * math.pi
        inner_r = min(30 + len(group) * 2, 120)
        jx = (random.random() - 0.5) * 20
        jy = (random.random() - 0.5) * 20
        pos[nid] = [
            ccx + math.cos(inner_angle) * inner_r + jx,
            ccy + math.sin(inner_angle) * inner_r + jy,
        ]

# Simulate (matching the JS parameters)
TOTAL_ITERS = 400
REP_STRENGTH = 2000
MAX_DIST = 400
SPRING_LEN = 60
SPRING_K = 0.06
GRAV = 0.3
MAX_V = 15

node_ids = [n["id"] for n in nodes]
N = len(node_ids)

print(f"Running force layout: {N} nodes, {len(edges)} edges, {TOTAL_ITERS} iterations...")

for it in range(TOTAL_ITERS):
    cooling = 1 - it / TOTAL_ITERS
    dt = 0.8 * cooling + 0.1

    vx = {nid: 0.0 for nid in node_ids}
    vy = {nid: 0.0 for nid in node_ids}

    # Repulsion
    for i in range(N):
        a = node_ids[i]
        ax, ay = pos[a]
        for j in range(i + 1, N):
            b = node_ids[j]
            bx, by = pos[b]
            dx = bx - ax
            dy = by - ay
            d2 = dx * dx + dy * dy
            if d2 > MAX_DIST * MAX_DIST:
                continue
            dist = math.sqrt(d2) or 0.1
            f = REP_STRENGTH / (dist * dist)
            fx = (dx / dist) * f
            fy = (dy / dist) * f
            vx[a] -= fx; vy[a] -= fy
            vx[b] += fx; vy[b] += fy

    # Edge attraction
    for fr, to, _ in edges:
        ax, ay = pos[fr]
        bx, by = pos[to]
        dx = bx - ax
        dy = by - ay
        dist = math.sqrt(dx * dx + dy * dy) or 0.1
        f = (dist - SPRING_LEN) * SPRING_K
        fx = (dx / dist) * f
        fy = (dy / dist) * f
        vx[fr] += fx; vy[fr] += fy
        vx[to] -= fx; vy[to] -= fy

    # Center gravity
    for nid in node_ids:
        vx[nid] += (cx - pos[nid][0]) * GRAV * 0.01
        vy[nid] += (cy - pos[nid][1]) * GRAV * 0.01

    # Apply velocities
    for nid in node_ids:
        dvx = max(-MAX_V, min(MAX_V, vx[nid] * dt))
        dvy = max(-MAX_V, min(MAX_V, vy[nid] * dt))
        pos[nid][0] += dvx
        pos[nid][1] += dvy

    if (it + 1) % 100 == 0:
        print(f"  iteration {it + 1}/{TOTAL_ITERS}")

# ─── Fit to canvas ──────────────────────────────────────────────────────────
min_x = min(p[0] for p in pos.values())
max_x = max(p[0] for p in pos.values())
min_y = min(p[1] for p in pos.values())
max_y = max(p[1] for p in pos.values())

graph_w = (max_x - min_x) or 1
graph_h = (max_y - min_y) or 1
scale = min((WIDTH - 2 * PADDING) / graph_w, (HEIGHT - 2 * PADDING) / graph_h)

for nid in node_ids:
    pos[nid][0] = PADDING + (pos[nid][0] - min_x) * scale
    pos[nid][1] = PADDING + (pos[nid][1] - min_y) * scale

# ─── Generate SVG ────────────────────────────────────────────────────────────
def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

svg_parts = []
svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">')
svg_parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG_COLOR}"/>')


# Edges layer
svg_parts.append('<g id="edges">')
for fr, to, etype in edges:
    x1, y1 = pos[fr]
    x2, y2 = pos[to]
    svg_parts.append(
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{EDGE_COLOR}" stroke-opacity="{EDGE_OPACITY}" stroke-width="{EDGE_WIDTH}"/>'
    )
svg_parts.append('</g>')

# Nodes layer
svg_parts.append('<g id="nodes">')
for n in nodes:
    nid = n["id"]
    x, y = pos[nid]
    conns = adj.get(nid, 0)
    r = NODE_BASE_R + min(conns, 20) * NODE_SCALE
    color = TYPE_COLORS.get(n["type"], DEFAULT_COLOR)
    svg_parts.append(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" opacity="0.9">'
        f'<title>{escape(n["title"])}</title></circle>'
    )
svg_parts.append('</g>')


svg_parts.append('</svg>')

svg_content = "\n".join(svg_parts)

out_path = "e343_alignment_graph.svg"
with open(out_path, "w") as f:
    f.write(svg_content)

print(f"\nDone! Wrote {out_path}")
print(f"  Size: {len(svg_content):,} bytes")
print(f"  Dimensions: {WIDTH}×{HEIGHT}")
print(f"  Edge stroke: {EDGE_COLOR} at {EDGE_OPACITY} opacity, {EDGE_WIDTH}px width")
print(f"  Labels shown for nodes with >= {LABEL_THRESHOLD} connections")

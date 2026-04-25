#!/usr/bin/env python3
"""
Generate a print-ready PDF of the E343 alignment graph using reportlab.
Reads positions from the SVG generation (same layout logic).
"""

import json
import math
import random
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas

# ─── Config ──────────────────────────────────────────────────────────────────
# Letter landscape = 11" × 8.5"
PAGE_W, PAGE_H = landscape((8.5 * inch, 11 * inch))
PADDING = 0.6 * inch
NODE_BASE_R = 2.5
NODE_SCALE = 0.35
EDGE_COLOR = HexColor("#4a5060")
EDGE_OPACITY = 0.5
EDGE_WIDTH = 0.4
FONT_SIZE = 4.5
LABEL_THRESHOLD = 6
TITLE_FONT_SIZE = 14
SUBTITLE_FONT_SIZE = 8

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

adj = {n["id"]: 0 for n in nodes}
for fr, to, _ in edges:
    adj[fr] = adj.get(fr, 0) + 1
    adj[to] = adj.get(to, 0) + 1

# ─── Force-directed layout ───────────────────────────────────────────────────
random.seed(42)
LAYOUT_W, LAYOUT_H = 2400, 1800

type_list = list(dict.fromkeys(n["type"] for n in nodes))
type_groups = {}
for n in nodes:
    type_groups.setdefault(n["type"], []).append(n["id"])

pos = {}
cx, cy = LAYOUT_W / 2, LAYOUT_H / 2
for ti, t in enumerate(type_list):
    angle = (ti / len(type_list)) * 2 * math.pi - math.pi / 2
    cluster_r = min(LAYOUT_W, LAYOUT_H) * 0.3
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

TOTAL_ITERS = 400
node_ids = [n["id"] for n in nodes]
N = len(node_ids)

print(f"Running force layout: {N} nodes, {len(edges)} edges, {TOTAL_ITERS} iterations...")

for it in range(TOTAL_ITERS):
    cooling = 1 - it / TOTAL_ITERS
    dt = 0.8 * cooling + 0.1

    vx = {nid: 0.0 for nid in node_ids}
    vy = {nid: 0.0 for nid in node_ids}

    for i in range(N):
        a = node_ids[i]
        ax, ay = pos[a]
        for j in range(i + 1, N):
            b = node_ids[j]
            bx, by = pos[b]
            dx = bx - ax
            dy = by - ay
            d2 = dx * dx + dy * dy
            if d2 > 160000:  # 400^2
                continue
            dist = math.sqrt(d2) or 0.1
            f = 2000 / (dist * dist)
            fx = (dx / dist) * f
            fy = (dy / dist) * f
            vx[a] -= fx; vy[a] -= fy
            vx[b] += fx; vy[b] += fy

    for fr, to, _ in edges:
        ax, ay = pos[fr]
        bx, by = pos[to]
        dx = bx - ax
        dy = by - ay
        dist = math.sqrt(dx * dx + dy * dy) or 0.1
        f = (dist - 60) * 0.06
        fx = (dx / dist) * f
        fy = (dy / dist) * f
        vx[fr] += fx; vy[fr] += fy
        vx[to] -= fx; vy[to] -= fy

    for nid in node_ids:
        vx[nid] += (cx - pos[nid][0]) * 0.003
        vy[nid] += (cy - pos[nid][1]) * 0.003

    for nid in node_ids:
        dvx = max(-15, min(15, vx[nid] * dt))
        dvy = max(-15, min(15, vy[nid] * dt))
        pos[nid][0] += dvx
        pos[nid][1] += dvy

    if (it + 1) % 100 == 0:
        print(f"  iteration {it + 1}/{TOTAL_ITERS}")

# ─── Map layout coords to PDF coords ────────────────────────────────────────
min_x = min(p[0] for p in pos.values())
max_x = max(p[0] for p in pos.values())
min_y = min(p[1] for p in pos.values())
max_y = max(p[1] for p in pos.values())

graph_w = (max_x - min_x) or 1
graph_h = (max_y - min_y) or 1
usable_w = PAGE_W - 2 * PADDING
usable_h = PAGE_H - 2 * PADDING
scale = min(usable_w / graph_w, usable_h / graph_h)

def to_pdf(lx, ly):
    """Convert layout coords to PDF coords (PDF origin is bottom-left)."""
    px = PADDING + (lx - min_x) * scale
    py = PADDING + (max_y - ly) * scale  # flip Y
    return px, py

# ─── Draw PDF ────────────────────────────────────────────────────────────────
out_path = "e343_alignment_graph.pdf"
c = canvas.Canvas(out_path, pagesize=(PAGE_W, PAGE_H))

# Edges
c.setLineWidth(EDGE_WIDTH)
c.setLineCap(1)  # round cap
for fr, to, _ in edges:
    x1, y1 = to_pdf(*pos[fr])
    x2, y2 = to_pdf(*pos[to])
    c.setStrokeColor(EDGE_COLOR, EDGE_OPACITY)
    c.line(x1, y1, x2, y2)

# Nodes
for n in nodes:
    nid = n["id"]
    x, y = to_pdf(*pos[nid])
    conns = adj.get(nid, 0)
    r = NODE_BASE_R + min(conns, 20) * NODE_SCALE
    color = HexColor(TYPE_COLORS.get(n["type"], DEFAULT_COLOR))
    c.setFillColor(color, 0.9)
    c.setStrokeColor(color, 0.6)
    c.setLineWidth(0.2)
    c.circle(x, y, r, fill=1, stroke=1)

c.save()
print(f"\nDone! Wrote {out_path}")
print(f"  Page size: {PAGE_W/inch:.1f}\" × {PAGE_H/inch:.1f}\" (landscape)")

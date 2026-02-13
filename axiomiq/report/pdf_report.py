from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from axiomiq.core.interpretation import interpret_param


def _fmt_eta(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "N/A"
    try:
        return f"{float(x):.1f}d"
    except Exception:
        return "N/A"


def _wrap_lines(c: canvas.Canvas, text: str, max_width: float, font_name: str, font_size: int) -> list[str]:
    c.setFont(font_name, font_size)
    words = (text or "").split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for w in words[1:]:
        test = f"{current} {w}"
        if c.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines


def _draw_wrapped(
    c: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    max_width: float,
    line_height: int = 13,
    font_name: str = "Helvetica",
    font_size: int = 10,
) -> float:
    lines = _wrap_lines(c, text, max_width, font_name, font_size)
    c.setFont(font_name, font_size)
    for line in lines:
        c.drawString(x, y, line)
        y -= line_height
    return y

def _draw_sparkline(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    values: list[float] | None,
) -> None:
    """
    Draw a tiny 0..1 sparkline.
    y is the current text baseline; we draw the sparkline slightly above/below baseline.
    """
    if not values:
        return

    # Keep it simple and safe
    vals = [v for v in values if isinstance(v, (int, float))]
    if len(vals) < 2:
        return

    # normalize again defensively to 0..1
    mn = min(vals)
    mx = max(vals)
    if mx - mn > 1e-9:
        vals = [(v - mn) / (mx - mn) for v in vals]
    else:
        vals = [0.5 for _ in vals]

    # Sparkline box (no border, just polyline)
    # We’ll draw it centered vertically around the current row baseline.
    y0 = y - (h * 0.6)

    n = len(vals)
    dx = w / (n - 1)

    # Build line segments
    last_x = x
    last_y = y0 + (vals[0] * h)

    for i in range(1, n):
        xx = x + i * dx
        yy = y0 + (vals[i] * h)
        c.line(last_x, last_y, xx, yy)
        last_x, last_y = xx, yy
        
def _draw_footer(
    c: canvas.Canvas,
    page_w: float,
    y: float,
    text: str,
    left: float,
    right: float,
) -> None:
    c.setFont("Helvetica", 8)
    c.drawRightString(page_w - right, y, text)
    c.drawString(left, y, "Blackreef · AxiomIQ")

def write_pdf_report(
    out_path: str | Path,
    fleet_df: pd.DataFrame,
    verdict: str,
    delta_lines: list[str] | None,
    generated_at: str | None,
    coverage_line: str | None,
    focus_engine_id: str,
    focus_score: float,
    focus_risks: pd.DataFrame,
    focus_trends: dict[str, list[float]] | None = None,
    notes: list[str] | None = None,
    run_config: dict[str, str] | None = None,
) -> Path:

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(out_path), pagesize=letter)
    page_w, page_h = letter

    # --- Layout / margins ---
    left = 34
    right = 44  # <-- more right margin = guaranteed no clipping
    max_width = page_w - left - right

    # --- Fleet table column widths (sum MUST be <= max_width) ---
    # NOTE: These widths sum to 523, and max_width is 534, so no clipping.
    COL_W = {
        "engine": 44,
        "trend": 48,
        "health": 42,
        "risk": 125,
        "reason": 130,
        "action": 70,
        "eta": 38,
        "pri": 26,
    }

    # X positions derived from widths
    order = ["engine", "trend", "health", "risk", "reason", "action", "eta", "pri"]
    X = {}
    x = left
    for k in order:
        X[k] = x
        x += COL_W[k]


    # Safety check (optional but nice)
    # print("table_right_edge=", x, "max_right=", page_w - right)

    # ======================
    # PAGE 1 — FLEET OVERVIEW
    # ======================
    y = page_h - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left, y, "Blackreef — AxiomIQ Fleet Overview")
    y -= 26

    # Report meta (timestamp + coverage)
    c.setFont("Helvetica", 10)
    if generated_at:
        c.drawString(left, y, f"Generated: {generated_at}")
        y -= 14
    if coverage_line:
        y = _draw_wrapped(c, left, y, coverage_line, max_width, line_height=12, font_name="Helvetica", font_size=10)
        y -= 6
    
    # ------------------------
    # Run Configuration (auditable metadata)
    # ------------------------
    if run_config:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "Run Configuration")
        y -= 12

        c.setFont("Helvetica", 10)

        # Render as compact key/value lines (wrap-safe)
        # Keep it short to avoid crowding the top of page 1.
        keys = ["profile", "seed", "days", "step_hours", "engines", "failure", "version"]
        items = [(k, run_config.get(k)) for k in keys if run_config.get(k)]

        # Build 1–2 compact lines (not a giant list)
        # Line 1: profile/seed/days/step
        line1_parts = []
        for k in ["profile", "seed", "days", "step_hours"]:
            v = run_config.get(k)
            if v:
                label = {
                    "profile": "Profile",
                    "seed": "Seed",
                    "days": "Days",
                    "step_hours": "Step(h)",
                }[k]
                line1_parts.append(f"{label}: {v}")

        if line1_parts:
            y = _draw_wrapped(c, left, y, " | ".join(line1_parts), max_width, line_height=12, font_name="Helvetica", font_size=10)
            y -= 2

        # Line 2: engines + failure + version (if present)
        line2_parts = []
        if run_config.get("engines"):
            line2_parts.append(f"Engines: {run_config['engines']}")
        if run_config.get("failure"):
            line2_parts.append(f"Failure: {run_config['failure']}")
        if run_config.get("version"):
            line2_parts.append(f"Version: {run_config['version']}")

        if line2_parts:
            y = _draw_wrapped(c, left, y, " | ".join(line2_parts), max_width, line_height=12, font_name="Helvetica", font_size=10)
            y -= 6
        else:
            y -= 6

    y -= 6

    # ------------------------
    # Key Changes Since Last Report
    # ------------------------
    if delta_lines is not None:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left, y, "Key Changes Since Last Report")
        y -= 16

        c.setFont("Helvetica", 11)
        for line in delta_lines:
            y = _draw_wrapped(
                c,
                left,
                y,
                f"• {line}",
                max_width,
                line_height=14,
                font_name="Helvetica",
                font_size=11,
            )
            y -= 2

        y -= 10

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Fleet Verdict")
    y -= 16

    y = _draw_wrapped(c, left, y, verdict, max_width, line_height=14, font_name="Helvetica", font_size=11)
    y -= 12

    c.setFont("Helvetica", 11)
    y = _draw_wrapped(
        c,
        left,
        y,
        "This page ranks generator sets by operational priority using health score, drift severity, and estimated time-to-limit.",
        max_width,
        line_height=14,
        font_name="Helvetica",
        font_size=11,
    )
    y -= 10
    
    # ------------------------
    # Top Alerts (top 3 engines)
    # ------------------------
    if not fleet_df.empty:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, "Top Alerts")
        y -= 14

        # Sort by priority then health (lowest health first inside same priority)
        pri_rank = {"HIGH": 0, "MED": 1, "LOW": 2}
        tmp = fleet_df.copy()
        if "priority" in tmp.columns:
            tmp["_pri_rank"] = tmp["priority"].map(lambda x: pri_rank.get(str(x), 9))
        else:
            tmp["_pri_rank"] = 9
        if "health" in tmp.columns:
            tmp["_health"] = pd.to_numeric(tmp["health"], errors="coerce")
        else:
            tmp["_health"] = 999.0

        tmp = tmp.sort_values(["_pri_rank", "_health"]).head(3)

        c.setFont("Helvetica", 9)
        for _, rr in tmp.iterrows():
            eng = str(rr.get("engine_id", ""))
            pri = str(rr.get("priority", ""))
            hs = rr.get("health", "")
            top = str(rr.get("top_risk", ""))
            eta = _fmt_eta(rr.get("eta_days"))
            action = str(rr.get("action", ""))

            # single compact line (wrap-safe)
            alert = f"{eng} [{pri}]  Health {hs}  |  {top}  |  ETA {eta}  |  {action}"
            y = _draw_wrapped(c, left, y, alert, max_width, line_height=11, font_name="Helvetica", font_size=9)
            y -= 2

        y -= 6

    # Table header
    c.setFont("Helvetica-Bold", 9)
    c.drawString(X["engine"], y, "Engine")
    c.drawString(X["trend"], y, "Trend")
    c.drawString(X["health"], y, "Health")
    c.drawString(X["risk"], y, "Top Risk")
    c.drawString(X["reason"], y, "Reason")
    c.drawString(X["action"], y, "Action")
    c.drawString(X["eta"], y, "ETA")
    c.drawString(X["pri"], y, "Pri")
    y -= 14

    c.setFont("Helvetica", 9)


    if fleet_df.empty:
        c.drawString(left, y, "No fleet data available.")
        y -= 14
    else:
        for _, r in fleet_df.iterrows():
            eng = str(r["engine_id"])
            hs = f'{float(r["health"]):.1f}'
            top = str(r["top_risk"])
            reason = str(r.get("reason", ""))
            action = str(r.get("action", ""))
            eta = _fmt_eta(r.get("eta_days"))
            pri = str(r["priority"])
            trend = r.get("trend", None)


            # ---- PRE-ROW PAGE BREAK (critical fix) ----
            min_row_height = 36  # enough for wrapped reason/top risk
            if y < min_row_height + 60:
                _draw_footer(
                    c,
                    page_w,
                    24,
                    f"Generated {generated_at}" if generated_at else "",
                    left,
                    right,
                )
                c.showPage()

                y = page_h - 60
                c.setFont("Helvetica-Bold", 12)
                c.drawString(left, y, "Blackreef — AxiomIQ Fleet Overview (cont.)")
                y -= 24
                c.setFont("Helvetica", 9)


            # Engine (with HIGH marker)
            is_high = (pri == "HIGH")
            if is_high:
                c.setFont("Helvetica-Bold", 9)
                c.drawString(X["engine"], y, f"! {eng}")
                c.setFont("Helvetica", 9)
            else:
                c.drawString(X["engine"], y, eng)

            # Trend sparkline should be drawn inside X["trend"]..X["trend"]+COL_W["trend"]
            # (keep your sparkline function, just ensure it uses COL_W["trend"])
            # Trend sparkline
            c.setLineWidth(0.6)
            _draw_sparkline(
                c,
                X["trend"],
                y,
                w=COL_W["trend"] - 6,
                h=10,
                values=trend if isinstance(trend, list) else None,
            )

            c.drawString(X["health"], y, hs)

            y_top = _draw_wrapped(
                c, X["risk"], y, top,
                max_width=COL_W["risk"], line_height=11,
                font_name="Helvetica", font_size=9
            )

            y_reason = _draw_wrapped(
                c, X["reason"], y, reason,
                max_width=COL_W["reason"], line_height=11,
                font_name="Helvetica", font_size=9
            )

            y_action = _draw_wrapped(
                c, X["action"], y, action,
                max_width=COL_W["action"] - 2, line_height=10,
                font_name="Helvetica", font_size=8
            )

            c.drawString(X["eta"], y, eta)
            c.drawString(X["pri"], y, pri)

            y = min(y_top, y_reason, y_action) - 10

    # --- Footer (Page 1) ---
    _draw_footer(
        c,
        page_w,
        24,
        f"Generated {generated_at}" if generated_at else "",
        left,
        right,
    )

    # ==========================
    # PAGE 2 — FOCUS ENGINE REPORT
    # ==========================
    c.showPage()
    y = page_h - 60

    c.setFont("Helvetica-Bold", 18)
    c.drawString(left, y, "Blackreef — AxiomIQ Analytics Report")
    y -= 34

    c.setFont("Helvetica-Bold", 14)
    c.drawString(left, y, "Executive Summary")
    y -= 22

    summary = (
        f"Engine {focus_engine_id} is currently operating within defined limits, with an overall health score "
        f"of {focus_score} out of 100. Analysis indicates developing drift patterns rather than immediate failure conditions."
    )
    y = _draw_wrapped(c, left, y, summary, max_width, line_height=14, font_name="Helvetica", font_size=11)
    y -= 14

    c.setFont("Helvetica-Bold", 13)
    c.drawString(left, y, "Key Developing Risk Indicators")
    y -= 18

    if focus_risks.empty:
        c.setFont("Helvetica", 10)
        c.drawString(left, y, "No significant risk indicators detected.")
    else:
        for _, row in focus_risks.iterrows():
            param = row["param"]
            interp = interpret_param(param)

            direction = row.get("direction", "→")
            eta_min = _fmt_eta(row.get("eta_to_min_days"))
            eta_max = _fmt_eta(row.get("eta_to_max_days"))

            if y < 140:
                c.showPage()
                y = page_h - 60

            c.setFont("Helvetica-Bold", 10)
            c.drawString(left, y, f"{param} ({interp['system']})  Trend: {direction}")
            
            # Mini trend chart (right side)
            has_chart = bool(focus_trends and str(param) in focus_trends)

            chart_w = 120
            chart_h = 16
            chart_lane = 0  # how much width we reserve on the right so text never collides

            if has_chart:
                c.setLineWidth(0.6)
                chart_x = page_w - right - chart_w
                _draw_sparkline(
                    c,
                    chart_x,
                    y,          # baseline
                    w=chart_w,
                    h=chart_h,
                    values=focus_trends.get(str(param)),
                )
                chart_lane = chart_w + 14  # chart width + gutter padding

            # Now that we know whether a chart exists, reserve space before writing wrapped text
            wrap_width = max_width - chart_lane

            y -= 14

            y = _draw_wrapped(
                c, left + 20, y,
                f"Observed trend suggests: {interp['meaning']}",
                wrap_width - 20,
                line_height=13, font_name="Helvetica", font_size=10,
            )

            y = _draw_wrapped(
                c, left + 20, y,
                f"Risk classification: {interp['risk_type']}",
                wrap_width - 20,
                line_height=13, font_name="Helvetica", font_size=10,
            )

            y = _draw_wrapped(
                c, left + 20, y,
                f"Estimated time to limits: min={eta_min} | max={eta_max}",
                wrap_width - 20,
                line_height=13, font_name="Helvetica", font_size=10,
            )

            c.setLineWidth(0.3)
            c.line(left, y + 10, page_w - right, y + 10)

            y -= 18

    # --- Footer (Page 2) ---
    _draw_footer(
        c,
        page_w,
        24,
        f"Engine {focus_engine_id} | Health {focus_score:.1f}",
        left,
        right,
    )

    # ======================
    # PAGE 3 — RECOMMENDATIONS
    # ======================
    c.showPage()
    y = page_h - 60

    c.setFont("Helvetica-Bold", 14)
    c.drawString(left, y, "Operational Recommendations")
    y -= 22

    c.setFont("Helvetica", 11)
    recommendations = [
        "No immediate shutdown or load reduction is recommended at this time.",
        "Prioritize inspection of the highest-risk subsystem during the next planned maintenance opportunity.",
        "Monitor key lubrication and cooling parameters for continued drift over the next 72 hours.",
        "Re-run AxiomIQ analysis after additional data is collected (ideally 7–14 days).",
    ]

    for rec in recommendations:
        y = _draw_wrapped(c, left, y, f"- {rec}", max_width, line_height=15, font_name="Helvetica", font_size=11)
        y -= 4

    if notes:
        y -= 14
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left, y, "Data Notes")
        y -= 14
        c.setFont("Helvetica", 10)
        for n in notes:
            y = _draw_wrapped(c, left, y, f"- {n}", max_width, line_height=13, font_name="Helvetica", font_size=10)

    # --- Footer (Page 3) ---
    _draw_footer(
        c,
        page_w,
        24,
        f"Version {run_config.get('version','')}" if run_config else "",
        left,
        right,
    )

    c.save()
    return out_path
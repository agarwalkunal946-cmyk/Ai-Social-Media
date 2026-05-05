from datetime import datetime, timezone
from html import escape
from pathlib import Path
from uuid import uuid4

from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import get_settings
from app.db.mongo import get_database
from app.services.alerts import sync_workspace_alerts
from app.services.dashboard_data import build_dashboard_snapshot, invalidate_dashboard_snapshot_cache


def _safe_text(value, fallback: str = "n/a") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _slugify(value: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in cleaned.split("-") if part)


def _format_dt(value: datetime) -> str:
    return value.strftime("%B %d, %Y %I:%M %p UTC")


def _platform_name(platform: str | None) -> str:
    mapping = {
        "youtube": "YouTube",
        "instagram": "Instagram",
        "x": "X / Twitter",
    }
    return mapping.get((platform or "").lower(), _safe_text(platform, "Platform"))


def _render_metric_cards(items: list[dict]) -> str:
    return "".join(
        (
            "<article class='metric-card'>"
            f"<p>{escape(_safe_text(item.get('label')))}</p>"
            f"<strong>{escape(_safe_text(item.get('value')))}</strong>"
            f"<span>{escape(_safe_text(item.get('delta'), ''))}</span>"
            "</article>"
        )
        for item in items
    )


def _render_rollups(items: list[dict]) -> str:
    if not items:
        return "<div class='empty-card'>No platform summaries are available yet.</div>"

    html = []
    for item in items:
        metric_rows = "".join(
            (
                "<div class='mini-metric-row'>"
                f"<span>{escape(_safe_text(metric.get('label')))}</span>"
                f"<strong>{escape(_safe_text(metric.get('value')))}</strong>"
                "</div>"
            )
            for metric in item.get("metrics") or []
        )
        html.append(
            "<article class='detail-card'>"
            f"<p class='eyebrow'>{escape(_safe_text(item.get('title')))}</p>"
            f"<h3>{escape(_safe_text(item.get('headline')))}</h3>"
            f"<div class='mini-metric-list'>{metric_rows}</div>"
            "</article>"
        )
    return "".join(html)


def _render_content_cards(items: list[dict]) -> str:
    if not items:
        return "<div class='empty-card'>No top content was available for this report.</div>"

    return "".join(
        (
            "<article class='detail-card'>"
            f"<p class='eyebrow'>{escape(_safe_text(item.get('platform')))}</p>"
            f"<h3>{escape(_safe_text(item.get('title')))}</h3>"
            f"<strong class='highlight'>{escape(_safe_text(item.get('metric')))}</strong>"
            f"<p class='body-copy'>{escape(_safe_text(item.get('insight'), ''))}</p>"
            "</article>"
        )
        for item in items
    )


def _render_recommendations(items: list[dict]) -> str:
    if not items:
        return "<div class='empty-card'>Recommendations will appear once more live data is available.</div>"

    return "".join(
        (
            "<article class='detail-card'>"
            f"<h3>{escape(_safe_text(item.get('title')))}</h3>"
            f"<p class='body-copy'>{escape(_safe_text(item.get('body'), ''))}</p>"
            "</article>"
        )
        for item in items
    )


def _render_connections(items: list[dict]) -> str:
    if not items:
        return "<div class='empty-card'>No connected accounts were included in this report.</div>"

    return "".join(
        (
            "<article class='detail-card compact-card'>"
            f"<p class='eyebrow'>{escape(_safe_text(item.get('platform')))}</p>"
            f"<h3>{escape(_safe_text(item.get('name')))}</h3>"
            f"<p class='body-copy'>{escape(_safe_text(item.get('status')))}{(' | ' + escape(_safe_text(item.get('handle')))) if item.get('handle') else ''}</p>"
            "</article>"
        )
        for item in items
    )


def _render_alerts(items: list[dict]) -> str:
    if not items:
        return "<div class='empty-card'>No alerts were active when this report was generated.</div>"

    html = []
    for item in items:
        severity = escape(_safe_text(item.get("severity"), "low")).lower()
        html.append(
            "<article class='detail-card alert-card'>"
            "<div class='row'>"
            f"<p class='eyebrow'>{escape(_safe_text(item.get('platform')))}</p>"
            f"<span class='pill pill-{severity}'>{severity}</span>"
            "</div>"
            f"<h3>{escape(_safe_text(item.get('title')))}</h3>"
            f"<p class='body-copy'>{escape(_safe_text(item.get('explanation'), ''))}</p>"
            f"<p class='highlight'>{escape(_safe_text(item.get('recommended_action'), ''))}</p>"
            "</article>"
        )
    return "".join(html)


def _render_summary_points(items: list[str]) -> str:
    if not items:
        return "<li>Live insights will appear here after more data is indexed.</li>"
    return "".join(f"<li>{escape(_safe_text(item))}</li>" for item in items)


def _render_bar_chart(items: list[dict], *, label_key: str, value_key: str, suffix: str = "") -> str:
    if not items:
        return "<div class='empty-card'>No chart data was available for this section.</div>"

    max_value = max(float(item.get(value_key) or 0) for item in items) or 1
    rows = []
    for item in items:
        value = float(item.get(value_key) or 0)
        width = max(8.0, (value / max_value) * 100)
        display_value = int(value) if value.is_integer() else round(value, 1)
        rows.append(
            "<div class='bar-row'>"
            f"<span>{escape(_safe_text(item.get(label_key)))}</span>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{width:.1f}%'></div></div>"
            f"<strong>{escape(_safe_text(str(display_value) + suffix))}</strong>"
            "</div>"
        )
    return "".join(rows)


def _build_report_data(snapshot: dict, alerts: list[dict], connections: list[dict], report_count: int) -> dict:
    overview = snapshot.get("overview") or []
    rollups = snapshot.get("platform_rollups") or []
    comparison = snapshot.get("platform_comparison") or []
    trend = snapshot.get("engagement_trend") or []
    sentiment = snapshot.get("sentiment_breakdown") or []
    top_content = snapshot.get("top_content") or []
    recommendations = snapshot.get("recommendations") or []
    hashtags = snapshot.get("trending_hashtags") or []
    explainable_ai = snapshot.get("explainable_ai") or {}
    chatbot = snapshot.get("chatbot") or {}
    predictive_analysis = snapshot.get("predictive_analysis") or {}
    high_severity_count = sum(1 for alert in alerts if str(alert.get("severity")).lower() == "high")
    audience_leader = max(comparison, key=lambda item: item.get("reach", 0), default=None)
    peak_day = max(trend, key=lambda item: item.get("value", 0), default=None)
    toxicity_value = (snapshot.get("toxicity_summary") or {}).get("label") or "n/a"

    coverage = [
        {
            "title": "Real-time analytics",
            "value": next((item.get("value") for item in overview if item.get("label") == "Interactions"), "0"),
            "detail": "Current interaction totals from the indexed content set.",
        },
        {
            "title": "Multi-platform view",
            "value": f"{len(connections)}/3",
            "detail": "Instagram, YouTube, and X are combined in one report view.",
        },
        {
            "title": "Sentiment and emotion",
            "value": next((item.get("value") for item in overview if item.get("label") == "Overall Mood"), "n/a"),
            "detail": "Audience tone inferred from captions, posts, and conversation text.",
        },
        {
            "title": "Toxicity detection",
            "value": toxicity_value,
            "detail": "Moderation risk stays visible when harmful-language signals are present.",
        },
        {
            "title": "Audience insights",
            "value": audience_leader.get("platform", "n/a") if audience_leader else "n/a",
            "detail": "Platform with the strongest current reach footprint.",
        },
        {
            "title": "Predictive analysis",
            "value": predictive_analysis.get("trend_direction", peak_day.get("day", "n/a") if peak_day else "n/a"),
            "detail": "Forecast direction derived from the recent engagement baseline versus the current momentum window.",
        },
        {
            "title": "AI recommendations",
            "value": str(len(recommendations)),
            "detail": "Publishing, content, and caption suggestions included in this report.",
        },
        {
            "title": "Crisis alerts",
            "value": str(high_severity_count),
            "detail": "High-severity negative spikes or moderation issues needing attention.",
        },
        {
            "title": "Trending hashtags",
            "value": str(len(hashtags)),
            "detail": "Recurring hashtags extracted from the strongest indexed content signals.",
        },
        {
            "title": "Explainable AI",
            "value": str(len(explainable_ai.get("factors") or [])),
            "detail": "Recommendations are backed by visible reach, sentiment, moderation, and content-topic factors.",
        },
        {
            "title": "Chatbot assistant",
            "value": str(len(chatbot.get("starter_questions") or [])),
            "detail": "The dashboard assistant can answer questions about timing, hashtags, audience, and crisis risk.",
        },
        {
            "title": "Automated reports",
            "value": str(report_count),
            "detail": "Total saved reports available for this workspace after this snapshot.",
        },
    ]

    summary_points = [
        f"{len(connections)} connected source(s) are included in this report snapshot.",
        f"{audience_leader.get('platform')} currently leads audience reach." if audience_leader else "Audience leader will appear here after more data loads.",
        f"{peak_day.get('day')} is the strongest engagement day in the current trend." if peak_day else "Trend peaks will appear here after more dated content is indexed.",
        f'Top content signal: "{top_content[0].get("title")}".' if top_content else "Top content will appear here once more posts are indexed.",
        f'Leading hashtag signal: {hashtags[0].get("tag")}.' if hashtags else "Hashtag momentum will appear here when recurring tags are detected.",
    ]

    return {
        "overview": overview,
        "platform_rollups": rollups,
        "platform_comparison": comparison,
        "engagement_trend": trend,
        "sentiment_breakdown": sentiment,
        "top_content": top_content,
        "recommendations": recommendations,
        "alerts": alerts[:6],
        "connections": connections,
        "coverage": coverage,
        "insights": summary_points,
    }


def build_report_html(report: dict) -> str:
    data = report.get("data") or {}
    title = escape(_safe_text(report.get("title"), "Insight Report"))
    period = escape(_safe_text(report.get("period"), "custom").title())
    generated = _format_dt(report.get("created_at") or datetime.now(timezone.utc))
    download_href = f"/api/reports/public/{report.get('public_token')}/download"
    metric_cards = _render_metric_cards(data.get("overview") or [])
    coverage_cards = _render_rollups(
        [
            {
                "title": item.get("title"),
                "headline": item.get("value"),
                "metrics": [{"label": "Detail", "value": item.get("detail")}],
            }
            for item in data.get("coverage") or []
        ]
    )
    platform_rollups = _render_rollups(data.get("platform_rollups") or [])
    top_content = _render_content_cards(data.get("top_content") or [])
    recommendations = _render_recommendations(data.get("recommendations") or [])
    alerts = _render_alerts(data.get("alerts") or [])
    connections = _render_connections(data.get("connections") or [])
    trend_chart = _render_bar_chart(data.get("engagement_trend") or [], label_key="day", value_key="value")
    sentiment_chart = _render_bar_chart(
        data.get("sentiment_breakdown") or [],
        label_key="name",
        value_key="value",
        suffix="%",
    )
    comparison_chart = _render_bar_chart(
        data.get("platform_comparison") or [],
        label_key="platform",
        value_key="reach",
    )
    insight_items = _render_summary_points(data.get("insights") or [])

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{title}</title>
      <style>
        :root {{
          color-scheme: dark;
          --card: rgba(255,255,255,0.05);
          --border: rgba(255,255,255,0.08);
          --text: #eef2ff;
          --muted: #94a3b8;
          --accent: #00e5ff;
          --accent-2: #34d399;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: "Segoe UI", sans-serif;
          background:
            radial-gradient(circle at top left, rgba(0,229,255,0.12), transparent 34%),
            radial-gradient(circle at top right, rgba(96,165,250,0.12), transparent 28%),
            linear-gradient(180deg, #07111f 0%, #0b1528 100%);
          color: var(--text);
          padding: 32px 18px 64px;
        }}
        .shell {{
          max-width: 1180px;
          margin: 0 auto;
          background: linear-gradient(180deg, rgba(7,17,31,0.88), rgba(10,20,36,0.96));
          border: 1px solid var(--border);
          border-radius: 32px;
          padding: 28px;
          box-shadow: 0 32px 80px rgba(0,0,0,0.32);
        }}
        .hero {{
          display: flex;
          flex-wrap: wrap;
          justify-content: space-between;
          gap: 20px;
          align-items: flex-start;
        }}
        .eyebrow {{
          margin: 0;
          font-size: 11px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          color: var(--muted);
        }}
        h1 {{
          margin: 10px 0 8px;
          font-size: clamp(2rem, 4vw, 3rem);
          line-height: 1.05;
        }}
        h2 {{
          margin: 0 0 16px;
          font-size: 1.2rem;
        }}
        h3 {{
          margin: 8px 0 0;
          font-size: 1rem;
          line-height: 1.35;
        }}
        p {{
          margin: 0;
          color: #d7e2f1;
        }}
        .subtle {{
          color: var(--muted);
          font-size: 0.95rem;
          line-height: 1.6;
          max-width: 760px;
        }}
        .meta-row {{
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 16px;
        }}
        .meta-pill {{
          border: 1px solid var(--border);
          background: rgba(255,255,255,0.04);
          border-radius: 999px;
          padding: 10px 14px;
          color: #dbeafe;
          font-size: 0.85rem;
        }}
        .actions {{
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }}
        .btn {{
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          border-radius: 999px;
          padding: 12px 16px;
          text-decoration: none;
          font-weight: 600;
          border: 1px solid transparent;
          cursor: pointer;
        }}
        .btn-primary {{
          background: linear-gradient(90deg, var(--accent), #38bdf8);
          color: #03131a;
        }}
        .btn-secondary {{
          background: rgba(255,255,255,0.05);
          color: var(--text);
          border-color: var(--border);
        }}
        .section {{
          margin-top: 28px;
        }}
        .grid {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
        }}
        .two-col {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 18px;
        }}
        .metric-card,
        .detail-card,
        .chart-card,
        .empty-card {{
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 22px;
          padding: 18px;
        }}
        .metric-card strong {{
          display: block;
          margin-top: 12px;
          font-size: clamp(1.7rem, 2.8vw, 2.35rem);
          line-height: 1;
        }}
        .metric-card span {{
          display: block;
          margin-top: 12px;
          color: #67e8f9;
          font-size: 0.86rem;
          line-height: 1.45;
        }}
        .body-copy {{
          margin-top: 10px;
          color: #d7e2f1;
          line-height: 1.65;
        }}
        .highlight {{
          display: inline-block;
          margin-top: 10px;
          color: var(--accent);
          font-weight: 700;
        }}
        .mini-metric-list {{
          display: grid;
          gap: 10px;
          margin-top: 16px;
        }}
        .mini-metric-row {{
          display: flex;
          justify-content: space-between;
          gap: 12px;
          border-radius: 16px;
          background: rgba(255,255,255,0.03);
          padding: 11px 12px;
          font-size: 0.9rem;
        }}
        .mini-metric-row span {{
          color: var(--muted);
        }}
        .compact-card {{
          padding-bottom: 16px;
        }}
        .alert-card .row {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }}
        .pill {{
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          padding: 6px 10px;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }}
        .pill-high {{
          background: rgba(244,63,94,0.14);
          color: #fb7185;
        }}
        .pill-medium {{
          background: rgba(251,191,36,0.14);
          color: #fbbf24;
        }}
        .pill-low {{
          background: rgba(52,211,153,0.14);
          color: #6ee7b7;
        }}
        .chart-card {{
          padding: 20px;
        }}
        .bar-row {{
          display: grid;
          grid-template-columns: 112px minmax(0, 1fr) max-content;
          gap: 12px;
          align-items: center;
          margin-top: 12px;
        }}
        .bar-row span {{
          color: #dbeafe;
          font-size: 0.88rem;
        }}
        .bar-row strong {{
          font-size: 0.88rem;
        }}
        .bar-track {{
          position: relative;
          overflow: hidden;
          height: 12px;
          border-radius: 999px;
          background: rgba(255,255,255,0.06);
        }}
        .bar-fill {{
          height: 100%;
          border-radius: 999px;
          background: linear-gradient(90deg, var(--accent), var(--accent-2));
        }}
        ul {{
          margin: 0;
          padding-left: 18px;
          color: #d7e2f1;
        }}
        li + li {{
          margin-top: 10px;
        }}
        .footer-note {{
          margin-top: 28px;
          color: var(--muted);
          font-size: 0.86rem;
        }}
        @media (max-width: 640px) {{
          body {{
            padding: 16px 12px 40px;
          }}
          .shell {{
            padding: 20px;
            border-radius: 24px;
          }}
          .hero {{
            flex-direction: column;
          }}
          .actions {{
            width: 100%;
          }}
          .actions .btn {{
            width: 100%;
          }}
          .bar-row {{
            grid-template-columns: 1fr;
            gap: 8px;
          }}
        }}
        @media print {{
          body {{
            padding: 0;
            background: #fff;
            color: #111827;
          }}
          .shell {{
            border: none;
            box-shadow: none;
            background: #fff;
            color: #111827;
          }}
          .metric-card,
          .detail-card,
          .chart-card,
          .empty-card {{
            background: #fff;
            border-color: #dbe3ef;
            break-inside: avoid;
          }}
          .actions {{
            display: none;
          }}
          .meta-pill {{
            color: #111827;
            background: #fff;
            border-color: #dbe3ef;
          }}
          .subtle,
          .body-copy,
          .mini-metric-row span,
          .footer-note,
          .eyebrow {{
            color: #475569;
          }}
          .bar-track {{
            background: #e2e8f0;
          }}
          .pill-high,
          .pill-medium,
          .pill-low {{
            color: #111827;
          }}
        }}
      </style>
    </head>
    <body>
      <main class="shell">
        <section class="hero">
          <div>
            <p class="eyebrow">{period} report</p>
            <h1>{title}</h1>
            <p class="subtle">This downloadable report mirrors the main dashboard with platform summaries, mood signals, audience trends, alerts, and AI recommendations in one presentation-ready view.</p>
            <div class="meta-row">
              <span class="meta-pill">Generated {generated}</span>
              <span class="meta-pill">{len(data.get("connections") or [])} connected account(s)</span>
              <span class="meta-pill">{len(data.get("alerts") or [])} active alert(s)</span>
            </div>
          </div>
          <div class="actions">
            <a class="btn btn-primary" href="{download_href}">Download HTML</a>
            <button class="btn btn-secondary" onclick="window.print()">Save as PDF</button>
          </div>
        </section>

        <section class="section">
          <h2>Overview</h2>
          <div class="grid">{metric_cards}</div>
        </section>

        <section class="section">
          <h2>Analytics coverage</h2>
          <div class="grid">{coverage_cards}</div>
        </section>

        <section class="section">
          <h2>Platform summaries</h2>
          <div class="grid">{platform_rollups}</div>
        </section>

        <section class="section">
          <h2>Executive summary</h2>
          <ul>{insight_items}</ul>
        </section>

        <section class="section two-col">
          <article class="chart-card">
            <h2>Engagement trend</h2>
            {trend_chart}
          </article>
          <article class="chart-card">
            <h2>Community mood</h2>
            {sentiment_chart}
          </article>
        </section>

        <section class="section">
          <h2>Platform comparison</h2>
          <article class="chart-card">{comparison_chart}</article>
        </section>

        <section class="section">
          <h2>Top content</h2>
          <div class="grid">{top_content}</div>
        </section>

        <section class="section">
          <h2>Recommendations</h2>
          <div class="grid">{recommendations}</div>
        </section>

        <section class="section two-col">
          <div>
            <h2>Connected accounts</h2>
            <div class="grid">{connections}</div>
          </div>
          <div>
            <h2>Alerts and notifications</h2>
            <div class="grid">{alerts}</div>
          </div>
        </section>

        <p class="footer-note">Public view generated by Synapse AI Social Intelligence. Open this page in any browser, download the HTML file, or use "Save as PDF" for sharing.</p>
      </main>
    </body>
    </html>
    """


async def generate_report_for_user(user: dict, period: str = "weekly") -> dict:
    settings = get_settings()
    db = get_database()
    snapshot = await build_dashboard_snapshot(user, force_refresh=True)
    await sync_workspace_alerts(user["id"])
    alerts = await db.alerts.find({"$or": [{"user_id": user["id"]}, {"user_id": None}]}).sort("timestamp", -1).to_list(length=6)
    connections_raw = await db.social_accounts.find({"user_id": user["id"]}).to_list(length=10)
    existing_reports = await db.reports.count_documents({"user_id": user["id"]})

    connections = [
        {
            "platform": _platform_name(item.get("platform")),
            "name": item.get("account_name") or item.get("handle") or item.get("platform"),
            "handle": item.get("handle"),
            "status": str(item.get("status") or "connected").replace("_", " ").title(),
        }
        for item in connections_raw
    ]

    data = _build_report_data(snapshot, alerts, connections, existing_reports + 1)
    report_id = uuid4().hex
    public_token = uuid4().hex
    created_at = datetime.now(timezone.utc)
    report = {
        "_id": report_id,
        "user_id": user["id"],
        "title": f"{user['display_name']} {period.title()} Insight Report",
        "period": period,
        "created_at": created_at,
        "public_token": public_token,
        "data": data,
    }

    html = build_report_html(report)
    file_path = settings.reports_dir / f"{report_id}.html"
    Path(file_path).write_text(html, encoding="utf-8")
    report["html_path"] = str(file_path)

    await db.reports.insert_one(report)
    await invalidate_dashboard_snapshot_cache(user["id"])
    return report


async def get_public_report(token: str) -> HTMLResponse | None:
    db = get_database()
    report = await db.reports.find_one({"public_token": token})
    if not report:
        return None
    return HTMLResponse(build_report_html(report))


async def get_report_download(token: str) -> FileResponse | None:
    db = get_database()
    report = await db.reports.find_one({"public_token": token})
    if not report:
        return None

    settings = get_settings()
    file_path = Path(report.get("html_path") or (settings.reports_dir / f"{report['_id']}.html"))
    file_path.write_text(build_report_html(report), encoding="utf-8")
    filename = f"{_slugify(report.get('title') or 'insight-report')}.html"
    return FileResponse(path=file_path, media_type="text/html; charset=utf-8", filename=filename)


async def delete_report_for_user(user_id: str, report_id: str) -> bool:
    db = get_database()
    report = await db.reports.find_one({"_id": report_id, "user_id": user_id})
    if not report:
        return False

    settings = get_settings()
    reports_dir = settings.reports_dir.resolve()
    raw_path = report.get("html_path")
    if raw_path:
        file_path = Path(raw_path).resolve()
        if file_path.exists() and reports_dir in file_path.parents:
            file_path.unlink()

    await db.reports.delete_one({"_id": report_id, "user_id": user_id})
    await invalidate_dashboard_snapshot_cache(user_id)
    return True


async def delete_report_as_admin(report_id: str) -> bool:
    db = get_database()
    report = await db.reports.find_one({"_id": report_id})
    if not report:
        return False

    settings = get_settings()
    reports_dir = settings.reports_dir.resolve()
    raw_path = report.get("html_path")
    if raw_path:
        file_path = Path(raw_path).resolve()
        if file_path.exists() and reports_dir in file_path.parents:
            file_path.unlink()

    await db.reports.delete_one({"_id": report_id})
    if report.get("user_id"):
        await invalidate_dashboard_snapshot_cache(report["user_id"])
    return True

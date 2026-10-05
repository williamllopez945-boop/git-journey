"""Renders the "bottom line" dashboard - the Main artboard of the Ledger
design canvas (docs/design/ledger.tokens.json's `canvas` link) - as one
self-contained static HTML page, built from the same recorded data
daily_review.py already summarizes.

Split the way the rest of this package is: build_dashboard() is a pure
function from already-loaded data (summarize_day's return value,
RISK_LIMITS, an optional account snapshot, research entries) to a plain
dict view model; render_html() turns that dict into markup. Only main()
touches the filesystem, and it only ever READS the runtime logs
(cycle_log.json, state.json, research_log.json - never written here) and
writes the single --out file it's given. It never calls the RobinHood
MCP tools.

Account value and open positions are not persisted anywhere in this
repo (they live at the broker), so the risk-cap section only fills in
when the caller passes an account snapshot the calling session already
fetched - a JSON file of the form
    {"as_of": "2026-10-05T19:30:00+00:00",
     "portfolio_value": 586.12,
     "positions": [{"asset": "BTC", "market_value": 101.5}, ...]}
Without one, the page says so rather than guessing.

Usage:
    python3 trading_agent/dashboard.py --date 2026-10-05 --out dashboard.html \\
        [--account-file account.json]
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_agent.daily_review import summarize_day, _is_protective_exit

# blocked_* gates driven by position/exposure limits or the whipsaw
# cooldown - the ones the owner can act on - drawn in the loss color;
# every other gate (no_position, volume, unprofitable, ...) in gate grey.
CAP_GATES = {"blocked_concurrent_cap", "blocked_aggregate_cap", "blocked_cooldown"}

MAX_RESEARCH_ITEMS = 4


def _fmt_pct(value):
    """Signed, 2 decimals, true minus sign (ledger.tokens.json format.percent)."""
    return f"{value:+.2f}%".replace("-", "−")


def _fmt_usd(value):
    sign = "−" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _day_position_pct(timestamp):
    """Where an ISO timestamp falls in its UTC day, 0-100."""
    t = datetime.fromisoformat(timestamp).astimezone(timezone.utc)
    seconds = t.hour * 3600 + t.minute * 60 + t.second
    return round(seconds / 86400 * 100, 1)


def _hhmm(timestamp):
    return datetime.fromisoformat(timestamp).astimezone(timezone.utc).strftime("%H:%M")


def _caps(limits, account):
    """Concurrent-position and aggregate-exposure usage against RISK_LIMITS,
    or None when no account snapshot was supplied."""
    if not account:
        return None
    portfolio_value = account["portfolio_value"]
    positions = account.get("positions", [])
    open_value = sum(p["market_value"] for p in positions)
    exposure = open_value / portfolio_value if portfolio_value > 0 else 0.0
    max_concurrent = limits["max_concurrent_positions"]
    max_aggregate = limits["max_aggregate_position_pct"]
    return {
        "as_of": account.get("as_of"),
        "portfolio_value": portfolio_value,
        "open_positions": len(positions),
        "max_concurrent_positions": max_concurrent,
        "concurrent_binding": len(positions) >= max_concurrent,
        "exposure_pct": exposure * 100,
        "max_aggregate_pct": max_aggregate * 100,
        "aggregate_binding": exposure >= max_aggregate,
    }


def _headline(summary, caps, halted):
    """The one-sentence bottom line, highest-priority condition first."""
    if halted:
        return ("HALTED", "Trading is halted for the rest of the day.",
                "The daily loss limit was reached; no new orders until the next UTC day.")
    if caps and (caps["concurrent_binding"] or caps["aggregate_binding"]):
        parts = []
        if caps["concurrent_binding"]:
            parts.append(f"{caps['open_positions']} of {caps['max_concurrent_positions']} positions")
        if caps["aggregate_binding"]:
            parts.append(f"{caps['exposure_pct']:.0f}% of a {caps['max_aggregate_pct']:.0f}% exposure cap")
        return ("CAPS BINDING", "New buys are blocked until a position closes.",
                "The account is at " + " and ".join(parts) + ".")
    pending = summary["num_recommended_pending"]
    if pending:
        noun = "order is" if pending == 1 else "orders are"
        return ("APPROVAL", f"{pending} {noun} waiting for your approval.",
                "Sized above auto_execute_max_pct of portfolio value, so not placed automatically.")
    return ("NO ACTION", "No owner action needed today.",
            f"{summary['num_executed']} trade(s) executed and {summary['num_blocked']} signal(s) "
            f"held by a gate.")


def build_dashboard(summary, limits, dry_run, exit_rules, account=None, halted=False,
                    research_entries=None, latest_backtest=None):
    """summary: daily_review.summarize_day's return value.
    limits: RISK_LIMITS. dry_run: config.DRY_RUN.
    exit_rules: {"stop_loss_pct", "take_profit_pct"} as fractions.
    account: optional snapshot (see module docstring).
    halted: RiskManager state's "halted" flag for the same day.
    research_entries: ResearchLogStore entries for the day (advisory).
    latest_backtest: optional {"file", "title"} of the newest backtest note.

    Returns a plain dict; render_html draws it."""
    caps = _caps(limits, account)
    status, headline, detail = _headline(summary, caps, halted)

    executed_marks = [
        {"pct": _day_position_pct(e["timestamp"]), "kind": "protective" if _is_protective_exit(e) else "executed",
         "label": f"{e['asset']} {_hhmm(e['timestamp'])}"}
        for e in summary["executed_entries"] + summary["protective_exit_entries"]
    ]
    blocked_marks = [
        {"pct": _day_position_pct(e["timestamp"]), "kind": "cap" if e["action"] in CAP_GATES else "gate",
         "label": f"{e['asset']} {e['action']} {_hhmm(e['timestamp'])}"}
        for e in summary["blocked_entries"]
    ]
    approval_marks = [
        {"pct": _day_position_pct(e["timestamp"]), "kind": "approval",
         "label": f"{e['asset']} recommended {_hhmm(e['timestamp'])}"}
        for e in summary["recommended_entries"]
    ]
    watch_marks = [
        {"pct": _day_position_pct(e["timestamp"]), "kind": "watch",
         "label": f"{e['asset']} {_fmt_pct(e['crossover_pct'])} {_hhmm(e['timestamp'])}"
         if isinstance(e.get("crossover_pct"), (int, float)) else e["asset"]}
        for e in summary["excellent_watch_entries"]
    ]

    gates = sorted(summary["blocked_by_gate"].items(), key=lambda kv: (-kv[1], kv[0]))
    top = gates[0][1] if gates else 0
    blocked_by_gate = [
        {"gate": gate.removeprefix("blocked_"), "count": count,
         "width_pct": round(count / top * 100) if top else 0, "is_cap": gate in CAP_GATES}
        for gate, count in gates
    ]
    cap_blocks = sum(g["count"] for g in blocked_by_gate if g["is_cap"])

    research = []
    for e in research_entries or []:
        if any(r["asset"] == e["asset"] for r in research):
            continue
        research.append({"asset": e["asset"], "summary": e["summary"]})
        if len(research) == MAX_RESEARCH_ITEMS:
            break

    sells = [t for t in summary["executed_trades"] if t["side"] == "sell"]
    buys = [t for t in summary["executed_trades"] if t["side"] == "buy"]

    return {
        "date": summary["date"],
        "live": not dry_run,
        "status": status,
        "headline": headline,
        "detail": detail,
        "pending_approval": summary["num_recommended_pending"],
        "watch_assets": sorted({e["asset"] for e in summary["excellent_watch_entries"]}),
        "tiles": {
            "account": caps["portfolio_value"] if caps else None,
            "account_as_of": caps["as_of"] if caps else None,
            "executed": summary["num_executed"],
            "executed_detail": f"{len(buys)} buy · {len(sells)} sell · {_fmt_usd(summary['total_notional'])}",
            "blocked": summary["num_blocked"],
            "blocked_detail": f"{cap_blocks} by caps or cooldown",
            "approval": summary["num_recommended_pending"],
            "protective": summary["num_protective_exits"],
            "protective_detail": (f"stop {exit_rules['stop_loss_pct'] * 100:g}% · "
                                  f"take {exit_rules['take_profit_pct'] * 100:g}%"),
        },
        "caps": caps,
        "timeline": [
            {"row": "Executed", "marks": executed_marks},
            {"row": "Approval", "marks": approval_marks},
            {"row": "Blocked", "marks": blocked_marks},
            {"row": "Watch", "marks": watch_marks},
        ],
        "blocked_by_gate": blocked_by_gate,
        "research": research,
        "latest_backtest": latest_backtest,
    }


def latest_backtest_note(directory):
    """{"file", "title"} for the newest backtest_*.md (by its dated
    filename) in directory, title being its first markdown heading, or
    None if there are none."""
    notes = sorted(Path(directory).glob("backtest_*.md"))
    if not notes:
        return None
    path = notes[-1]
    title = path.stem
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"#+\s+(.*)", line)
        if m:
            title = m.group(1).strip()
            break
    return {"file": path.name, "title": title}


# ---------------------------------------------------------------- rendering

# Continental theme, verbatim from docs/design/ledger.tokens.json.
_CSS = """
:root{--paper:#0B0B0D;--surface:#15151A;--rule:#2A2A31;--ink:#ECE6D8;--ink2:#B8B0A0;--ink3:#8C8577;
--on-fill:#0B0B0D;--brass:#C9A227;--gain:#D9B44A;--gain-strong:#F0D27A;--loss:#E5484D;--loss-tint:#2B1013;
--loss-strong:#F07A80;--gate:#A3A3AF;--gate-tint:#24242B;--watch:#2EC4B6;--watch-tint:#0F2A28;
--watch-strong:#5FE0D3;--approval:#D14BD8;--approval-tint:#2A1230;--approval-strong:#E98AEE;
--sans:'IBM Plex Sans',system-ui,sans-serif;--mono:'IBM Plex Mono',ui-monospace,monospace;--display:'Cinzel','Trajan Pro',serif}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);color-scheme:dark}
a{color:var(--gain)}a:hover{color:var(--gain-strong)}
.mono,code{font-family:var(--mono)}
.top{background:#000;border-bottom:1px solid var(--brass)}
.top nav{max-width:1240px;margin:0 auto;padding:12px 24px;display:flex;flex-wrap:wrap;gap:12px 24px;justify-content:space-between;align-items:center}
.brand{font-family:var(--display);font-size:18px;letter-spacing:.08em;color:var(--gain)}
.badge{display:inline-flex;align-items:center;gap:8px;padding:4px 10px;border-radius:4px;font-family:var(--mono);font-size:13px;font-weight:500}
.badge.live{background:var(--loss);color:var(--on-fill)}
.badge.dry{background:var(--gate-tint);color:var(--gate)}
.dot{width:8px;height:8px;border-radius:50%;background:currentColor}
main{max-width:1240px;margin:0 auto;padding:40px 24px 72px;display:flex;flex-direction:column;gap:28px}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:6px;padding:24px;display:flex;flex-direction:column;gap:16px}
.hero{border:2px solid var(--brass);padding:28px;gap:18px}
.label{font-family:var(--mono);font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2)}
.row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
.status{padding:4px 10px;border-radius:4px;font-family:var(--mono);font-size:13px;font-weight:500}
.status.binding,.status.halted{background:var(--loss-tint);color:var(--loss-strong)}
.status.approval{background:var(--approval-tint);color:var(--approval-strong)}
.status.ok{background:var(--gate-tint);color:var(--gate)}
h1{margin:0;font-family:var(--display);font-size:clamp(1.75rem,3.6vw,2.6rem);line-height:1.2;font-weight:600}
h2{margin:0;font-size:20px;font-weight:600}
.lede{margin:0;font-size:18px;line-height:1.55;color:var(--ink2);max-width:900px}
.chips{display:flex;flex-wrap:wrap;gap:10px}
.chip{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:4px;background:var(--gate-tint);color:var(--ink2);font-size:14px}
.chip.watch{background:var(--watch-tint);color:var(--watch-strong)}
.chip.approval{background:var(--approval-tint);color:var(--approval-strong)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--rule);border-radius:6px;padding:18px 20px;display:flex;flex-direction:column;gap:6px}
.tile .label{font-size:12px;letter-spacing:.06em}
.tile .value{font-family:var(--mono);font-size:34px;font-weight:500;line-height:1}
.tile .meta{font-size:13px;color:var(--ink3)}
.split{display:flex;flex-wrap:wrap;gap:20px}
.split>.card{flex:1 1 340px}
.split>.wide{flex:1.6 1 520px}
.head{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;align-items:baseline}
.head .mono{font-size:12px;color:var(--ink3)}
.cap{display:flex;flex-direction:column;gap:10px}
.cap .row{font-size:14px}
.over{color:var(--loss);font-weight:500}
.slots{display:flex;gap:6px}
.slot{flex:1;height:28px;border-radius:3px;background:var(--gate-tint)}
.slot.used{background:var(--gate)}
.slot.over{background:var(--loss)}
.divider{width:2px;background:var(--brass)}
.bar{position:relative;height:28px;background:var(--gate-tint);border-radius:3px;overflow:hidden}
.bar span{position:absolute;top:0;bottom:0}
.scale{display:flex;justify-content:space-between;font-family:var(--mono);font-size:12px;color:var(--ink3)}
.missing{color:var(--ink3);font-size:14px;margin:0}
.tl{display:flex;flex-direction:column;gap:10px}
.tl-row{display:flex;align-items:center;gap:12px}
.tl-name{width:76px;flex-shrink:0;font-size:13px;color:var(--ink2)}
.track{position:relative;flex:1;height:28px;border-bottom:1px solid var(--rule)}
.mark{position:absolute;top:9px;width:10px;height:10px;margin-left:-5px}
.mark.executed{top:7px;width:14px;height:14px;margin-left:-7px;border-radius:50%;background:var(--gain)}
.mark.protective{top:7px;width:14px;height:14px;margin-left:-7px;border-radius:50%;background:var(--loss)}
.mark.approval{border-radius:50%;border:2px solid var(--approval)}
.mark.cap{border-radius:2px;background:var(--loss)}
.mark.gate{border-radius:2px;background:var(--gate)}
.mark.watch{transform:rotate(45deg);background:var(--watch)}
.legend{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:13px;color:var(--ink2)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend .mark{position:static;margin:0}
.gates{display:flex;flex-direction:column;gap:12px;font-size:13px}
.gate-row{display:grid;grid-template-columns:minmax(0,1fr) 110px 28px;gap:10px;align-items:center}
.gate-bar{height:8px;background:var(--gate-tint)}
.gate-bar div{height:8px;background:var(--gate)}
.gate-bar div.cap{background:var(--loss)}
.num{font-family:var(--mono);text-align:right}
.research{display:flex;flex-direction:column;gap:12px;font-size:14px;line-height:1.5}
.research div{display:flex;flex-direction:column;gap:2px}
.research strong{font-weight:600}
.research span{color:var(--ink2)}
footer{max-width:1240px;margin:0 auto;padding:0 24px 40px;font-size:13px;color:var(--ink3)}
"""

_FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
          '<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600&amp;family=IBM+Plex+Mono:'
          'wght@400;500&amp;family=IBM+Plex+Sans:wght@400;500;600&amp;display=swap" rel="stylesheet">')

_STATUS_CLASS = {"CAPS BINDING": "binding", "HALTED": "halted", "APPROVAL": "approval", "NO ACTION": "ok"}


def _e(value):
    return html.escape(str(value), quote=True)


def _tile(label, value, meta, value_style=""):
    style = f' style="color:var({value_style})"' if value_style else ""
    return (f'<div class="tile"><span class="label">{_e(label)}</span>'
            f'<span class="value"{style}>{_e(value)}</span><span class="meta">{_e(meta)}</span></div>')


def _render_caps(caps):
    if caps is None:
        return ('<p class="missing">No account snapshot supplied, so position and exposure usage '
                'are not shown. Pass <code>--account-file</code> with the values the calling '
                'session fetched.</p>')
    n, cap = caps["open_positions"], caps["max_concurrent_positions"]
    slots = []
    for i in range(max(n, cap)):
        if i == cap:
            slots.append('<div class="divider"></div>')
        cls = "slot over" if i >= cap else "slot used" if i < n else "slot"
        slots.append(f'<div class="{cls}"></div>')
    conc_cls = ' class="mono over"' if caps["concurrent_binding"] else ' class="mono"'

    exposure, agg = caps["exposure_pct"], caps["max_aggregate_pct"]
    within = min(exposure, agg)
    beyond = max(min(exposure, 100) - agg, 0)
    agg_cls = ' class="mono over"' if caps["aggregate_binding"] else ' class="mono"'
    return (
        f'<div class="cap"><div class="row"><code>max_concurrent_positions</code>'
        f'<span{conc_cls}>{n} / {cap}</span></div><div class="slots">{"".join(slots)}</div></div>'
        f'<div class="cap"><div class="row"><code>max_aggregate_position_pct</code>'
        f'<span{agg_cls}>{exposure:.0f}% / {agg:.0f}%</span></div>'
        f'<div class="bar"><span style="left:0;width:{within:.1f}%;background:var(--gate)"></span>'
        f'<span style="left:{agg:.1f}%;width:{beyond:.1f}%;background:var(--loss)"></span>'
        f'<span style="left:{agg:.1f}%;width:2px;background:var(--brass)"></span></div>'
        f'<div class="scale"><span>0%</span><span>cap {agg:.0f}%</span><span>100%</span></div></div>'
    )


def _render_timeline(timeline):
    rows = []
    for row in timeline:
        marks = "".join(
            f'<span class="mark {_e(m["kind"])}" style="left:{m["pct"]:.1f}%" title="{_e(m["label"])}"></span>'
            for m in row["marks"])
        rows.append(f'<div class="tl-row"><span class="tl-name">{_e(row["row"])}</span>'
                    f'<div class="track">{marks}</div></div>')
    rows.append('<div class="tl-row"><span class="tl-name"></span><div class="scale" style="flex:1">'
                '<span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div></div>')
    return "".join(rows)


def render_html(view):
    """A complete, self-contained HTML document for build_dashboard's view."""
    t = view["tiles"]
    badge = ('<span class="badge live"><span class="dot"></span>LIVE · DRY_RUN = False</span>'
             if view["live"] else '<span class="badge dry"><span class="dot"></span>DRY_RUN = True</span>')

    chips = []
    if view["pending_approval"]:
        n = view["pending_approval"]
        chips.append(f'<span class="chip approval">{n} order{"" if n == 1 else "s"} awaiting approval</span>')
    else:
        chips.append('<span class="chip">0 orders awaiting approval</span>')
    if view["watch_assets"]:
        chips.append(f'<span class="chip watch">Watch: {_e(", ".join(view["watch_assets"]))} '
                     f'(not confirmed)</span>')

    account_value = _fmt_usd(t["account"]) if t["account"] is not None else "—"
    if t["account_as_of"]:
        as_of = datetime.fromisoformat(t["account_as_of"]).astimezone(timezone.utc)
        account_meta = f"as of {as_of:%Y-%m-%d %H:%M} UTC"
    else:
        account_meta = "no snapshot supplied"
    tiles = "".join([
        _tile("Account", account_value, account_meta),
        _tile("Executed", t["executed"], t["executed_detail"]),
        _tile("Blocked signals", t["blocked"], t["blocked_detail"], "--gate"),
        _tile("Awaiting approval", t["approval"], "oversized for auto-execute",
              "--approval" if t["approval"] else ""),
        _tile("Protective exits", t["protective"], t["protective_detail"]),
    ])

    if view["blocked_by_gate"]:
        gates = "".join(
            f'<div class="gate-row"><code>{_e(g["gate"])}</code><div class="gate-bar">'
            f'<div class="{"cap" if g["is_cap"] else ""}" style="width:{g["width_pct"]}%"></div></div>'
            f'<span class="num">{g["count"]}</span></div>'
            for g in view["blocked_by_gate"])
    else:
        gates = '<p class="missing">Nothing was blocked today.</p>'

    if view["research"]:
        research = "".join(f'<div><strong>{_e(r["asset"])}</strong><span>{_e(r["summary"])}</span></div>'
                           for r in view["research"])
    else:
        research = '<p class="missing">No research findings logged for this date.</p>'

    bt = view["latest_backtest"]
    backtest = (f'<div style="font-size:15px;font-weight:600">{_e(bt["title"])}</div>'
                f'<code style="font-size:13px;color:var(--ink3)">trading_agent/{_e(bt["file"])}</code>'
                if bt else '<p class="missing">No backtest notes found.</p>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trading dashboard · {_e(view["date"])}</title>
{_FONTS}
<style>{_CSS}</style>
</head>
<body>
<header class="top"><nav><span class="brand">LEDGER</span>{badge}</nav></header>
<main>
<section class="card hero">
<div class="row"><span class="label">Bottom line · {_e(view["date"])}</span>
<span class="status {_STATUS_CLASS[view["status"]]}">{_e(view["status"])}</span></div>
<h1>{_e(view["headline"])}</h1>
<p class="lede">{_e(view["detail"])}</p>
<div class="chips">{"".join(chips)}</div>
</section>
<section class="tiles">{tiles}</section>
<div class="split">
<section class="card"><div class="head"><h2>Risk caps</h2><span class="mono">RISK_LIMITS</span></div>
{_render_caps(view["caps"])}</section>
<section class="card wide"><div class="head"><h2>Today's decisions, UTC</h2></div>
<div class="tl">{_render_timeline(view["timeline"])}</div>
<div class="legend"><span><span class="mark executed"></span>executed</span>
<span><span class="mark protective"></span>protective exit</span>
<span><span class="mark approval"></span>awaiting approval</span>
<span><span class="mark cap"></span>blocked by cap or cooldown</span>
<span><span class="mark gate"></span>other gates</span>
<span><span class="mark watch"></span>excellent watch</span></div>
</section>
</div>
<div class="split">
<section class="card"><div class="head"><h2>Blocked, by gate</h2></div><div class="gates">{gates}</div></section>
<section class="card"><div class="head"><h2>Latest backtest note</h2></div>{backtest}</section>
<section class="card"><div class="head"><h2>Research to read</h2><span class="mono">advisory</span></div>
<div class="research">{research}</div></section>
</div>
</main>
<footer>Generated from cycle_log.json and state.json for {_e(view["date"])} (UTC). Read-only view; no orders are placed from this page.</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- CLI

def _load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    from trading_agent import config, exit_criteria

    here = Path(__file__).parent
    parser = argparse.ArgumentParser(description="Render the bottom-line dashboard as static HTML.")
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat(),
                        help="UTC date, YYYY-MM-DD (default: today)")
    parser.add_argument("--out", required=True, help="HTML file to write")
    parser.add_argument("--account-file", help="optional account snapshot JSON (see module docstring)")
    parser.add_argument("--cycle-log", default=str(here / "cycle_log.json"))
    parser.add_argument("--state", default=str(here / "state.json"))
    parser.add_argument("--research-log", default=str(here.parent / "research_agent" / "research_log.json"))
    parser.add_argument("--backtest-dir", default=str(here))
    args = parser.parse_args(argv)

    out = Path(args.out).resolve()
    protected = {Path(p).resolve() for p in (args.cycle_log, args.state, args.research_log)}
    if out in protected or out.suffix.lower() != ".html":
        parser.error("--out must be a separate .html file, never a runtime state/log file")

    # Read the JSON files directly rather than through CycleLogStore/
    # RiskManager/ResearchLogStore so nothing here can ever write them.
    cycle_entries = [e for e in _load_json(args.cycle_log, []) if e["timestamp"][:10] == args.date]
    state = _load_json(args.state, {})
    trade_log = state.get("trade_log", [])
    halted = bool(state.get("halted")) and state.get("date") == args.date
    research = [e for e in _load_json(args.research_log, []) if e["timestamp"][:10] == args.date]
    account = _load_json(args.account_file, None) if args.account_file else None

    view = build_dashboard(
        summarize_day(cycle_entries, trade_log, args.date),
        config.RISK_LIMITS,
        config.DRY_RUN,
        {"stop_loss_pct": exit_criteria.STOP_LOSS_PCT, "take_profit_pct": exit_criteria.TAKE_PROFIT_PCT},
        account=account,
        halted=halted,
        research_entries=research,
        latest_backtest=latest_backtest_note(args.backtest_dir),
    )
    out.write_text(render_html(view), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

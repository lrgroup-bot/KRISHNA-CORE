from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "core" / "web_validation.html"
SPATIAL_APP = ROOT / "app" / "spatial-ui" / "src" / "App.tsx"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def repair_canonical_ui() -> None:
    html = UI.read_text(encoding="utf-8")

    # 1) Keep upper-system labels visible. The previous override intentionally
    # clipped both the system name and state down to 1px, producing icon-only
    # controls and preventing the owner from understanding the rail.
    html = replace_once(
        html,
        ".miniGodRow{\n position:relative!important;flex:0 0 42px!important;width:42px!important;height:42px!important;min-width:42px!important;\n display:grid!important;place-items:center!important;padding:0!important;border-radius:13px!important;\n border:1px solid rgba(119,215,231,.14)!important;background:rgba(8,24,34,.78)!important;color:var(--kr-text)!important;\n box-shadow:inset 0 1px 0 rgba(255,255,255,.035)!important;cursor:pointer!important;transition:.16s ease!important;\n}",
        ".miniGodRow{\n position:relative!important;flex:0 0 auto!important;min-width:132px!important;height:46px!important;\n display:grid!important;grid-template-columns:26px minmax(72px,1fr) auto!important;align-items:center!important;gap:7px!important;\n padding:0 10px!important;border-radius:13px!important;\n border:1px solid rgba(119,215,231,.14)!important;background:rgba(8,24,34,.78)!important;color:var(--kr-text)!important;\n box-shadow:inset 0 1px 0 rgba(255,255,255,.035)!important;cursor:pointer!important;transition:.16s ease!important;\n}",
        "expand live-system rail controls",
    )
    html = replace_once(
        html,
        ".miniGodLogo{font-size:18px!important;line-height:1!important}.miniGodName,.miniGodState{position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip:rect(0 0 0 0)!important;white-space:nowrap!important}",
        ".miniGodLogo{font-size:17px!important;line-height:1!important}.miniGodName{display:block!important;min-width:0!important;overflow:hidden!important;text-overflow:ellipsis!important;white-space:nowrap!important;font-size:10px!important;font-weight:800!important;letter-spacing:.01em!important}.miniGodState{display:block!important;max-width:72px!important;overflow:hidden!important;text-overflow:ellipsis!important;white-space:nowrap!important;font-size:8px!important;color:#91aeb8!important;text-transform:uppercase!important}",
        "restore live-system labels",
    )

    # 2) Correct owner-facing state semantics. Healthy IDLE/READY is gold,
    # recovery is blue, owner wait is amber, and only blocked/error is red.
    html = replace_once(
        html,
        ".orbitDot{width:6px;height:6px;border-radius:50%;display:inline-block}.orbitDot.active{background:#53f0a5;box-shadow:0 0 10px rgba(83,240,165,.7)}.orbitDot.idle{background:#da5d66}",
        ".orbitDot{width:6px;height:6px;border-radius:50%;display:inline-block}.orbitDot.active{background:#53f0a5;box-shadow:0 0 10px rgba(83,240,165,.7)}.orbitDot.idle{background:#e6c66f;box-shadow:0 0 8px rgba(230,198,111,.35)}",
        "correct idle legend color",
    )
    html = replace_once(
        html,
        ".godLight.status-green{background:#53f0a5!important;box-shadow:0 0 10px rgba(83,240,165,.72)!important}\n.godLight.status-red{background:#cb4f5a!important;box-shadow:0 0 7px rgba(203,79,90,.28)!important}\n.godLight.status-yellow{background:#cb4f5a!important;box-shadow:0 0 7px rgba(203,79,90,.28)!important}",
        ".godLight.status-green{background:#53f0a5!important;box-shadow:0 0 10px rgba(83,240,165,.72)!important}\n.godLight.status-yellow{background:#e6c66f!important;box-shadow:0 0 9px rgba(230,198,111,.38)!important}\n.godLight.status-blue{background:#63a9ff!important;box-shadow:0 0 9px rgba(99,169,255,.38)!important}\n.godLight.status-amber{background:#f1a94d!important;box-shadow:0 0 9px rgba(241,169,77,.38)!important}\n.godLight.status-red{background:#cb4f5a!important;box-shadow:0 0 7px rgba(203,79,90,.28)!important}",
        "correct system state colors",
    )
    html = replace_once(
        html,
        "Live internal systems. Green = working now. Red = idle or not active. Select any system to see its latest activity and exact state.",
        "Live internal systems. WORKING = green. IDLE/READY = gold. HEALING/RECOVERING = blue. WAITING FOR PARTHA = amber. BLOCKED/ERROR = red. Select any system to see its latest activity and exact state.",
        "replace misleading system status copy",
    )

    # 3) Normal Sudarshan conversation should not ask the owner to manually
    # choose research/investigation routing. Preserve Inspect UI as an explicit
    # owner-facing visual verification action; internal investigate()/research()
    # functions remain available for KRISHNA orchestration.
    html = replace_once(
        html,
        '<div class="holoPanel"><div class="k">QUICK TOOLS</div><button class="ghost" onclick="investigate()">⌕ Investigate</button><button class="ghost" onclick="research()">⌁ Research</button><button class="ghost" onclick="inspectUI()">▣ Inspect UI</button></div>',
        '<div class="holoPanel"><div class="k">OWNER TOOLS</div><button class="ghost" onclick="inspectUI()">▣ Inspect UI</button></div>',
        "remove manual research routing from Sudarshan side rail",
    )
    html = replace_once(
        html,
        '<button class="tool" onclick="focusProjectSidebar()">◇ Project</button><button class="tool" onclick="investigate()">⌕ Investigate</button><button class="tool" onclick="research()">⌁ Research</button>',
        '<button class="tool" onclick="focusProjectSidebar()">◇ Project</button>',
        "remove manual research routing from normal composer",
    )

    UI.write_text(html, encoding="utf-8")


def remove_frontend_self_approval() -> None:
    app = SPATIAL_APP.read_text(encoding="utf-8")

    # The frontend may describe a request, but it must never manufacture the
    # executable approval bit itself. Remove each known caller-supplied path
    # explicitly so source drift fails loudly instead of being silently changed.
    app = replace_once(
        app,
        "          approved: true,\n",
        "",
        "remove Wi-Fi caller-supplied approval",
    )
    app = replace_once(
        app,
        ", approved: true, project: 'KRISHNA'",
        ", project: 'KRISHNA'",
        "remove plugin caller-supplied approval",
    )

    SPATIAL_APP.write_text(app, encoding="utf-8")


def main() -> None:
    repair_canonical_ui()
    remove_frontend_self_approval()
    print("Spatial Command OS phase-1 source repair applied.")
    print("No deploy performed. Run acceptance tests before any runtime promotion.")


if __name__ == "__main__":
    main()

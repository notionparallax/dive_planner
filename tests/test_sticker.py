import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dive_plan  # noqa: E402
import sticker  # noqa: E402
from scenario_helpers import (  # noqa: E402
    _SCENARIO_COLS,
    _b64_to_scenarios_df,
    _default_scenario_rows,
)


def _b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()


# ─── gas_role_at ──────────────────────────────────────────────────────────────
def test_gas_role_zones():
    assert sticker.gas_role_at(30, False, 21, 6) is None
    assert sticker.gas_role_at(21, False, 21, 6) == "lean"
    assert sticker.gas_role_at(6, False, 21, 6) == "rich"
    assert sticker.gas_role_at(0, False, 21, 6) == "rich"


def test_gas_role_lost():
    assert sticker.gas_role_at(6, "rich", 21, 6) == "lean"
    assert sticker.gas_role_at(9, "lean", 21, 6) is None
    assert sticker.gas_role_at(6, ["lean", "rich"], 21, 6) is None
    assert sticker.gas_role_at(6, True, 21, 6) is None


def test_gas_role_not_carried():
    assert sticker.gas_role_at(6, False, 21, None) == "lean"
    assert sticker.gas_role_at(6, False, None, None) is None


# ─── tolerant URL decoding ────────────────────────────────────────────────────
def test_legacy_rows_get_defaults():
    old = [{k: v for k, v in r.items() if k not in ("print", "short")}
           for r in _default_scenario_rows(50, 100)]
    df = _b64_to_scenarios_df(_b64(old), 50, 100)
    assert list(df.columns) == _SCENARIO_COLS
    assert len(df) == len(old)
    main = df[df["name"] == "Main"].iloc[0]
    longer = df[df["name"] == "Longer"].iloc[0]
    assert main["print"] and main["short"] == "Main"
    assert not longer["print"]


def test_partial_and_junk_rows_salvaged():
    rows = [{"name": "Custom", "depth": 45, "extra": "ignored"}, "junk", {"time": "+5"}]
    df = _b64_to_scenarios_df(_b64(rows), 50, 100)
    assert list(df["name"]) == ["Custom", "Scenario 3"]
    assert df.iloc[0]["depth"] == "45"
    assert bool(df.iloc[0]["enabled"]) and bool(df.iloc[0]["print"])
    assert df.iloc[0]["short"] == "Custo"


def test_undecodable_falls_back_to_defaults():
    df = _b64_to_scenarios_df("!!!not base64!!!", 50, 100)
    assert len(df) == len(_default_scenario_rows(50, 100))


# ─── rendering ────────────────────────────────────────────────────────────────
def test_render_real_plan_fits():
    results = []
    for short, d, t, lost in [("Main 🦈", 43, 29, False), ("D&L", 46, 32, False),
                              ("-50", 46, 32, "lean"), ("-100", 46, 32, "rich"),
                              ("Bnce", 43, 10, False), ("99", 43, 29, False)]:
        r = dive_plan.run_scenario(short, d, t, deco_gases_lost=lost, back_gas=(21, 0),
                                   lean_gas=(50, 0), rich_gas=(100, 0),
                                   lean_switch=21, rich_switch=6)
        r["short"] = short
        results.append(r)
    headers, rows = sticker.build_grid(results, lambda m: f"{m:.0f}m", 21, 6)
    assert rows[-1][0] == "0m"
    title = [sticker.TitleItem("Cave Dive 3", bold=True), sticker.TitleItem("06/11/26"),
             sticker.TitleItem("50%", sticker.LEAN), sticker.TitleItem("O2", sticker.RICH)]
    img, info = sticker.render_sticker(title, headers, rows)
    assert img.size == (sticker.STICKER_W, sticker.STICKER_H)
    assert img.mode == "1"
    assert info["fits"] and not info["warnings"]
    assert info["font_size"] >= 18


def test_overflow_warns():
    headers = [f"S{i}" for i in range(30)]
    rows = [(f"{d}m", [sticker.Cell("999 (99)")] * 30) for d in range(30)]
    _, info = sticker.render_sticker([sticker.TitleItem("x")], headers, rows)
    assert not info["fits"] and info["warnings"]

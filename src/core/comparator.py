"""
comparator.py — lógica de comparação multi-sheet, multi-ref.
Roda em thread separada e envia resultado via queue.
"""

import queue
import traceback

import pandas as pd


def run_compare(
    base_panel,
    ref_panels: list,
    join: str,
    case: bool,
    strip: bool,
    result_queue: queue.Queue,
) -> None:
    """
    Executa a comparação e envia o resultado pela fila.

    Mensagens enviadas:
        ("compare_done", dict[str, pd.DataFrame])
        ("compare_err",  str)
    """
    try:
        base_configs    = base_panel.get_configs()
        results: dict[str, pd.DataFrame] = {}

        # Coleta todas as configs de referência
        all_ref_configs = []
        for rp in ref_panels:
            for rc in rp.get_configs():
                rc["panel_label"] = rp._label
                all_ref_configs.append(rc)

        # Uma comparação por (base_sheet × ref_sheet)
        for bc in base_configs:
            bdf   = bc["df"][bc["cols"]].copy()
            bkey  = bc["key"]
            bname = bc["sheet_name"]

            if strip:
                bdf[bkey] = bdf[bkey].astype(str).str.strip()
            if case:
                bdf["__jk__"] = bdf[bkey].str.lower()

            for i, rc in enumerate(all_ref_configs, 1):
                rdf    = rc["df"].copy()
                rkey   = rc["key"]
                rlabel = f"{rc['panel_label']}:{rc['sheet_name']}"
                rcols  = list(dict.fromkeys([rkey] + rc["cols"]))
                rsub   = rdf[rcols].copy()

                if strip:
                    rsub[rkey] = rsub[rkey].astype(str).str.strip()

                rename = {
                    c: f"{c}[{rlabel}]"
                    for c in rsub.columns
                    if c != rkey and c in bdf.columns
                }
                if rename:
                    rsub = rsub.rename(columns=rename)

                if case:
                    rsub["__jk__"] = rsub[rkey].str.lower()
                    lon, ron = "__jk__", "__jk__"
                else:
                    lon, ron = bkey, rkey

                merged = bdf.merge(
                    rsub, how=join,
                    left_on=lon, right_on=ron,
                    suffixes=("", f"_dup{i}"),
                )

                merged["__match_any__"] = merged[rkey].notna()
                drop = ["__jk__", f"__jk___dup{i}"]
                if ron != lon:
                    drop.append(rkey)
                merged = merged.drop(columns=[c for c in drop if c in merged.columns])

                tab_label = f"{bname}  ↔  {rlabel}"
                results[tab_label] = merged

        result_queue.put(("compare_done", results))

    except Exception:
        result_queue.put(("compare_err", traceback.format_exc()))

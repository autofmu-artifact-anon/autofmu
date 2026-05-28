from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.patches import Rectangle


RUNS_DIR = Path("evaluator/runs")
DEFAULT_OUTPUT = Path("ablation_heatmap.pdf")

ABLATION_METHOD_ORDER = [
    "COMPASS",
    "Top-1 LLM Decomposition",
    "Rule Template Decomposition",
    "Heuristic Neighborhood",
    "Semantic Retrieval Only",
    "Graph Match Only",
    "Greedy Hybrid",
    "Static Rule Scheduler",
    "Greedy Multirate",
    "LLM-Generated Script",
]

GROUP_BOUNDARIES = [1, 4, 7]
GROUP_LABELS = [
    ("Reference", 0.0),
    ("Requirement\nDecomposition", 2.0),
    ("Units\nMatching", 5.0),
    ("Program\nConstruction", 8.0),
]
GROUP_LABEL_X = -2.45

PANELS = [
    (
        "Simple FMU",
        [
            ("Simple_Decision_Acc(%)", "Dec"),
            ("Simple_Exec_Succ(%)", "Succ"),
            ("Simple_Exec_Time(s)", "Time"),
            ("Simple_MAE", "MAE"),
            ("Simple_RMSE", "RMSE"),
            ("Simple_NRMSE", "NRMSE"),
        ],
    ),
    (
        "Complex FMU",
        [
            ("Complex_Decision_Acc(%)", "Dec"),
            ("Complex_Exec_Succ(%)", "Succ"),
            ("Complex_Exec_Time(s)", "Time"),
            ("Complex_MAE", "MAE"),
            ("Complex_RMSE", "RMSE"),
            ("Complex_NRMSE", "NRMSE"),
        ],
    ),
    (
        "Overall",
        [
            ("Overall_Decision_Acc(%)", "Dec"),
            ("Overall_Exec_Succ(%)", "Succ"),
            ("Overall_Exec_Time(s)", "Time"),
            ("Overall_MAE", "MAE"),
            ("Overall_RMSE", "RMSE"),
            ("Overall_NRMSE", "NRMSE"),
        ],
    ),
]

HIGHER_IS_BETTER = {
    "Simple_Decision_Acc(%)",
    "Simple_Exec_Succ(%)",
    "Complex_Decision_Acc(%)",
    "Complex_Exec_Succ(%)",
    "Overall_Decision_Acc(%)",
    "Overall_Exec_Succ(%)",
}

FORMAT_BY_COLUMN = {
    "Simple_Decision_Acc(%)": "{:.1f}",
    "Simple_Exec_Succ(%)": "{:.1f}",
    "Simple_Exec_Time(s)": "{:.2f}",
    "Simple_MAE": "{:.2f}",
    "Simple_RMSE": "{:.2f}",
    "Simple_NRMSE": "{:.3f}",
    "Complex_Decision_Acc(%)": "{:.1f}",
    "Complex_Exec_Succ(%)": "{:.1f}",
    "Complex_Exec_Time(s)": "{:.2f}",
    "Complex_MAE": "{:.2f}",
    "Complex_RMSE": "{:.2f}",
    "Complex_NRMSE": "{:.3f}",
    "Overall_Decision_Acc(%)": "{:.1f}",
    "Overall_Exec_Succ(%)": "{:.1f}",
    "Overall_Exec_Time(s)": "{:.2f}",
    "Overall_MAE": "{:.2f}",
    "Overall_RMSE": "{:.2f}",
    "Overall_NRMSE": "{:.3f}",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the ablation heatmap from a cross-method CSV.")
    parser.add_argument(
        "--input",
        default=None,
        help="Path to a cross-method CSV. Defaults to the newest *_cross_method.csv in evaluator/runs.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output PDF path. Defaults to {DEFAULT_OUTPUT}.",
    )
    parser.add_argument(
        "--preview-png",
        default=None,
        help="Optional PNG preview path.",
    )
    return parser


def _latest_cross_method_csv() -> Path:
    candidates = sorted(RUNS_DIR.glob("*_cross_method.csv"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No *_cross_method.csv found under {RUNS_DIR}")
    return candidates[-1]


def _load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _select_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    by_method = {str(row.get("Method") or "").strip(): row for row in rows}
    selected = []
    missing = []
    for method in ABLATION_METHOD_ORDER:
        row = by_method.get(method)
        if row is None:
            missing.append(method)
            continue
        selected.append(row)
    if missing:
        raise ValueError(f"Missing methods in CSV: {', '.join(missing)}")
    return selected


def _parse_float(row: Dict[str, str], key: str) -> float:
    raw = str(row.get(key) or "").strip()
    if not raw:
        return float("nan")
    return float(raw)


def _normalize_column(values: Sequence[float], higher_is_better: bool) -> List[float]:
    finite_values = [value for value in values if value == value]
    if not finite_values:
        return [0.0 for _ in values]
    col_min = min(finite_values)
    col_max = max(finite_values)
    if abs(col_max - col_min) < 1e-12:
        return [1.0 if value == value else 0.0 for value in values]
    normalized: List[float] = []
    for value in values:
        if value != value:
            normalized.append(0.0)
            continue
        if higher_is_better:
            normalized.append((value - col_min) / (col_max - col_min))
        else:
            normalized.append((col_max - value) / (col_max - col_min))
    return normalized


def _format_value(column_key: str, value: float) -> str:
    if value != value:
        return "NA"
    return FORMAT_BY_COLUMN[column_key].format(value)


def _build_panel_values(rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> List[List[float]]:
    matrix: List[List[float]] = []
    for row in rows:
        matrix.append([_parse_float(row, column) for column in columns])
    return matrix


def _build_panel_scores(values: Sequence[Sequence[float]], columns: Sequence[str]) -> List[List[float]]:
    by_column: List[List[float]] = []
    for idx, column in enumerate(columns):
        raw_column = [row[idx] for row in values]
        by_column.append(_normalize_column(raw_column, higher_is_better=column in HIGHER_IS_BETTER))
    scores: List[List[float]] = []
    for row_idx in range(len(values)):
        scores.append([by_column[col_idx][row_idx] for col_idx in range(len(columns))])
    return scores


def _draw_panel(
    ax: plt.Axes,
    title: str,
    rows: Sequence[Dict[str, str]],
    columns: Sequence[tuple[str, str]],
    show_y_labels: bool,
    cmap: colors.Colormap,
) -> None:
    column_keys = [column_key for column_key, _ in columns]
    column_labels = [column_label for _, column_label in columns]
    raw_values = _build_panel_values(rows, column_keys)
    score_values = _build_panel_scores(raw_values, column_keys)

    image = ax.imshow(score_values, cmap=cmap, vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xticks(range(len(column_labels)))
    ax.set_xticklabels(column_labels, fontsize=10)
    ax.set_yticks(range(len(rows)))
    if show_y_labels:
        ax.set_yticklabels([row["Method"] for row in rows], fontsize=10)
    else:
        ax.set_yticklabels([])

    ax.set_xticks([tick - 0.5 for tick in range(1, len(column_labels))], minor=True)
    ax.set_yticks([tick - 0.5 for tick in range(1, len(rows))], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="x", top=False, bottom=True, labeltop=False, labelbottom=True)
    ax.tick_params(axis="y", length=0)

    for boundary in GROUP_BOUNDARIES:
        ax.axhline(boundary - 0.5, color="#3b3b3b", linewidth=1.6)

    for row_idx, row in enumerate(raw_values):
        for col_idx, value in enumerate(row):
            score = score_values[row_idx][col_idx]
            text_color = "#17212b" if score < 0.68 else "white"
            ax.text(
                col_idx,
                row_idx,
                _format_value(column_keys[col_idx], value),
                ha="center",
                va="center",
                fontsize=7.2,
                color=text_color,
            )

    ax.add_patch(
        Rectangle(
            (-0.5, -0.5),
            len(column_labels),
            1.0,
            linewidth=2.2,
            edgecolor="#0f172a",
            facecolor="none",
        )
    )

    for spine in ax.spines.values():
        spine.set_visible(False)

    return image


def render_heatmap(csv_path: Path, output_path: Path, preview_png: Path | None = None) -> None:
    rows = _select_rows(_load_rows(csv_path))

    fig, axes = plt.subplots(
        1,
        len(PANELS),
        figsize=(18.2, 6.2),
        gridspec_kw={"wspace": 0.08, "left": 0.24, "right": 0.94, "top": 0.84, "bottom": 0.13},
    )
    axes = axes.ravel().tolist() if hasattr(axes, "ravel") else [axes]

    cmap = colors.LinearSegmentedColormap.from_list(
        "ablation_quality",
        ["#9f1239", "#f8d7a6", "#0f766e"],
    )

    for idx, (panel_title, columns) in enumerate(PANELS):
        image = _draw_panel(
            axes[idx],
            panel_title,
            rows,
            columns,
            show_y_labels=(idx == 0),
            cmap=cmap,
        )

    fig.suptitle("Ablation Heatmap from Latest Cross-Method Metrics", fontsize=16, fontweight="bold", y=0.96)
    fig.text(
        0.20,
        0.90,
        f"Source: {csv_path.as_posix()} | color = relative performance within each metric column",
        fontsize=9.5,
        color="#334155",
    )

    for label, y in GROUP_LABELS:
        axes[0].text(
            GROUP_LABEL_X,
            y,
            label,
            ha="right",
            va="center",
            fontsize=9.5,
            fontweight="bold",
            color="#334155",
            transform=axes[0].transData,
        )

    colorbar = fig.colorbar(image, ax=axes, fraction=0.025, pad=0.012)
    colorbar.set_label("Column-wise relative score", fontsize=10)
    colorbar.ax.tick_params(labelsize=9)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    if preview_png is not None:
        preview_png.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(preview_png, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    csv_path = Path(args.input).resolve() if args.input else _latest_cross_method_csv().resolve()
    output_path = Path(args.output).resolve()
    preview_png = Path(args.preview_png).resolve() if args.preview_png else None

    render_heatmap(csv_path=csv_path, output_path=output_path, preview_png=preview_png)
    print(f"Wrote {output_path}")
    if preview_png is not None:
        print(f"Wrote {preview_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

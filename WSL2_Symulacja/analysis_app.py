"""
Analiza klastrowania i wymiaru fraktalnego 3D
dla danych z symulacji Geant4 (detektor 101x101).

Wymagania: PyQt6, numpy, pandas, matplotlib, scikit-learn
"""

import sys
import os
import re
import numpy as np
import pandas as pd
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QFileDialog, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QSlider, QSpinBox, QDoubleSpinBox,
    QSplitter, QHeaderView, QMessageBox, QFrame, QSizePolicy,
    QProgressBar, QComboBox
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import colormaps
from sklearn.cluster import DBSCAN


# ─────────────────────────────────────────────────────────────────
# LOGIKA OBLICZENIOWA — czyste funkcje
# ─────────────────────────────────────────────────────────────────

def load_csv(path: str) -> pd.DataFrame:
    """Załaduj CSV z danymi detektora. Ignoruje linie metadanych (# ...)."""
    df = pd.read_csv(path, comment='#')
    df.columns = [c.strip() for c in df.columns]
    return df


def build_grid(df: pd.DataFrame, grid_size: int = 101) -> np.ndarray:
    """Buduje pełną siatkę 2D (101x101) z rzadkich danych CSV."""
    half = grid_size // 2  # 50
    grid = np.zeros((grid_size, grid_size), dtype=float)
    for _, row in df.iterrows():
        xi = int(row['X']) + half
        yi = int(row['Y']) + half
        if 0 <= xi < grid_size and 0 <= yi < grid_size:
            grid[yi, xi] = row['Hits']
    return grid


def extract_metadata(path: str) -> dict:
    """Wyciąga metadane z ostatnich linii pliku CSV."""
    meta = {}
    with open(path, 'r') as f:
        for line in f:
            if line.startswith('# METADATA:'):
                parts = line.replace('# METADATA:', '').strip().split(',')
                for part in parts:
                    k, v = part.strip().split('=')
                    meta[k.strip()] = v.strip()
    return meta


def run_dbscan(df: pd.DataFrame, eps: float, min_samples: int) -> dict:
    """
    Wykonuje DBSCAN na pozycjach detektorów z trafień (Hits > 0).
    Zwraca dict z wynikami: labels, n_clusters, stats per cluster.
    """
    hit_df = df[df['Hits'] > 0].copy()
    if hit_df.empty:
        return {'n_clusters': 0, 'labels': np.array([]), 'hit_df': hit_df, 'cluster_stats': []}

    coords = hit_df[['X', 'Y']].values
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    labels = clustering.labels_
    hit_df['Cluster'] = labels

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    cluster_stats = []
    for cid in sorted(set(labels)):
        mask = labels == cid
        cluster_data = hit_df[mask]
        stats = {
            'id': cid,
            'name': f'Klaster {cid}' if cid >= 0 else 'Szum',
            'n_detectors': int(mask.sum()),
            'total_hits': int(cluster_data['Hits'].sum()),
            'mean_hits': float(cluster_data['Hits'].mean()),
            'center_x': float(cluster_data['X'].mean()),
            'center_y': float(cluster_data['Y'].mean()),
        }
        cluster_stats.append(stats)

    return {
        'n_clusters': n_clusters,
        'labels': labels,
        'hit_df': hit_df,
        'cluster_stats': cluster_stats,
    }


def compute_fractal_dimension_3d(grid: np.ndarray) -> dict:
    """
    Oblicza wymiar fraktalny 3D metodą box-counting.

    Powierzchnia (X, Y, Hits) jest normalizowana do sześcianu [0,1]^3.
    Dla kolejnych rozmiarów pudełka epsilon liczymy ile pudełek
    przecina powierzchnię.
    """
    ny, nx = grid.shape
    max_hits = grid.max()
    if max_hits == 0:
        return {'dimension': 0.0, 'epsilons': [], 'counts': [], 'r_squared': 0.0}

    # Normalizacja do [0, 1]^3
    norm_grid = grid / max_hits

    # Rozmiary pudełek: od dużych do małych
    # Używamy potęg 2 dla czystości podziału
    max_exp = int(np.floor(np.log2(min(nx, ny))))
    box_sizes = [2 ** k for k in range(1, max_exp + 1)]
    box_sizes = [s for s in box_sizes if s <= min(nx, ny) // 2]

    if len(box_sizes) < 2:
        return {'dimension': 0.0, 'epsilons': [], 'counts': [], 'r_squared': 0.0}

    epsilons = []
    counts = []

    for box_size in box_sizes:
        eps_spatial = box_size / max(nx, ny)
        eps_z = eps_spatial  # Taki sam rozmiar w Z (znormalizowane)
        count = 0

        for iy in range(0, ny, box_size):
            for ix in range(0, nx, box_size):
                # Wycinek siatki w tym pudełku
                block = norm_grid[iy:iy + box_size, ix:ix + box_size]
                if block.size == 0:
                    continue

                z_min = block.min()
                z_max = block.max()

                # Ile pudełek w Z potrzeba, żeby pokryć zakres [z_min, z_max]?
                k_min = int(np.floor(z_min / eps_z))
                k_max = int(np.floor(z_max / eps_z))
                count += max(k_max - k_min + 1, 1)

        epsilons.append(eps_spatial)
        counts.append(count)

    # Regresja liniowa log-log
    log_inv_eps = np.log(1.0 / np.array(epsilons))
    log_counts = np.log(np.array(counts))

    coeffs = np.polyfit(log_inv_eps, log_counts, 1)
    dimension = coeffs[0]

    # R²
    y_pred = np.polyval(coeffs, log_inv_eps)
    ss_res = np.sum((log_counts - y_pred) ** 2)
    ss_tot = np.sum((log_counts - np.mean(log_counts)) ** 2)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        'dimension': dimension,
        'epsilons': epsilons,
        'counts': counts,
        'r_squared': r_squared,
        'coeffs': coeffs,
    }


def parse_thickness_from_filename(filename: str) -> str:
    """Wyciąga grubość z nazwy pliku, np. 'results_1.1cm_1.csv' -> '1.1cm'."""
    m = re.search(r'results_(.+?)_\d+\.csv', filename)
    if m:
        return m.group(1)
    return filename


def run_batch_fractal(folder: str, progress_callback=None) -> list:
    """
    Przetwarza wszystkie pliki CSV w folderze.
    Zwraca listę dict z wynikami per grubość.
    """
    csv_files = sorted(Path(folder).glob('results_*.csv'))
    if not csv_files:
        return []

    results = []
    for i, csv_path in enumerate(csv_files):
        if progress_callback:
            progress_callback(i, len(csv_files), csv_path.name)

        try:
            df = load_csv(str(csv_path))
            grid = build_grid(df)
            meta = extract_metadata(str(csv_path))
            frac = compute_fractal_dimension_3d(grid)

            thickness_str = meta.get('thickness', parse_thickness_from_filename(csv_path.name))
            # Parsuj wartość numeryczną do sortowania
            thickness_num = float(re.sub(r'[^\d.]', '', thickness_str))

            results.append({
                'file': csv_path.name,
                'thickness_str': thickness_str,
                'thickness_num': thickness_num,
                'dimension': frac['dimension'],
                'r_squared': frac['r_squared'],
                'total_hits': int(df['Hits'].sum()),
                'epsilons': frac.get('epsilons', []),
                'counts': frac.get('counts', []),
            })
        except Exception as e:
            print(f'Błąd przetwarzania {csv_path.name}: {e}')

    # Sortuj po grubości
    results.sort(key=lambda r: r['thickness_num'])

    if progress_callback:
        progress_callback(len(csv_files), len(csv_files), 'Gotowe')

    return results


def export_batch_results(results: list, output_dir: str):
    """
    Eksportuje wyniki batch:
    1. fractal_dimensions.csv — podsumowanie (grubość, D, R², hits)
    2. fractal_<grubość>.csv — box-counting per grubość
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Podsumowanie
    summary_rows = []
    for r in results:
        summary_rows.append({
            'thickness': r['thickness_str'],
            'thickness_cm': r['thickness_num'],
            'fractal_dimension': round(r['dimension'], 6),
            'r_squared': round(r['r_squared'], 6),
            'total_hits': r['total_hits'],
        })
    pd.DataFrame(summary_rows).to_csv(out / 'fractal_dimensions.csv', index=False)

    # 2. Pliki per grubość
    for r in results:
        if not r['epsilons']:
            continue
        safe_name = r['thickness_str'].replace(' ', '')
        rows = []
        for eps, cnt in zip(r['epsilons'], r['counts']):
            rows.append({
                'epsilon': eps,
                'N_epsilon': cnt,
                'log_inv_epsilon': float(np.log(1.0 / eps)),
                'log_N': float(np.log(cnt)),
            })
        pd.DataFrame(rows).to_csv(out / f'fractal_{safe_name}.csv', index=False)

    return str(out)


# ─────────────────────────────────────────────────────────────────
# KOMPONENTY UI
# ─────────────────────────────────────────────────────────────────

DARK_BG = "#1a1a2e"
DARK_CARD = "#16213e"
DARK_ACCENT = "#0f3460"
ACCENT_COLOR = "#e94560"
TEXT_COLOR = "#eaeaea"
MUTED_COLOR = "#8892a0"

STYLESHEET = f"""
    QMainWindow {{
        background-color: {DARK_BG};
    }}
    QTabWidget::pane {{
        background: {DARK_BG};
        border: 1px solid {DARK_ACCENT};
        border-radius: 8px;
    }}
    QTabBar::tab {{
        background: {DARK_CARD};
        color: {MUTED_COLOR};
        padding: 10px 24px;
        margin-right: 2px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: 600;
        font-size: 13px;
    }}
    QTabBar::tab:selected {{
        background: {DARK_ACCENT};
        color: {TEXT_COLOR};
    }}
    QGroupBox {{
        background: {DARK_CARD};
        border: 1px solid {DARK_ACCENT};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 20px;
        font-weight: 600;
        color: {TEXT_COLOR};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}
    QPushButton {{
        background-color: {ACCENT_COLOR};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: #ff6b81;
    }}
    QPushButton:disabled {{
        background-color: #444;
        color: #888;
    }}
    QLabel {{
        color: {TEXT_COLOR};
        font-size: 13px;
    }}
    QTableWidget {{
        background-color: {DARK_CARD};
        color: {TEXT_COLOR};
        border: 1px solid {DARK_ACCENT};
        border-radius: 6px;
        gridline-color: {DARK_ACCENT};
        font-size: 12px;
    }}
    QTableWidget::item {{
        padding: 4px;
    }}
    QHeaderView::section {{
        background-color: {DARK_ACCENT};
        color: {TEXT_COLOR};
        padding: 6px;
        border: none;
        font-weight: 600;
    }}
    QSlider::groove:horizontal {{
        background: {DARK_ACCENT};
        height: 6px;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {ACCENT_COLOR};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    QSpinBox, QDoubleSpinBox {{
        background: {DARK_CARD};
        color: {TEXT_COLOR};
        border: 1px solid {DARK_ACCENT};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QComboBox {{
        background: {DARK_CARD};
        color: {TEXT_COLOR};
        border: 1px solid {DARK_ACCENT};
        border-radius: 4px;
        padding: 4px 8px;
    }}
"""


def make_figure(dark: bool = True) -> Figure:
    """Tworzy figurę matplotlib z ciemnym tłem."""
    fig = Figure(facecolor=DARK_CARD if dark else 'white', dpi=100)
    ax = fig.add_subplot(111)
    if dark:
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors=TEXT_COLOR)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        ax.title.set_color(TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_color(DARK_ACCENT)
    return fig


def result_label(text: str, value: str) -> QLabel:
    """Etykieta z wynikiem w stylu: 'text: value'."""
    lbl = QLabel(f"<b style='color:{MUTED_COLOR}'>{text}:</b> "
                 f"<span style='color:{ACCENT_COLOR}; font-size:15px'>{value}</span>")
    return lbl


# ─────────────────────────────────────────────────────────────────
# ZAKŁADKA 1: DANE
# ─────────────────────────────────────────────────────────────────

class DataTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df = None
        self.grid = None
        self.file_path = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        self.btn_load = QPushButton("📂  Załaduj CSV")
        self.btn_load.clicked.connect(self._load_file)
        self.lbl_file = QLabel("Nie załadowano pliku")
        self.lbl_file.setStyleSheet(f"color: {MUTED_COLOR}; font-style: italic;")
        header.addWidget(self.btn_load)
        header.addWidget(self.lbl_file, 1)
        layout.addLayout(header)

        # Metadata
        self.lbl_meta = QLabel("")
        layout.addWidget(self.lbl_meta)

        # Splitter: tabela + heatmapa
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tabela
        table_group = QGroupBox("Surowe dane")
        tl = QVBoxLayout(table_group)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Hits"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tl.addWidget(self.table)
        splitter.addWidget(table_group)

        # Heatmapa
        heatmap_group = QGroupBox("Heatmapa trafień")
        hl = QVBoxLayout(heatmap_group)
        self.fig_heatmap = make_figure()
        self.canvas_heatmap = FigureCanvas(self.fig_heatmap)
        hl.addWidget(self.canvas_heatmap)
        splitter.addWidget(heatmap_group)

        splitter.setSizes([300, 500])
        layout.addWidget(splitter, 1)

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik CSV", "",
            "CSV (*.csv);;Wszystkie (*)"
        )
        if not path:
            return

        try:
            self.df = load_csv(path)
            self.grid = build_grid(self.df)
            self.file_path = path
            meta = extract_metadata(path)

            self.lbl_file.setText(os.path.basename(path))
            self.lbl_file.setStyleSheet(f"color: {TEXT_COLOR}; font-weight: bold;")

            meta_text = " | ".join(f"<b>{k}</b>: {v}" for k, v in meta.items())
            meta_text += f" | <b>detektory z trafień</b>: {len(self.df)}"
            self.lbl_meta.setText(meta_text)

            self._fill_table()
            self._draw_heatmap()

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się załadować pliku:\n{e}")

    def _fill_table(self):
        self.table.setRowCount(len(self.df))
        for i, (_, row) in enumerate(self.df.iterrows()):
            for j, col in enumerate(['X', 'Y', 'Hits']):
                item = QTableWidgetItem(str(int(row[col])))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, j, item)

    def _draw_heatmap(self):
        self.fig_heatmap.clear()
        ax = self.fig_heatmap.add_subplot(111)
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(DARK_ACCENT)

        im = ax.imshow(
            self.grid, origin='lower', cmap='inferno',
            extent=[-50.5, 50.5, -50.5, 50.5], aspect='equal',
            interpolation='nearest'
        )
        cb = self.fig_heatmap.colorbar(im, ax=ax, shrink=0.8)
        cb.ax.yaxis.set_tick_params(color=TEXT_COLOR)
        cb.ax.yaxis.set_ticklabels(
            cb.ax.yaxis.get_ticklabels(), color=TEXT_COLOR, fontsize=9
        )
        cb.set_label("Trafienia", color=TEXT_COLOR, fontsize=11)

        ax.set_xlabel("X (indeks detektora)", color=TEXT_COLOR, fontsize=11)
        ax.set_ylabel("Y (indeks detektora)", color=TEXT_COLOR, fontsize=11)
        ax.set_title("Rozkład trafień", color=TEXT_COLOR, fontsize=13, fontweight='bold')

        self.fig_heatmap.tight_layout()
        self.canvas_heatmap.draw()


# ─────────────────────────────────────────────────────────────────
# ZAKŁADKA 2: KLASTROWANIE
# ─────────────────────────────────────────────────────────────────

class ClusterTab(QWidget):
    def __init__(self, data_tab: DataTab):
        super().__init__()
        self.data_tab = data_tab
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Parametry
        params_group = QGroupBox("Parametry DBSCAN")
        pl = QHBoxLayout(params_group)

        # eps
        pl.addWidget(QLabel("eps:"))
        self.spin_eps = QDoubleSpinBox()
        self.spin_eps.setRange(0.5, 20.0)
        self.spin_eps.setValue(2.0)
        self.spin_eps.setSingleStep(0.5)
        self.spin_eps.setFixedWidth(80)
        pl.addWidget(self.spin_eps)

        pl.addSpacing(20)

        # min_samples
        pl.addWidget(QLabel("min_samples:"))
        self.spin_min = QSpinBox()
        self.spin_min.setRange(1, 50)
        self.spin_min.setValue(3)
        self.spin_min.setFixedWidth(80)
        pl.addWidget(self.spin_min)

        pl.addSpacing(20)

        self.btn_run = QPushButton("▶  Analizuj klastry")
        self.btn_run.clicked.connect(self._run_analysis)
        pl.addWidget(self.btn_run)
        pl.addStretch()

        layout.addWidget(params_group)

        # Wyniki + wykres
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Wyniki
        results_group = QGroupBox("Wyniki")
        rl = QVBoxLayout(results_group)
        self.lbl_n_clusters = result_label("Liczba klastrów", "—")
        self.lbl_noise = result_label("Punkty szumu", "—")
        self.lbl_avg_size = result_label("Śr. rozmiar klastra", "—")
        rl.addWidget(self.lbl_n_clusters)
        rl.addWidget(self.lbl_noise)
        rl.addWidget(self.lbl_avg_size)

        rl.addSpacing(10)
        rl.addWidget(QLabel(f"<b style='color:{MUTED_COLOR}'>Szczegóły klastrów:</b>"))

        self.cluster_table = QTableWidget()
        self.cluster_table.setColumnCount(5)
        self.cluster_table.setHorizontalHeaderLabels([
            "ID", "Detektory", "Σ trafień", "Śr. trafień", "Centrum (X,Y)"
        ])
        self.cluster_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        rl.addWidget(self.cluster_table, 1)
        splitter.addWidget(results_group)

        # Wykres
        plot_group = QGroupBox("Wizualizacja klastrów")
        pl2 = QVBoxLayout(plot_group)
        self.fig_cluster = make_figure()
        self.canvas_cluster = FigureCanvas(self.fig_cluster)
        pl2.addWidget(self.canvas_cluster)
        splitter.addWidget(plot_group)

        splitter.setSizes([350, 500])
        layout.addWidget(splitter, 1)

    def _run_analysis(self):
        if self.data_tab.df is None:
            QMessageBox.warning(self, "Brak danych",
                                'Najpierw załaduj plik CSV w zakładce "Dane".')
            return

        eps = self.spin_eps.value()
        min_samples = self.spin_min.value()
        result = run_dbscan(self.data_tab.df, eps, min_samples)

        # Aktualizuj etykiety
        self.lbl_n_clusters.setText(
            f"<b style='color:{MUTED_COLOR}'>Liczba klastrów:</b> "
            f"<span style='color:{ACCENT_COLOR}; font-size:15px'>{result['n_clusters']}</span>"
        )

        noise_count = int(np.sum(result['labels'] == -1)) if len(result['labels']) > 0 else 0
        self.lbl_noise.setText(
            f"<b style='color:{MUTED_COLOR}'>Punkty szumu:</b> "
            f"<span style='color:{ACCENT_COLOR}; font-size:15px'>{noise_count}</span>"
        )

        real_clusters = [s for s in result['cluster_stats'] if s['id'] >= 0]
        avg_size = np.mean([s['n_detectors'] for s in real_clusters]) if real_clusters else 0
        self.lbl_avg_size.setText(
            f"<b style='color:{MUTED_COLOR}'>Śr. rozmiar klastra:</b> "
            f"<span style='color:{ACCENT_COLOR}; font-size:15px'>{avg_size:.1f} det.</span>"
        )

        # Tabela
        self.cluster_table.setRowCount(len(result['cluster_stats']))
        for i, s in enumerate(result['cluster_stats']):
            vals = [
                s['name'],
                str(s['n_detectors']),
                str(s['total_hits']),
                f"{s['mean_hits']:.1f}",
                f"({s['center_x']:.1f}, {s['center_y']:.1f})"
            ]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.cluster_table.setItem(i, j, item)

        # Wykres
        self._draw_clusters(result)

    def _draw_clusters(self, result: dict):
        self.fig_cluster.clear()
        ax = self.fig_cluster.add_subplot(111)
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(DARK_ACCENT)

        hit_df = result['hit_df']
        labels = result['labels']

        if len(hit_df) == 0:
            ax.set_title("Brak danych", color=TEXT_COLOR)
            self.canvas_cluster.draw()
            return

        unique_labels = sorted(set(labels))
        cmap = colormaps.get_cmap('tab20')

        # Logarytmiczne skalowanie rozmiaru punktów (zakres 4–40 px)
        all_hits = hit_df['Hits'].values
        log_hits = np.log1p(all_hits)
        log_min, log_max = log_hits.min(), log_hits.max()
        SIZE_MIN, SIZE_MAX = 4, 40

        for k in unique_labels:
            mask = labels == k
            cluster_data = hit_df[mask]
            if k == -1:
                color = '#555555'
                alpha = 0.3
                label = 'Szum'
                marker = 'x'
                size = 10
            else:
                color = cmap(k % 20)
                alpha = 0.7
                label = f'Klaster {k}'
                marker = 'o'
                # Rozmiar log-skalowany i ograniczony
                hits_log = np.log1p(cluster_data['Hits'].values)
                if log_max > log_min:
                    norm = (hits_log - log_min) / (log_max - log_min)
                else:
                    norm = np.ones_like(hits_log) * 0.5
                size = SIZE_MIN + norm * (SIZE_MAX - SIZE_MIN)

            ax.scatter(
                cluster_data['X'], cluster_data['Y'],
                c=[color], s=size, alpha=alpha,
                label=label, marker=marker, edgecolors='none'
            )

        ax.set_xlabel("X", color=TEXT_COLOR, fontsize=11)
        ax.set_ylabel("Y", color=TEXT_COLOR, fontsize=11)
        ax.set_title(
            f"DBSCAN: {result['n_clusters']} klastrów (eps={self.spin_eps.value()}, "
            f"min={self.spin_min.value()})",
            color=TEXT_COLOR, fontsize=12, fontweight='bold'
        )
        ax.set_xlim(-52, 52)
        ax.set_ylim(-52, 52)
        ax.set_aspect('equal')

        # Legenda — ograniczona do 10 elementów
        handles, lbls = ax.get_legend_handles_labels()
        if len(handles) > 10:
            handles = handles[:10]
            lbls = lbls[:10]
            lbls[-1] = f"... i {result['n_clusters'] - 9} więcej"
        legend = ax.legend(handles, lbls, loc='upper right', fontsize=8,
                           facecolor=DARK_CARD, edgecolor=DARK_ACCENT,
                           labelcolor=TEXT_COLOR)

        self.fig_cluster.tight_layout()
        self.canvas_cluster.draw()


# ─────────────────────────────────────────────────────────────────
# ZAKŁADKA 3: WYMIAR FRAKTALNY
# ─────────────────────────────────────────────────────────────────

class FractalTab(QWidget):
    def __init__(self, data_tab: DataTab):
        super().__init__()
        self.data_tab = data_tab
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header — pojedynczy plik
        header = QHBoxLayout()
        self.btn_compute = QPushButton("▶  Oblicz wymiar fraktalny")
        self.btn_compute.clicked.connect(self._compute)
        header.addWidget(self.btn_compute)

        info = QLabel(
            f"<span style='color:{MUTED_COLOR}'>Metoda box-counting 3D — "
            f"powierzchnia (X, Y, Hits) normalizowana do [0,1]³</span>"
        )
        header.addWidget(info, 1)
        layout.addLayout(header)

        # Splitter: wyniki + wykres
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Wyniki
        results_group = QGroupBox("Wyniki (pojedynczy plik)")
        rl = QVBoxLayout(results_group)

        self.lbl_dim = QLabel(
            f"<span style='font-size:28px; color:{ACCENT_COLOR}; font-weight:bold'>—</span>"
            f"<br><span style='color:{MUTED_COLOR}'>Wymiar fraktalny D</span>"
        )
        self.lbl_dim.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self.lbl_dim)

        self.lbl_r2 = result_label("R²", "—")
        self.lbl_r2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self.lbl_r2)

        rl.addSpacing(20)
        rl.addWidget(QLabel(f"<b style='color:{MUTED_COLOR}'>Tabela box-counting:</b>"))

        self.bc_table = QTableWidget()
        self.bc_table.setColumnCount(3)
        self.bc_table.setHorizontalHeaderLabels(["ε (rozmiar pudełka)", "N(ε)", "log(1/ε)"])
        self.bc_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        rl.addWidget(self.bc_table, 1)
        splitter.addWidget(results_group)

        # Wykres log-log
        plot_group = QGroupBox("Wykres log-log")
        pl = QVBoxLayout(plot_group)
        self.fig_fractal = make_figure()
        self.canvas_fractal = FigureCanvas(self.fig_fractal)
        pl.addWidget(self.canvas_fractal)
        splitter.addWidget(plot_group)

        splitter.setSizes([300, 500])
        layout.addWidget(splitter, 1)

        # ═══════════════════════════════════════════════════
        # BATCH — przetwarzanie całego folderu
        # ═══════════════════════════════════════════════════
        batch_group = QGroupBox("Batch — analiza całego folderu")
        bl = QVBoxLayout(batch_group)

        # Batch header
        batch_header = QHBoxLayout()
        self.btn_batch = QPushButton("📂  Wybierz folder i oblicz")
        self.btn_batch.clicked.connect(self._run_batch)
        batch_header.addWidget(self.btn_batch)

        self.lbl_batch_status = QLabel(
            f"<span style='color:{MUTED_COLOR}'>Wybierz folder z plikami results_*.csv</span>")
        batch_header.addWidget(self.lbl_batch_status, 1)

        self.btn_export = QPushButton("💾  Eksportuj CSV")
        self.btn_export.clicked.connect(self._export_batch)
        self.btn_export.setEnabled(False)
        batch_header.addWidget(self.btn_export)
        bl.addLayout(batch_header)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background: {DARK_BG}; border: 1px solid {DARK_ACCENT};
                border-radius: 4px; text-align: center; color: {TEXT_COLOR};
            }}
            QProgressBar::chunk {{
                background: {ACCENT_COLOR}; border-radius: 3px;
            }}
        """)
        bl.addWidget(self.progress)

        # Batch splitter: tabela + wykres D(grubość)
        batch_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tabela wyników batch
        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(5)
        self.batch_table.setHorizontalHeaderLabels([
            "Grubość", "D (wymiar)", "R²", "Σ trafień", "Plik"
        ])
        self.batch_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        batch_splitter.addWidget(self.batch_table)

        # Wykres D vs grubość
        self.fig_batch = make_figure()
        self.canvas_batch = FigureCanvas(self.fig_batch)
        batch_splitter.addWidget(self.canvas_batch)

        batch_splitter.setSizes([400, 400])
        bl.addWidget(batch_splitter, 1)

        layout.addWidget(batch_group, 1)

        # Stan batch
        self.batch_results = None

    def _compute(self):
        if self.data_tab.grid is None:
            QMessageBox.warning(self, "Brak danych",
                                'Najpierw załaduj plik CSV w zakładce "Dane".')
            return

        result = compute_fractal_dimension_3d(self.data_tab.grid)

        dim = result['dimension']
        r2 = result['r_squared']

        self.lbl_dim.setText(
            f"<span style='font-size:28px; color:{ACCENT_COLOR}; font-weight:bold'>"
            f"{dim:.4f}</span>"
            f"<br><span style='color:{MUTED_COLOR}'>Wymiar fraktalny D</span>"
        )
        self.lbl_r2.setText(
            f"<b style='color:{MUTED_COLOR}'>R²:</b> "
            f"<span style='color:{ACCENT_COLOR}; font-size:15px'>{r2:.6f}</span>"
        )

        # Tabela
        epsilons = result['epsilons']
        counts = result['counts']
        self.bc_table.setRowCount(len(epsilons))
        for i, (eps, cnt) in enumerate(zip(epsilons, counts)):
            vals = [f"{eps:.6f}", str(cnt), f"{np.log(1.0 / eps):.4f}"]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.bc_table.setItem(i, j, item)

        # Wykres
        self._draw_loglog(result)

    def _draw_loglog(self, result: dict):
        self.fig_fractal.clear()
        ax = self.fig_fractal.add_subplot(111)
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(DARK_ACCENT)

        epsilons = np.array(result['epsilons'])
        counts = np.array(result['counts'])
        coeffs = result['coeffs']

        log_inv_eps = np.log(1.0 / epsilons)
        log_counts = np.log(counts)

        # Punkty pomiarowe
        ax.scatter(log_inv_eps, log_counts, color=ACCENT_COLOR, s=50, zorder=5,
                   edgecolors='white', linewidths=0.5)

        # Prosta dopasowana
        x_fit = np.linspace(log_inv_eps.min() - 0.2, log_inv_eps.max() + 0.2, 100)
        y_fit = np.polyval(coeffs, x_fit)
        ax.plot(x_fit, y_fit, color='#00d2ff', linewidth=2, linestyle='--',
                label=f'D = {result["dimension"]:.4f}')

        ax.set_xlabel("log(1/ε)", color=TEXT_COLOR, fontsize=12)
        ax.set_ylabel("log N(ε)", color=TEXT_COLOR, fontsize=12)
        ax.set_title(
            f"Wymiar fraktalny 3D: D = {result['dimension']:.4f} (R² = {result['r_squared']:.4f})",
            color=TEXT_COLOR, fontsize=13, fontweight='bold'
        )
        legend = ax.legend(fontsize=11, facecolor=DARK_CARD, edgecolor=DARK_ACCENT,
                           labelcolor=TEXT_COLOR)

        self.fig_fractal.tight_layout()
        self.canvas_fractal.draw()

    def _run_batch(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder z wynikami", "")
        if not folder:
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_batch.setEnabled(False)
        self.btn_export.setEnabled(False)

        # Synchroniczny callback — Qt processEvents dla responsywności
        def on_progress(current, total, name):
            pct = int(current / total * 100) if total > 0 else 0
            self.progress.setValue(pct)
            self.lbl_batch_status.setText(
                f"<span style='color:{TEXT_COLOR}'>"
                f"Przetwarzanie {current}/{total}: {name}</span>"
            )
            QApplication.processEvents()

        results = run_batch_fractal(folder, progress_callback=on_progress)
        self.batch_results = results
        self.batch_folder = folder

        if not results:
            self.lbl_batch_status.setText(
                f"<span style='color:{ACCENT_COLOR}'>Nie znaleziono plików results_*.csv</span>")
            self.btn_batch.setEnabled(True)
            self.progress.setVisible(False)
            return

        # Wypełnij tabelę
        self.batch_table.setRowCount(len(results))
        for i, r in enumerate(results):
            vals = [
                r['thickness_str'],
                f"{r['dimension']:.4f}",
                f"{r['r_squared']:.4f}",
                f"{r['total_hits']:,}",
                r['file'],
            ]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.batch_table.setItem(i, j, item)

        self.lbl_batch_status.setText(
            f"<span style='color:{TEXT_COLOR}'>"
            f"Gotowe — <b>{len(results)}</b> plików przetworzonych</span>"
        )
        self.btn_batch.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.progress.setVisible(False)

        self._draw_batch_plot(results)

    def _export_batch(self):
        if not self.batch_results:
            return

        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder docelowy eksportu",
            getattr(self, 'batch_folder', ''))
        if not folder:
            return

        out_dir = os.path.join(folder, 'fractal_analysis')
        export_batch_results(self.batch_results, out_dir)

        n_files = len(self.batch_results) + 1  # summary + per-thickness
        QMessageBox.information(
            self, "Eksport zakończony",
            f"Zapisano {n_files} plików CSV do:\n{out_dir}\n\n"
            f"• fractal_dimensions.csv (podsumowanie)\n"
            f"• fractal_<grubość>.csv × {len(self.batch_results)}"
        )

    def _draw_batch_plot(self, results: list):
        self.fig_batch.clear()
        ax = self.fig_batch.add_subplot(111)
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(DARK_ACCENT)

        thicknesses = [r['thickness_num'] for r in results]
        dimensions = [r['dimension'] for r in results]

        ax.scatter(thicknesses, dimensions, color=ACCENT_COLOR, s=30, zorder=5,
                   edgecolors='white', linewidths=0.5)
        ax.plot(thicknesses, dimensions, color='#00d2ff', linewidth=1.5, alpha=0.6)

        ax.set_xlabel("Grubość tarczy [cm]", color=TEXT_COLOR, fontsize=11)
        ax.set_ylabel("Wymiar fraktalny D", color=TEXT_COLOR, fontsize=11)
        ax.set_title("D(grubość) — batch", color=TEXT_COLOR, fontsize=13,
                     fontweight='bold')

        # Zakres Y z marginesem
        d_min, d_max = min(dimensions), max(dimensions)
        margin = (d_max - d_min) * 0.1 or 0.1
        ax.set_ylim(d_min - margin, d_max + margin)

        self.fig_batch.tight_layout()
        self.canvas_batch.draw()

# ─────────────────────────────────────────────────────────────────
# OKNO GŁÓWNE
# ─────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analiza klastrowania i wymiaru fraktalnego 3D")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        tabs = QTabWidget()

        self.data_tab = DataTab()
        self.cluster_tab = ClusterTab(self.data_tab)
        self.fractal_tab = FractalTab(self.data_tab)

        tabs.addTab(self.data_tab, "📊  Dane")
        tabs.addTab(self.cluster_tab, "🔬  Klastrowanie")
        tabs.addTab(self.fractal_tab, "📐  Wymiar fraktalny")

        self.setCentralWidget(tabs)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    font = QFont("Inter", 12)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

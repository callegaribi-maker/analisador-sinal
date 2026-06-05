import io
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import find_peaks

st.set_page_config(
    page_title="Análise de Sinal — Picos e Ciclos",
    layout="wide",
    page_icon="📊",
)

st.title("📊 Análise de Sinal — Picos e Ciclos")

# ── Session state ─────────────────────────────────────────────────────────────
if "peaks" not in st.session_state:
    st.session_state.peaks = []
if "trigger_auto" not in st.session_state:
    st.session_state.trigger_auto = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configurações")

    uploaded = st.file_uploader(
        "Arquivo de sinal", type=["csv", "txt", "xlsx", "xls"]
    )

    df = None
    x_col = y_col = None

    if uploaded:
        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        if ext in ("xlsx", "xls"):
            try:
                df = pd.read_excel(uploaded)
            except Exception as e:
                st.error(f"Erro ao ler Excel: {e}")
        else:
            sep = st.selectbox(
                "Separador",
                [";", ",", "\t", " "],
                format_func=lambda s: {
                    ";": "Ponto-e-vírgula (;)",
                    ",": "Vírgula (,)",
                    "\t": "Tab",
                    " ": "Espaço",
                }[s],
                index=0,
            )
            header_row = st.number_input(
                "Linha do cabeçalho (0 = primeira)",
                min_value=0, max_value=20, value=0,
            )
            decimal = st.selectbox(
                "Decimal",
                [".", ","],
                format_func=lambda s: {
                    ".": "Ponto . (padrão EN)",
                    ",": "Vírgula , (padrão BR)",
                }[s],
                index=0,
            )
            try:
                raw = uploaded.read()
                try:
                    text = raw.decode("utf-8-sig")
                except Exception:
                    text = raw.decode("latin-1")
                df = pd.read_csv(
                    io.StringIO(text),
                    sep=sep,
                    header=int(header_row),
                    decimal=decimal,
                    engine="python",
                )
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

        if df is not None:
            cols = df.columns.tolist()
            # Default X = DURACAO, Y = ACC EIXO Y if present
            default_x = "DURACAO" if "DURACAO" in cols else cols[0]
            default_y = "ACC EIXO Y" if "ACC EIXO Y" in cols else cols[-1]
            x_col = st.selectbox(
                "Coluna X (tempo)",
                cols,
                index=cols.index(default_x) if default_x in cols else 0,
            )
            y_col = st.selectbox(
                "Coluna Y (sinal)",
                cols,
                index=cols.index(default_y) if default_y in cols else 0,
            )

    st.divider()

    st.subheader("🔍 Detecção automática")
    prominence_pct = st.slider("Proeminência mínima (%)", 1, 80, 20)
    min_dist_pct = st.slider("Distância mínima entre picos (%)", 1, 30, 5)
    if st.button("Auto-detectar picos", use_container_width=True):
        st.session_state.trigger_auto = True

    st.divider()
    snap_pct = st.slider("Snap para máximo local (%)", 0, 10, 2)

# ── Sem arquivo ───────────────────────────────────────────────────────────────
if df is None:
    st.info("👈 Carregue um arquivo na barra lateral para começar.")
    with st.expander("📖 Como usar"):
        st.markdown(
            """
            1. **Carregue** um arquivo CSV ou TXT na barra lateral
            2. Verifique as colunas X e Y selecionadas
            3. **Clique no sinal** para adicionar picos (triângulo vermelho)
            4. **Clique em um pico** para removê-lo
            5. Use **Auto-detectar** para encontrar picos automaticamente
            6. Baixe a tabela de ciclos em CSV
            """
        )
    st.stop()

# ── Preparar dados ────────────────────────────────────────────────────────────
x = pd.to_numeric(df[x_col], errors="coerce").values.astype(float)
y = pd.to_numeric(df[y_col], errors="coerce").values.astype(float)
valid = ~(np.isnan(x) | np.isnan(y))
x, y = x[valid], y[valid]
n = len(x)

if n == 0:
    st.error("Nenhum dado numérico válido. Verifique separador e decimal.")
    st.stop()

# ── Auto-detecção ─────────────────────────────────────────────────────────────
if st.session_state.trigger_auto:
    y_range = np.ptp(y) or 1.0
    prom = prominence_pct / 100 * y_range
    dist = max(1, int(n * min_dist_pct / 100))
    idx_peaks, _ = find_peaks(y, prominence=prom, distance=dist)
    st.session_state.peaks = [
        {"x": float(x[i]), "y": float(y[i])} for i in idx_peaks
    ]
    st.session_state.trigger_auto = False

sorted_peaks = sorted(st.session_state.peaks, key=lambda p: p["x"])

# ── Figura ────────────────────────────────────────────────────────────────────
fig = go.Figure()

cycle_colors = ["rgba(99,200,99,0.12)", "rgba(99,149,255,0.12)"]
for i in range(len(sorted_peaks) - 1):
    fig.add_vrect(
        x0=sorted_peaks[i]["x"], x1=sorted_peaks[i + 1]["x"],
        fillcolor=cycle_colors[i % 2],
        layer="below", line_width=0,
        annotation_text=f" C{i + 1}",
        annotation_position="top left",
        annotation=dict(font_size=10, font_color="#777"),
    )

for p in sorted_peaks:
    fig.add_vline(
        x=p["x"],
        line=dict(color="rgba(200,50,50,0.3)", width=1, dash="dot"),
    )

fig.add_trace(go.Scatter(
    x=x, y=y, mode="lines", name="Sinal",
    line=dict(color="#4C78A8", width=1.5),
    hovertemplate="x: %{x:.4g}<br>y: %{y:.4g}<extra>Sinal</extra>",
))

if sorted_peaks:
    fig.add_trace(go.Scatter(
        x=[p["x"] for p in sorted_peaks],
        y=[p["y"] for p in sorted_peaks],
        mode="markers+text",
        name="Picos",
        text=[f"P{i + 1}" for i in range(len(sorted_peaks))],
        textposition="top center",
        textfont=dict(size=10, color="darkred"),
        marker=dict(color="crimson", size=11, symbol="triangle-up",
                    line=dict(color="darkred", width=1)),
        hovertemplate="Pico x=%{x:.4g}<br>y=%{y:.4g}<extra>Pico</extra>",
    ))

fig.update_layout(
    height=500,
    title="<b>Clique no sinal</b> para adicionar pico · <b>Clique no triângulo</b> para remover",
    xaxis_title=x_col,
    yaxis_title=y_col,
    hovermode="closest",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=70, b=10),
    plot_bgcolor="white",
    paper_bgcolor="white",
)
fig.update_xaxes(showgrid=True, gridcolor="#eee", zeroline=False)
fig.update_yaxes(showgrid=True, gridcolor="#eee", zeroline=False)

# ── Seleção nativa do Streamlit ───────────────────────────────────────────────
selected = st.plotly_chart(
    fig,
    on_select="rerun",
    selection_mode="points",
    key="signal_plot",
    use_container_width=True,
)

if selected and selected.selection and selected.selection.points:
    pt = selected.selection.points[0]
    click_x = pt.get("x")
    curve = pt.get("curve_number", 0)
    x_tol = np.ptp(x) * 0.015

    if sorted_peaks and curve == 1:
        pt_idx = pt.get("point_index", 0)
        if 0 <= pt_idx < len(sorted_peaks):
            target_x = sorted_peaks[pt_idx]["x"]
            st.session_state.peaks = [
                p for p in st.session_state.peaks
                if abs(p["x"] - target_x) > x_tol * 0.1
            ]
    else:
        idx_click = int(np.argmin(np.abs(x - click_x)))
        half_w = max(1, int(n * snap_pct / 100))
        i0 = max(0, idx_click - half_w)
        i1 = min(n - 1, idx_click + half_w)
        idx_max = i0 + int(np.argmax(y[i0: i1 + 1]))
        new_x, new_y = float(x[idx_max]), float(y[idx_max])

        if not any(abs(p["x"] - new_x) < x_tol for p in st.session_state.peaks):
            st.session_state.peaks.append({"x": new_x, "y": new_y})

    st.rerun()

# ── Controles ─────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([1, 1, 4])
with c1:
    if st.button("🗑️ Limpar tudo", use_container_width=True):
        st.session_state.peaks = []
        st.rerun()
with c2:
    if st.button("↩️ Último pico", use_container_width=True) and sorted_peaks:
        last_x = sorted_peaks[-1]["x"]
        st.session_state.peaks = [
            p for p in st.session_state.peaks if p["x"] != last_x
        ]
        st.rerun()
with c3:
    st.caption(f"**{len(sorted_peaks)} pico(s) selecionado(s)**")

# ── Tabela de ciclos ──────────────────────────────────────────────────────────
if len(sorted_peaks) >= 2:
    st.subheader(f"📊 {len(sorted_peaks) - 1} ciclo(s) detectado(s)")

    rows = []
    for i in range(len(sorted_peaks) - 1):
        xs, xe = sorted_peaks[i]["x"], sorted_peaks[i + 1]["x"]
        mask = (x >= xs) & (x <= xe)
        cy = y[mask]
        rows.append({
            "Ciclo": i + 1,
            "X início": round(xs, 3),
            "X fim": round(xe, 3),
            "Duração": round(xe - xs, 3),
            "Pontos": int(mask.sum()),
            "Máx.": round(float(cy.max()), 5) if cy.size else "—",
            "Mín.": round(float(cy.min()), 5) if cy.size else "—",
            "Média": round(float(cy.mean()), 5) if cy.size else "—",
            "RMS": round(float(np.sqrt(np.mean(cy ** 2))), 5) if cy.size else "—",
        })

    cycles_df = pd.DataFrame(rows)
    st.dataframe(cycles_df, use_container_width=True, hide_index=True)

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇️ Baixar ciclos (CSV)",
            cycles_df.to_csv(index=False).encode("utf-8"),
            "ciclos.csv", "text/csv",
            use_container_width=True,
        )
    with dl2:
        peaks_df = pd.DataFrame(
            [{"Pico": i + 1, "x": p["x"], "y": p["y"]}
             for i, p in enumerate(sorted_peaks)]
        )
        st.download_button(
            "⬇️ Baixar picos (CSV)",
            peaks_df.to_csv(index=False).encode("utf-8"),
            "picos.csv", "text/csv",
            use_container_width=True,
        )

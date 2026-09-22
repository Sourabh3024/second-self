"""Streamlit application for SecondSelf."""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from secondself.ask import NO_NOTES_ANSWER, ask
from secondself.capture import CaptureStore
from secondself.classify import Classifier
from secondself.config import settings
from secondself.graph import build_and_write_graph
from secondself.link import link_all


COLOR_MAP = {
    "Projects": "#f2c879",
    "Areas": "#7dd3b0",
    "Resources": "#8fb8e8",
    "Archives": "#c09ad8",
}


@st.cache_data(show_spinner=False)
def load_graph() -> dict:
    """Load the current graph JSON, rebuilding it if needed."""
    graph_path = settings.data_dir / "graph.json"
    if not graph_path.exists():
        graph, _ = build_and_write_graph(settings.wiki_dir, graph_path)
        return graph

    try:
        return json.loads(graph_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        graph, _ = build_and_write_graph(settings.wiki_dir, graph_path)
        return graph


def render_graph_html(graph: dict) -> str:
    """Return an inline vis-network HTML snippet for the knowledge graph."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    color_block = json.dumps(COLOR_MAP)
    data_block = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)

    template = """
    <div style="color-scheme:light;position:relative;width:100%;height:700px;border:1px solid #cbd5e1;border-radius:12px;background:#f8fafc !important;background:linear-gradient(180deg, #f8fafc 0%, #eef4f7 100%);box-shadow: inset 0 0 32px rgba(71,85,105,0.08);color:#1e293b;overflow:hidden;">
      <div style="position:absolute;top:14px;left:50%;z-index:10;transform:translateX(-50%);display:flex;align-items:center;gap:10px;padding:8px 14px;border:1px solid #d7e0e5;border-radius:999px;background:rgba(255,255,255,0.94);box-shadow:0 3px 12px rgba(71,85,105,0.14);font:600 13px Georgia,serif;white-space:nowrap;">
        <span style="color:#9a6b16;">📁 Projects</span>
        <span style="color:#16745a;">◈ Areas</span>
        <span style="color:#326aa8;">▣ Resources</span>
        <span style="color:#7951a0;">▤ Archives</span>
      </div>
      <div id="network" style="width:100%;height:700px;background:#f8fafc !important;"></div>
    </div>
    <script type="text/javascript" src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
    <script type="text/javascript">
      const palette = {color_block};
      const graphData = {data_block};
      const nodeData = new vis.DataSet((graphData.nodes || []).map((node) => {{
        const group = node.group || node.para || 'Uncategorized';
        const color = palette[group] || '#b6c6c1';
        return {{
          id: node.id,
          label: node.label || node.summary || node.id,
          title: '<strong>' + escapeHtml(node.summary || node.label || node.id) + '</strong><br>' + escapeHtml(node.content_preview || 'No preview available.'),
          group,
          para: node.para || group,
          summary: node.summary || '',
          content_preview: node.content_preview || '',
          color: {{
            background: color,
            border: '#64748b',
            highlight: {{ background: '#ffffff', border: '#334155' }},
            hover: {{ background: '#ffffff', border: '#334155' }}
          }},
          font: {{ color: '#1e293b', face: 'Georgia', size: 13, strokeWidth: 1.8, strokeColor: '#f8fafc', vadjust: 2 }},
          shape: 'dot',
          size: 22,
          borderWidth: 2,
          shadow: {{ enabled: true, color: 'rgba(71,85,105,0.25)', size: 12, x: 0, y: 4 }}
        }};
      }}));

      const edgeData = new vis.DataSet((graphData.edges || []).map((edge) => {{
        return {{
          ...edge,
          arrows: {{ to: {{ enabled: false }} }},
          color: {{ color: '#94a3b8', highlight: '#9a6b16', hover: '#326aa8' }},
          smooth: {{ type: 'continuous' }},
          width: Math.max(1.2, Number(edge.weight || 1.0))
        }};
      }}));

      function escapeHtml(value) {{
        return String(value ?? '').replace(/[&<>\"']/g, (character) => {{
          const map = {{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\\"': '&quot;', "'": '&#039;' }};
          return map[character] || character;
        }});
      }}

      const container = document.getElementById('network');
      const network = new vis.Network(container, {{
        nodes: nodeData,
        edges: edgeData
      }}, {{
        autoResize: true,
        height: '700px',
        interaction: {{ hover: true, navigationButtons: true, keyboard: true }},
        physics: {{
          enabled: true,
          barnesHut: {{
            gravitationalConstant: -8000,
            centralGravity: 0.2,
            springLength: 150,
            springConstant: 0.04,
            damping: 0.09
          }},
          stabilization: {{ enabled: true, iterations: 200, updateInterval: 25 }}
        }},
        nodes: {{ chosen: true, font: {{ color: '#1e293b' }} }},
        edges: {{ selectionWidth: 2, hoverWidth: 2 }},
        interaction: {{ tooltipDelay: 100 }}
      }});

      network.on('click', (event) => {{
        const selected = event.nodes && event.nodes[0];
        if (!selected) return;
        const node = nodeData.get(selected);
        if (!node) return;
        const tooltip = '<strong>' + escapeHtml(node.summary || node.label || node.id) + '</strong><br>' + escapeHtml(node.content_preview || 'No preview available.');
        network.setSelection({{ nodes: [selected] }});
        const info = document.getElementById('graph-selection');
        if (info) {{
          info.innerHTML = tooltip;
        }}
      }});

      if (nodeData.length) {{
        network.once('stabilizationIterationsDone', () => {{
          network.setOptions({{ physics: {{ enabled: false }} }});
        }});
      }}
    </script>
    """
    return template.format(color_block=color_block, data_block=data_block)


def process_pipeline() -> list[dict]:
    """Process new raw captures, link wiki notes, and rebuild graph.json."""
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.wiki_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    classifier = Classifier(settings.raw_dir, settings.wiki_dir, settings.data_dir)
    processed = classifier.process_all()
    try:
        link_all(settings.wiki_dir, settings.data_dir)
    except Exception:
        pass

    graph, _ = build_and_write_graph(settings.wiki_dir, settings.data_dir / "graph.json")
    st.cache_data.clear()
    st.session_state["graph_snapshot"] = graph
    return processed


def render_stats(graph: dict) -> None:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    wiki_files = sorted(Path(settings.wiki_dir).glob("**/*.md"))
    st.sidebar.metric("Notes", len(wiki_files))
    st.sidebar.metric("Nodes", len(nodes))
    st.sidebar.metric("Links", len(edges))


def main() -> None:
    st.set_page_config(page_title="SecondSelf", page_icon="🧠", layout="wide")
    st.title("🧠 SecondSelf")
    st.caption("Ask your own knowledge base in plain English and explore the living map of your notes.")

    if not os.getenv("GROQ_API_KEY"):
        st.warning("GROQ_API_KEY is not configured. The app will still render the graph, but answer synthesis will fall back to note-based responses or a friendly message.")

    graph = load_graph()
    if "graph_snapshot" in st.session_state:
        graph = st.session_state["graph_snapshot"]

    with st.sidebar:
        st.header("Capture")
        note_text = st.text_area("New note", height=160, placeholder="Capture an idea, task, or insight...")
        if st.button("Save note"):
            if note_text.strip():
                store = CaptureStore(settings.raw_dir)
                store.capture_note(note_text.strip(), source="streamlit")
                st.success("Note saved to raw captures.")
            else:
                st.warning("Please enter text before saving.")

        url = st.text_input("Bookmark URL", placeholder="https://example.com")
        if st.button("Save link"):
            if url.strip():
                store = CaptureStore(settings.raw_dir)
                store.capture_link(url.strip(), source="streamlit")
                st.success("Link saved to raw captures.")
            else:
                st.warning("Please enter a valid URL.")

        st.header("Process")
        if st.button("Refresh graph"):
            with st.spinner("Rebuilding wiki graph..."):
                processed = process_pipeline()
            st.success(f"Processed {len(processed)} captures and rebuilt the graph.")

        st.header("Stats")
        render_stats(graph)

    question = st.text_input("Ask your brain", placeholder="What are my active projects and goals?")
    if st.button("Ask") and question.strip():
        with st.spinner("Searching your notes..."):
            answer = ask(question, top_k=5)
        st.subheader("Answer")
        st.write(answer.answer if answer.answer else NO_NOTES_ANSWER)
        if answer.sources:
            st.caption("Sources")
            for source in answer.sources:
                st.markdown(
                    f"- {source.id} · {source.para} · relevance {source.relevance_score:.3f}\n  {source.summary}"
                )
    elif question.strip():
        st.info("Press Ask to retrieve the most relevant notes.")

    st.subheader("Interactive Knowledge Graph")
    with st.container():
        st.components.v1.html(render_graph_html(graph), height=720, scrolling=False)

    if graph.get("metadata"):
        meta = graph["metadata"]
        st.caption(f"Graph generated at {meta.get('generated_at', 'unknown')} · {meta.get('node_count', len(graph.get('nodes', [])))} nodes · {meta.get('edge_count', len(graph.get('edges', [])))} edges")


if __name__ == "__main__":
    main()

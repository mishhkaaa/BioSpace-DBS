"""
Space Biology Knowledge Engine Dashboard
Member 3 - Streamlit UI Implementation

This dashboard provides an interface to explore:
- Papers and their AI-generated summaries
- Clusters of related research
- Natural language query capabilities
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard_integration.data_access import (
    list_papers,
    get_paper_details,
    get_cluster_summaries,
    get_cluster_papers,
    get_entities,
    get_entity_relations,
    is_graph_available
)
from dashboard_integration.query_engine import run_query
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sql.models import Paper, Cluster, Keyword

# -------------------------
# Page Configuration
# -------------------------

st.set_page_config(
    page_title="Space Biology Knowledge Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# Database Connection
# -------------------------

@st.cache_resource
def get_db_session():
    """Create a cached database session."""
    DB_PATH = Path(__file__).resolve().parents[1] / "sql" / "space_bio.db"
    engine = create_engine(f"sqlite:///{DB_PATH}")
    Session = sessionmaker(bind=engine)
    return Session()

# -------------------------
# Helper Functions
# -------------------------

def get_statistics():
    """Get overview statistics from the database."""
    session = get_db_session()
    try:
        total_papers = session.query(func.count(Paper.id)).scalar()
        total_clusters = session.query(func.count(Cluster.id)).scalar()
        total_keywords = session.query(func.count(Keyword.id)).scalar()
        
        # Get papers by year
        papers_by_year = session.query(
            Paper.year,
            func.count(Paper.id).label('count')
        ).group_by(Paper.year).order_by(Paper.year).all()
        
        # Get papers by cluster
        papers_by_cluster = session.query(
            Cluster.label,
            func.count(Paper.id).label('count')
        ).join(Cluster.papers).group_by(Cluster.label).all()
        
        return {
            'total_papers': total_papers,
            'total_clusters': total_clusters,
            'total_keywords': total_keywords,
            'papers_by_year': papers_by_year,
            'papers_by_cluster': papers_by_cluster
        }
    except Exception as e:
        st.error(f"Error fetching statistics: {e}")
        return None

def load_insights():
    """Load insights from JSON file if available."""
    insights_path = Path(__file__).resolve().parents[1] / "data" / "outputs" / "insights.json"
    try:
        if insights_path.exists():
            with open(insights_path, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        st.warning(f"Could not load insights: {e}")
        return None

# -------------------------
# Tab Renderers
# -------------------------

def render_overview_tab():
    """Render the Overview tab with statistics and charts."""
    st.header("📊 Overview")
    st.markdown("Welcome to the Space Biology Knowledge Engine dashboard!")
    
    stats = get_statistics()
    
    if stats:
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Papers", stats['total_papers'])
        
        with col2:
            st.metric("Total Clusters", stats['total_clusters'])
        
        with col3:
            st.metric("Total Keywords", stats['total_keywords'])
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Papers by Year")
            if stats['papers_by_year']:
                df_year = pd.DataFrame(stats['papers_by_year'], columns=['Year', 'Count'])
                st.bar_chart(df_year.set_index('Year'))
            else:
                st.info("No year data available")
        
        with col2:
            st.subheader("Papers by Cluster")
            if stats['papers_by_cluster']:
                df_cluster = pd.DataFrame(stats['papers_by_cluster'], columns=['Cluster', 'Count'])
                df_cluster = df_cluster.sort_values('Count', ascending=False).head(10)
                st.bar_chart(df_cluster.set_index('Cluster'))
            else:
                st.info("No cluster data available")
    else:
        st.error("Unable to load statistics. Please check the database connection.")

def render_papers_tab():
    """Render the Papers Explorer tab."""
    st.header("📄 Papers Explorer")
    
    try:
        # Fetch papers
        papers = list_papers(limit=100)
        
        if not papers:
            st.warning("No papers found in the database.")
            return
        
        # Create DataFrame for display
        df = pd.DataFrame(papers)
        
        st.subheader(f"Available Papers ({len(papers)})")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Paper selection
        st.subheader("View Paper Details")
        
        paper_options = {f"{p['paper_id']} - {p['title'][:60]}...": p['paper_id'] for p in papers}
        selected_paper = st.selectbox(
            "Select a paper to view details:",
            options=list(paper_options.keys()),
            index=0
        )
        
        if selected_paper:
            paper_id = paper_options[selected_paper]
            details = get_paper_details(paper_id)
            
            if details:
                # Display paper details
                st.markdown(f"### {details['title']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Authors:** {details['authors']}")
                    st.markdown(f"**Year:** {details['year']}")
                with col2:
                    st.markdown(f"**Journal:** {details['journal']}")
                    if details['doi']:
                        st.markdown(f"**DOI:** {details['doi']}")
                
                st.divider()
                
                # Abstract
                if details['abstract']:
                    with st.expander("📄 Abstract", expanded=True):
                        st.write(details['abstract'])
                
                # AI-Generated Summary
                if details['summary']:
                    with st.expander("🤖 AI-Generated Summary", expanded=True):
                        st.write(details['summary'])
                
                # Keywords
                if details['keywords']:
                    with st.expander("🔑 Keywords", expanded=False):
                        st.write(", ".join(details['keywords']))
                
                # Clusters
                if details['clusters']:
                    with st.expander("🔍 Clusters", expanded=False):
                        st.write(", ".join(details['clusters']))
            else:
                st.error(f"Could not find details for paper: {paper_id}")
    
    except Exception as e:
        st.error(f"Error loading papers: {e}")
        st.exception(e)

def render_clusters_tab():
    """Render the Clusters Explorer tab."""
    st.header("🔍 Clusters Explorer")
    
    try:
        # Fetch cluster summaries
        clusters = get_cluster_summaries()
        
        if not clusters:
            st.warning("No clusters found in the database.")
            return
        
        st.subheader(f"Available Clusters ({len(clusters)})")
        
        # Create DataFrame for display
        df_clusters = pd.DataFrame(clusters)
        st.dataframe(df_clusters, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Cluster selection
        st.subheader("View Cluster Papers")
        
        cluster_options = {
            f"Cluster {c['cluster_id']}: {c['summary'][:60] if c['summary'] else 'No summary'}...": c['cluster_id'] 
            for c in clusters
        }
        
        selected_cluster = st.selectbox(
            "Select a cluster to view its papers:",
            options=list(cluster_options.keys()),
            index=0
        )
        
        if selected_cluster:
            cluster_id = cluster_options[selected_cluster]
            
            # Get selected cluster details
            cluster_info = next((c for c in clusters if c['cluster_id'] == cluster_id), None)
            
            if cluster_info:
                st.markdown(f"### Cluster {cluster_id}")
                
                if cluster_info['summary']:
                    st.markdown("**Summary:**")
                    st.write(cluster_info['summary'])
                
                if cluster_info['representative_keyword']:
                    st.markdown(f"**Representative Keyword:** {cluster_info['representative_keyword']}")
                
                st.divider()
                
                # Fetch papers in this cluster
                papers = get_cluster_papers(cluster_id)
                
                if papers:
                    st.markdown(f"**Papers in this cluster ({len(papers)}):**")
                    df_papers = pd.DataFrame(papers)
                    st.dataframe(df_papers, use_container_width=True, hide_index=True)
                else:
                    st.info("No papers found in this cluster.")
    
    except Exception as e:
        st.error(f"Error loading clusters: {e}")
        st.exception(e)

def render_query_tab():
    """Render the Query Console tab."""
    st.header("💬 Query Console")
    st.markdown("Enter a natural language query to search the knowledge base.")
    
    # Query examples
    with st.expander("📖 Example Queries", expanded=False):
        st.markdown("""
        **SQL Queries:**
        - `papers in cluster 5`
        - `papers after 2020`
        - `keyword microgravity`
        
        **Graph Queries:**
        - `entities`
        - `related to spaceflight`
        
        **Hybrid Queries:**
        - `papers related to radiation and in cluster 3`
        - `papers related to bone and after 2018`
        """)
    
    # Query input
    user_query = st.text_input("Enter your query:", placeholder="e.g., papers in cluster 5")
    
    if st.button("🔍 Run Query", type="primary"):
        if user_query.strip():
            with st.spinner("Processing query..."):
                try:
                    result = run_query(user_query)
                    
                    st.success("Query executed successfully!")
                    st.divider()
                    
                    # Display results based on type
                    result_type = result.get('type', 'unknown')
                    st.markdown(f"**Query Type:** `{result_type.upper()}`")
                    
                    if result_type == "sql":
                        # SQL results
                        if 'papers' in result and result['papers']:
                            st.subheader(f"📄 Papers ({len(result['papers'])})")
                            df = pd.DataFrame(result['papers'])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        elif 'keywords' in result and result['keywords']:
                            st.subheader(f"🔑 Keywords ({len(result['keywords'])})")
                            df = pd.DataFrame(result['keywords'])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No results found.")
                    
                    elif result_type == "graph":
                        # Graph results
                        if 'entities' in result and result['entities']:
                            st.subheader(f"🌐 Entities ({len(result['entities'])})")
                            df = pd.DataFrame(result['entities'])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        elif 'papers' in result and result['papers']:
                            st.subheader(f"📄 Related Papers ({len(result['papers'])})")
                            if isinstance(result['papers'][0], dict):
                                df = pd.DataFrame(result['papers'])
                            else:
                                df = pd.DataFrame({'paper_id': result['papers']})
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No graph results found.")
                    
                    elif result_type == "hybrid":
                        # Hybrid results
                        st.subheader("🔀 Hybrid Results")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Graph Papers:**")
                            if result.get('graph_papers'):
                                if isinstance(result['graph_papers'][0], dict):
                                    df = pd.DataFrame(result['graph_papers'])
                                else:
                                    df = pd.DataFrame({'paper_id': result['graph_papers']})
                                st.dataframe(df, use_container_width=True, hide_index=True)
                            else:
                                st.info("No graph results")
                        
                        with col2:
                            st.markdown("**SQL Results:**")
                            if result.get('sql', {}).get('papers'):
                                df = pd.DataFrame(result['sql']['papers'])
                                st.dataframe(df, use_container_width=True, hide_index=True)
                            else:
                                st.info("No SQL results")
                        
                        st.divider()
                        st.markdown("**Combined Results:**")
                        if result.get('combined'):
                            df = pd.DataFrame(result['combined'])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No combined results found.")
                    
                    # Show raw result in expander
                    with st.expander("🔍 Raw Result", expanded=False):
                        st.json(result)
                
                except Exception as e:
                    st.error(f"Error executing query: {e}")
                    st.exception(e)
        else:
            st.warning("Please enter a query.")

def render_insights_tab():
    """Render the Insights tab (optional)."""
    st.header("💡 Insights")
    st.markdown("AI-generated insights from the knowledge base.")
    
    insights = load_insights()
    
    if insights:
        # Top keywords per cluster
        if 'top_keywords_per_cluster' in insights:
            st.subheader("🔑 Top Keywords per Cluster")
            
            for cluster_id, keywords in insights['top_keywords_per_cluster'].items():
                with st.expander(f"Cluster {cluster_id}", expanded=False):
                    if keywords:
                        df = pd.DataFrame(keywords)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No keywords available")
        
        # Knowledge gaps
        if 'knowledge_gaps' in insights and insights['knowledge_gaps']:
            st.subheader("🔍 Knowledge Gaps")
            for gap in insights['knowledge_gaps']:
                st.markdown(f"- {gap}")
        
        # Show raw insights
        with st.expander("📊 Raw Insights", expanded=False):
            st.json(insights)
    else:
        st.info("No insights available. The insights.json file may not exist or could not be loaded.")
        st.markdown("""
        To generate insights, ensure that:
        - The AI/NLP pipeline has been run
        - The `data/outputs/insights.json` file exists
        """)

# -------------------------
# Knowledge Graph Tab
# -------------------------

def render_knowledge_graph_tab():
    """Render the Knowledge Graph tab with Neo4j visualization."""
    st.header("🕸️ Knowledge Graph")
    st.markdown("Explore the biomedical entity knowledge graph extracted from research papers.")
    
    # Neo4j Browser Button
    st.markdown("### 🌐 External Neo4j Browser")
    st.markdown("""
    Open the full Neo4j Browser to explore the knowledge graph with advanced Cypher queries and visualizations.
    """)
    
    neo4j_browser_url = "https://browser.neo4j.io/?connectURL=neo4j+s://78b1da4c.databases.neo4j.io&username=neo4j"
    
    col1, col2 = st.columns([2, 3])
    with col1:
        if st.button("🚀 Open Neo4j Browser", type="primary", use_container_width=True):
            st.markdown(f'<meta http-equiv="refresh" content="0; url={neo4j_browser_url}">', unsafe_allow_html=True)
            st.success("Opening Neo4j Browser in new tab...")
    with col2:
        st.caption("⚠️ You will need Neo4j credentials. Contact your team lead or check the team secret manager.")
    
    st.markdown("---")
    
    # PyVis Visualization
    st.markdown("### 📊 Interactive Graph Visualization")
    
    pyvis_html_path = Path(__file__).resolve().parents[1] / "ner_pipeline" / "knowledge_graph_full.html"
    
    if pyvis_html_path.exists():
        # Read and display the HTML with timestamp to prevent caching
        with open(pyvis_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        st.components.v1.html(html_content, height=700, scrolling=True)
        
        st.caption("💡 Tip: Click any node to view details. Drag to explore, hover for info.")
    else:
        st.warning(f"Visualization file not found: {pyvis_html_path}")
        st.info("The PyVis HTML visualization should be located at `ner_pipeline/knowledge_graph_full.html`")
    
    st.markdown("---")

# -------------------------
# Main App
# -------------------------

def main():
    """Main application entry point."""
    
    # Sidebar
    st.sidebar.title("🚀 Space Biology Knowledge Engine")
    st.sidebar.markdown("---")
    
    # Tab selection
    tab_selection = st.sidebar.radio(
        "Navigation",
        ["📊 Overview", "📄 Papers Explorer", "🔍 Clusters Explorer", 
         "💬 Query Console", "💡 Insights", "🕸️ Knowledge Graph"],
        index=0
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **About this dashboard:**
    
    This dashboard provides access to a curated knowledge base of space biology research papers, 
    enhanced with AI-generated summaries, clustering, and natural language query capabilities.
     
    **Project:** BioSpace-DBS
    """)
    
    # Render selected tab
    if tab_selection == "📊 Overview":
        render_overview_tab()
    elif tab_selection == "📄 Papers Explorer":
        render_papers_tab()
    elif tab_selection == "🔍 Clusters Explorer":
        render_clusters_tab()
    elif tab_selection == "💬 Query Console":
        render_query_tab()
    elif tab_selection == "💡 Insights":
        render_insights_tab()
    elif tab_selection == "🕸️ Knowledge Graph":
        render_knowledge_graph_tab()

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Intelligence Board", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 1. INGESTÃO E TRATAMENTO DA BASE DE DADOS
# ==========================================
@st.cache_data
def load_and_clean_data():
    # Caminho do arquivo real
    file_path = r"C:\Users\Administrador\OneDrive\Documentos\Digital_Moda_Praia_50026.xlsx"
    
    # Tenta ler como CSV delimitado por ponto e vírgula 
    try:
        df = pd.read_csv(file_path, sep=';', encoding='latin1')
    except Exception:
        # Fallback caso seja um Excel nativo
        df = pd.read_excel(file_path)

    # Padronizando o nome das colunas
    df = df.rename(columns={
        'MASTER BRAND': 'brand',
        'R$': 'invest',
        'IMPRESSIONS': 'impressions',
        'TIME PERIOD': 'period',
        'MEDIA': 'media',
        'PROPERTY': 'property',
        'SITE CATEGORY': 'siteCategory',
        'AD TYPE': 'adType',
        'TRANSACTION TYPE': 'transactionType'
    })

    # Limpeza de Tipos Numéricos
    for col in ['invest', 'impressions']:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = df[col].fillna(0)

    raw_granular_data = df.copy()
    
    # Extraindo listas únicas para os filtros
    ALL_BRANDS = sorted([str(b) for b in df['brand'].dropna().unique()])
    COMPETITOR_PERIODS = df['period'].dropna().unique().tolist()
    
    # --- RECRIANDO AS BASES AGREGADAS ---
    brand_data = df.groupby('brand').agg({'invest': 'sum', 'impressions': 'sum'}).reset_index()
    brand_data['cpm'] = np.where(brand_data['impressions'] > 0, (brand_data['invest'] / brand_data['impressions']) * 1000, 0)
    brand_data['type'] = 'Mapeada'
    
    top_5_brands = brand_data.sort_values('invest', ascending=False).head(5)['brand'].tolist()
    df_top_5 = df[df['brand'].isin(top_5_brands)]
    seasonality_data = df_top_5.groupby(['period', 'brand'])['invest'].sum().reset_index()
    
    monthly_media_data = df.groupby(['period', 'media'])['invest'].sum().reset_index()
    
    ad_types_data = df.groupby('adType')['invest'].sum().reset_index()
    ad_types_data = ad_types_data.rename(columns={'adType': 'name', 'invest': 'value'})
    
    efficiency_channel_data = df.groupby('media').agg({'invest': 'sum', 'impressions': 'sum'}).reset_index()
    efficiency_channel_data['cpm'] = np.where(efficiency_channel_data['impressions'] > 0, (efficiency_channel_data['invest'] / efficiency_channel_data['impressions']) * 1000, 0)
    efficiency_channel_data = efficiency_channel_data.sort_values(by='cpm', ascending=True)
    
    top_sites_data = df.groupby(['media', 'property'])['invest'].sum().reset_index()
    top_sites_data = top_sites_data.rename(columns={'property': 'site'})
    total_by_media = top_sites_data.groupby('media')['invest'].transform('sum')
    top_sites_data['share'] = (top_sites_data['invest'] / total_by_media) * 100
    top_sites_data = top_sites_data.sort_values(['media', 'invest'], ascending=[True, False])
    
    return df, raw_granular_data, ALL_BRANDS, COMPETITOR_PERIODS, brand_data, seasonality_data, monthly_media_data, ad_types_data, efficiency_channel_data, top_sites_data

# Executa a função e carrega as variáveis na memória do Streamlit
(df, raw_granular_data, ALL_BRANDS, COMPETITOR_PERIODS, brand_data, 
 seasonality_data, monthly_media_data, ad_types_data, 
 efficiency_channel_data, top_sites_data) = load_and_clean_data()

# ==========================================
# 2. HEADER E KPIS DINÂMICOS
# ==========================================
st.title("📊 Intelligence Board: Moda Praia Feminina")
st.markdown("Master Dashboard | Investimento, Inventário e Performance Competitiva")
st.divider()

total_invest = brand_data['invest'].sum()
total_imp = brand_data['impressions'].sum()
avg_cpm = (total_invest / total_imp) * 1000 if total_imp > 0 else 0
top_brand = brand_data.loc[brand_data['invest'].idxmax()]['brand'] if not brand_data.empty else "N/A"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Investimento Mapeado Total", f"R$ {total_invest/1000000:.2f}M")
col2.metric("Impressões Auditadas", f"{total_imp/1000000:.1f} Mi")
col3.metric("CPM Médio da Categoria", f"R$ {avg_cpm:.2f}")
col4.metric("Maior Share of Voice", top_brand)
st.write("") 

# ==========================================
# 3. TABS DO DASHBOARD
# ==========================================
tab_macro, tab_marcas, tab_inventario, tab_insights, tab_comparador = st.tabs([
    "📈 Visão Executiva", 
    "🎯 Performance de Marcas", 
    "📱 Inventário & Formatos", 
    "💡 Consultoria Estratégica", 
    "⚖️ Comparador Competitivo"
])

# --- TAB 1: MACRO E SAZONALIDADE ---
with tab_macro:
    st.subheader("Sazonalidade Anual: Corrida das Marcas Principais (Top 5)")
    fig_line = px.line(seasonality_data, x='period', y='invest', color='brand', markers=True, template='plotly_white')
    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("Evolução do Mix de Mídia")
    fig_area = px.area(monthly_media_data, x='period', y='invest', color='media', template='plotly_white')
    st.plotly_chart(fig_area, use_container_width=True)

# --- TAB 2: PERFORMANCE DE MARCAS ---
with tab_marcas:
    col_A, col_B = st.columns([2, 1])
    with col_A:
        st.subheader("Matriz de Compra (Todas as Marcas)")
        fig_scatter = px.scatter(
            brand_data, x='invest', y='impressions', size='cpm', color='cpm',
            hover_name='brand', template='plotly_white', color_continuous_scale="RdYlGn_r"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col_B:
        st.subheader("🌟 Destaques")
        st.info("O mapeamento de dados brutos foi atualizado com sucesso. Navegue pelos gráficos para identificar as anomalias de CPM e volume.")

    st.subheader("Ranking Geral: Investimento vs Impressões")
    
    # Pegando o Top 15 e criando uma coluna com a escala ajustada
    sorted_brands = brand_data.sort_values(by='invest', ascending=True).tail(15)
    sorted_brands['impressions_scaled'] = sorted_brands['impressions'] / 100

    fig_bars = go.Figure()
    
    # Barra 1: Investimento
    fig_bars.add_trace(go.Bar(
        y=sorted_brands['brand'], 
        x=sorted_brands['invest'], 
        orientation='h', 
        name='Investimento (R$)', 
        marker_color='#3b82f6',
        hovertext=sorted_brands['invest'].apply(lambda x: f"R$ {x:,.2f}"),
        hoverinfo="text+name"
    ))
    
    # Barra 2: Impressões (Escala ajustada para o visual)
    fig_bars.add_trace(go.Bar(
        y=sorted_brands['brand'], 
        x=sorted_brands['impressions_scaled'], 
        orientation='h', 
        name='Impressões (Escala Ajustada)', 
        marker_color='#818cf8',
        hovertext=sorted_brands['impressions'].apply(lambda x: f"{x:,.0f} imp"),
        hoverinfo="text+name"
    ))

    # Agrupando as barras para ficarem paralelas
    fig_bars.update_layout(
        template='plotly_white', 
        height=600, 
        barmode='group',
        xaxis_title="",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_bars, use_container_width=True)

# --- TAB 3: INVENTÁRIO E FORMATOS ---
with tab_inventario:
    st.subheader("Top Sites por Canal de Mídia (Top 3 por canal)")
    canais = top_sites_data['media'].unique()
    cols = st.columns(len(canais) if len(canais) > 0 else 1)
    
    for i, canal in enumerate(canais):
        with cols[i % len(cols)]:
            st.markdown(f"**{canal}**")
            df_canal = top_sites_data[top_sites_data['media'] == canal].head(3)
            for _, row in df_canal.iterrows():
                st.caption(f"{row['site']} - R$ {row['invest']/1000:.0f}k ({row['share']:.1f}%)")
                st.progress(float(row['share']) / 100)

    st.write("---")
    col_C, col_D = st.columns(2)
    with col_C:
        st.subheader("Distribuição de Formatos (Ad Types)")
        fig_pie = px.pie(ad_types_data, values='value', names='name', hole=0.5, template='plotly_white', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_D:
        st.subheader("Benchmarking de CPM por Canal")
        fig_bar_cpm = px.bar(efficiency_channel_data, x='cpm', y='media', orientation='h', text='cpm', template='plotly_white', color_discrete_sequence=['#10b981'])
        fig_bar_cpm.update_traces(texttemplate='R$ %{text:.2f}', textposition='outside')
        fig_bar_cpm.update_layout(height=350)
        st.plotly_chart(fig_bar_cpm, use_container_width=True)

# --- TAB 4: CONSULTORIA ESTRATÉGICA ---
with tab_insights:
    st.subheader("Insights Baseados na Extração")
    st.success("A base de dados foi processada. Explore as abas de inventário e sazonalidade para montar seu plano de mídia focado em conversão e Share of Voice.")

# --- TAB 5: COMPARADOR COMPETITIVO ---
with tab_comparador:
    st.subheader("Comparador Competitivo (Granular)")
    
    if len(ALL_BRANDS) > 0:
        filt_col1, filt_col2, filt_col3, filt_col4 = st.columns([2, 3, 3, 2])
        with filt_col1:
            comp_my_brand = st.selectbox("Minha Marca", ALL_BRANDS, index=0)
        with filt_col2:
            comp_competitors = st.multiselect("Concorrentes (até 3)", [b for b in ALL_BRANDS if b != comp_my_brand], max_selections=3)
        with filt_col3:
            comp_periods = st.multiselect("Períodos", ['Todos'] + COMPETITOR_PERIODS, default=['Todos'])
        with filt_col4:
            comp_metric = st.radio("Métrica Gráfica", ['invest', 'impressions'], format_func=lambda x: "Investimento (R$)" if x == 'invest' else "Impressões")

        periods_to_filter = COMPETITOR_PERIODS if 'Todos' in comp_periods else comp_periods
        brands_to_filter = [comp_my_brand] + comp_competitors
        
        df_filtered = raw_granular_data[
            (raw_granular_data['brand'].isin(brands_to_filter)) & 
            (raw_granular_data['period'].isin(periods_to_filter))
        ]

        st.write("---")
        
        def plot_comparative_bar(dimension, title):
            df_group = df_filtered.groupby([dimension, 'brand'])[comp_metric].sum().reset_index()
            if df_group.empty:
                st.warning(f"Sem dados para {title}")
                return
            fig = px.bar(df_group, x=dimension, y=comp_metric, color='brand', barmode='group', template='plotly_white')
            fig.update_layout(title=title, xaxis_title="", yaxis_title="Métrica", height=350, legend_title="")
            st.plotly_chart(fig, use_container_width=True)

        g_col1, g_col2 = st.columns(2)
        with g_col1:
            plot_comparative_bar('media', 'Atuação por Canal de Mídia')
            plot_comparative_bar('siteCategory', 'Segmentação de Audiência')
            plot_comparative_bar('transactionType', 'Modo de Compra')
        
        with g_col2:
            plot_comparative_bar('property', 'Top Properties (Plataformas)')
            plot_comparative_bar('adType', 'Formatos')
    else:
        st.warning("Nenhuma marca encontrada na base de dados conectada.")
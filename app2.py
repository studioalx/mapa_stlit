import requests
import numpy as np
import pandas as pd
import streamlit as st
import geopandas as gpd
import plotly.express as px

# -------------------- CONFIGURAÇÕES ----------------------
titulo_pagina = 'Mapa de Desastres Climáticos no Brasil'
layout = 'wide'
st.set_page_config(page_title=titulo_pagina, layout=layout)
st.title(titulo_pagina)
st.caption('Municípios com maior risco estão em vermelho e os de menor risco em azul.')
# ---------------------------------------------------------

# ----- OPÇÕES DO DROPDOWN
estados = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']

# ----- FUNÇÕES
@st.cache_data
def carrega_dados(caminho_arquivo):
    df = pd.read_csv(caminho_arquivo)
    return df

@st.cache_data
def carrega_parquet(caminho_arquivo):
    df = pd.read_parquet(caminho_arquivo)
    return df

@st.cache_data
def carrega_malha(tipo='estados', uf='MG', intrarregiao='municipio', qualidade='minima'):
    url = f'https://servicodados.ibge.gov.br/api/v3/malhas/{tipo}/{uf}?formato=application/vnd.geo+json&intrarregiao={intrarregiao}&qualidade={qualidade}'
    return requests.get(url).json()

def filtra_estado(df, uf):
    return df[(df.uf.eq(uf))]

def filtra_grupo_desastre(df, grupo_desastre):
    return df[df.grupo_de_desastre == grupo_desastre]

def filtra_ano(df, inicio, fim):
    return df[(df.data.ge(f'{inicio}-01-01')) & (df.data.le(f'{fim}-12-30'))]

def calcula_ocorrencias(df, cols_selecionadas, cols_agrupadas):
    return df.groupby(cols_agrupadas, as_index=False)[cols_selecionadas].count().rename(columns={'protocolo': 'ocorrencias'})

def classifica_risco(df, col_ocorrencias):
    quartis = df[col_ocorrencias].quantile([0.2, 0.4, 0.6, 0.8]).values
    risco = []
    for valor in df[col_ocorrencias]:
        if valor > quartis[3]:
            risco.append('Muito Alto')
        elif valor > quartis[2]:
            risco.append('Alto')
        elif valor > quartis[1]:
            risco.append('Moderado')
        elif valor > quartis[0]:
            risco.append('Baixo')
        else:
            risco.append('Muito Baixo')
    df['risco'] = risco
    return df

# @st.cache_data
# def unir_malhas(malha1, malha2):
#     for feature in malha2['features']:
#         malha1['features'].append(feature)
#     return malha1

def cria_mapa(df, malha, locais='ibge', cor='ocorrencias', tons=None, nome_hover=None, dados_hover=None, lista_cores=None):
    fig = px.choropleth_mapbox(
        df, geojson=malha, color=cor,
        color_continuous_scale=tons,
        color_discrete_map=lista_cores,
        locations=locais, featureidkey='properties.codarea',
        center={'lat': -14, 'lon': -53}, zoom=3, 
        mapbox_style='carto-positron', height=500,
        hover_name=nome_hover, hover_data=dados_hover
    )

    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        mapbox_bounds={"west": -90, "east": -30, "south": -35, "north": 10},
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgb(250, 250, 250)',
            font=dict(size=14),
            title=dict(
                font=dict(size=16),
                text='Risco'
            )
        )
    )
    #mapbox_bounds={"west": -180, "east": -50, "south": 20, "north": 90}) 
    
    return fig

# VARIAVEIS
dados_atlas = carrega_parquet('dados_atlas_desastres.parquet')
cores_risco = {
    'Muito Alto': '#DC3912',
    'Alto': '#FF9900',
    'Moderado': '#FECB52',
    'Baixo': '#0099C6',
    'Muito Baixo': '#3366CC'
}
anos = dados_atlas.ano.unique()
codigo_estados = {
    'AC': '12', 'AL': '27', 'AM': '13', 'AP': '16', 'BA': '29', 'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52',
    'MA': '21', 'MG': '31', 'MS': '50', 'MT': '51', 'PA': '15', 'PB': '25', 'PE': '26', 'PI': '22', 'PR': '41',
    'RJ': '33', 'RN': '24', 'RO': '11', 'RR': '14', 'RS': '43', 'SC': '42', 'SE': '28', 'SP': '35', 'TO': '17'
}


# COLUNAS
# main_container = st.container()
tabs = st.tabs(['UF', "Brasil"])

with tabs[0]:
    col_mapa, col_dados = st.columns([1, 1], gap='large')

    # col_dados_container = col_dados.container()
    # col_uf, col_tipologia = col_dados_container.columns([1, 1])


    # SELECTBOX
    uf_selecionado = col_dados.selectbox('Selecione o estado', estados, index = 23)
    tipologia_selecionada = col_dados.selectbox('Selecione o grupo de desastre', dados_atlas.descricao_tipologia.unique(), index=0)
    ano_inicial, ano_final = col_mapa.select_slider('Selecione o período', anos, value=(anos[0], anos[-1]))


    # QUERY
    dados_atlas_query = dados_atlas.query("descricao_tipologia == @tipologia_selecionada & uf == @uf_selecionado & ano >= @ano_inicial & ano <= @ano_final")


    # MAPA
    malha_mun_estados = carrega_malha(uf=uf_selecionado)
    gdf = gpd.GeoDataFrame.from_features(malha_mun_estados)
    gdf_pandas = pd.DataFrame(gdf['codarea'])
    ocorrencias = dados_atlas_query.groupby(['ibge', 'municipio'], as_index=False).size().rename(columns={'size': 'ocorrencias'}).sort_values('ocorrencias', ascending=False).drop_duplicates(subset='ibge', keep='first')
    ocorrencias_merge = gdf_pandas.merge(ocorrencias, how='left', left_on='codarea', right_on='ibge')
    ocorrencias_merge.loc[np.isnan(ocorrencias_merge["ocorrencias"]), 'ocorrencias'] = 0
    classificacao_ocorrencias = classifica_risco(ocorrencias_merge, 'ocorrencias')
    fig_mapa = cria_mapa(classificacao_ocorrencias, malha_mun_estados, locais='codarea', cor='risco', lista_cores=cores_risco, dados_hover='ocorrencias', nome_hover='municipio')
    col_mapa.plotly_chart(fig_mapa, use_container_width=True)


    # LINEPLOT
    ocorrencias_ano = dados_atlas_query.groupby('ano', as_index=False).size().rename(columns={'size': 'ocorrencias'})
    titulo_line = f'Ocorrências de {tipologia_selecionada} ao longo dos anos em {uf_selecionado}'
    fig_line = px.line(ocorrencias_ano, 'ano', 'ocorrencias', markers=True, title=titulo_line, labels={'ocorrencias': f'Casos de {tipologia_selecionada}', 'ano': 'Ano'}, color_discrete_sequence=['#66AA00'])
    fig_line.update_layout(
        title_x=0.15,
        title_y=0.9
    )
    col_dados.plotly_chart(fig_line)

    # DATAFRAME E DOWNLOAD
    expander = col_dados.expander('**Tabela com os dados selecionados**')
    expander.dataframe(dados_atlas_query)
    col_dados.download_button('Baixar tabela', dados_atlas_query.to_csv(index=False), file_name=f'ocorrencias_{uf_selecionado}.csv', mime='text/csv', use_container_width=True)

with tabs[1]:
    col_mapa_br, col_dados_br = st.columns([1, 1], gap='large')


    # SELECTBOX
    tipologia_selecionada_br = col_dados_br.selectbox('Selecione o grupo de desastre', dados_atlas.descricao_tipologia.unique(), index=0, key='tipol_br')
    ano_inicial_br, ano_final_br = col_mapa_br.select_slider('Selecione o período', anos, value=(anos[0], anos[-1]), key='periodo_br')


    # QUERY
    dados_atlas_query_br = dados_atlas.query("descricao_tipologia == @tipologia_selecionada_br & ano >= @ano_inicial_br & ano <= @ano_final_br")


    # MAPA
    malha_estados_br = carrega_malha(tipo='paises', uf='BR', intrarregiao='UF')
    # gdf_br = gpd.GeoDataFrame.from_features(malha_mun_estados)
    # gdf_pandas_br = pd.DataFrame(gdf_br['codarea'])
    ocorrencias_br = dados_atlas_query_br.groupby(['uf'], as_index=False).size().rename(columns={'size': 'ocorrencias'})
    # ocorrencias_br.uf = ocorrencias_br.uf.map(codigo_estados)
    ocorrencias_br['cod_uf'] = ocorrencias_br.uf.map(codigo_estados)
    # ocorrencias_merge_br = gdf_pandas_br.merge(ocorrencias_br, how='left', left_on='codarea', right_on='uf')
    # ocorrencias_merge_br.loc[np.isnan(ocorrencias_merge_br["ocorrencias"]), 'ocorrencias'] = 0
    classificacao_ocorrencias_br = classifica_risco(ocorrencias_br, 'ocorrencias')
    fig_mapa_br = cria_mapa(classificacao_ocorrencias_br, malha_estados_br, locais='cod_uf', cor='risco', lista_cores=cores_risco, dados_hover='ocorrencias', nome_hover='uf')
    col_mapa_br.plotly_chart(fig_mapa_br, use_container_width=True)


    # LINEPLOT
    ocorrencias_ano_br = dados_atlas_query_br.groupby('ano', as_index=False).size().rename(columns={'size': 'ocorrencias'})
    titulo_line_br = f'Ocorrências de {tipologia_selecionada} ao longo dos anos no Brasil'
    fig_line_br = px.line(ocorrencias_ano_br, 'ano', 'ocorrencias', markers=True, title=titulo_line_br, labels={'ocorrencias': f'Casos de {tipologia_selecionada_br}', 'ano': 'Ano'}, color_discrete_sequence=['#66AA00'])
    fig_line_br.update_layout(
        title_x=0.15,
        title_y=0.9
    )
    col_dados_br.plotly_chart(fig_line_br)

    # DATAFRAME E DOWNLOAD
    expander_br = col_dados_br.expander('**Tabela com os dados selecionados**')
    expander_br.dataframe(dados_atlas_query_br)
    col_dados_br.download_button('Baixar tabela', dados_atlas_query_br.to_csv(index=False), file_name=f'ocorrencias_BR.csv', mime='text/csv', use_container_width=True)
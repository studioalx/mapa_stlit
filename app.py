import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# -------------------- CONFIGURAÇÕES ----------------------
titulo_pagina = 'Mapa de Desastres'
layout = 'wide'
st.set_page_config(page_title=titulo_pagina, layout=layout)
st.title(titulo_pagina)
# ---------------------------------------------------------

# ----- OPÇÕES DO DROPDOWN
estados = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']

# ----- FUNÇÕES
@st.cache_data
def carrega_dados(caminho_arquivo):
    df = pd.read_csv(caminho_arquivo)
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

@st.cache_data
def unir_malhas(malha1, malha2):
    for feature in malha2['features']:
        malha1['features'].append(feature)
    return malha1

def cria_mapa(df, malha, locais='ibge', cor='ocorrencias', tons=None, nome_hover='municipio', dados_hover=None, lista_cores=None):
    fig = px.choropleth_mapbox(
        df, geojson=malha, color=cor,
        color_continuous_scale=tons,
        color_discrete_map=lista_cores,
        locations=locais, featureidkey='properties.codarea',
        center={'lat': -14, 'lon': -53}, zoom=3, 
        mapbox_style='carto-positron', height=500,
        hover_name=nome_hover, hover_data=dados_hover,
        labels={locais: 'Código municipal', 'ocorrencias': 'Ocorrências'}
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, 
                      legend_font_size=15,
                      legend_title_text='Tipo de Desastre',
                      legend_orientation='h')
                    #   mapbox_bounds={"west": -180, "east": -50, "south": 20, "north": 90}) 
    
    return fig

# ----- VARIAVEIS
dados_atlas = carrega_dados('https://raw.githubusercontent.com/LucasclFerreira/IA-algoritmos-aprendizado-de-maquina/main/dados_climate/BD_Atlas_1991_2022_tratado.csv')
dados_atlas.data = pd.to_datetime(dados_atlas.data)
dados_atlas.ibge = dados_atlas.ibge.astype(str)
dados_atlas.uf = dados_atlas.uf.str.upper()
anos = dados_atlas.data.dt.year.unique()

disaster = carrega_dados('disaster.csv')
disaster.data = pd.to_datetime(disaster.data)

# coord = carrega_dados('https://raw.githubusercontent.com/LucasclFerreira/IA-algoritmos-aprendizado-de-maquina/main/dados_climate/coord_muni.csv')
# coord.codarea = coord.codarea.astype(str)
# disaster = pd.merge(coord, dados_atlas, how='right', left_on='codarea', right_on='ibge').rename(columns={'lat': 'long', 'long': 'lat'}).drop('ibge', axis=1)

mapa_de_cores = {
    'Estiagem e Seca': '#EECA3B',
    'Incêndio Florestal': '#E45756',
    'Onda de Frio': '#72B7B2',
    'Onda de Calor e Baixa Umidade': '#F58518',
    'Enxurradas': '#B279A2',
    'Inundações': '#0099C6',
    'Alagamentos': '#72B7B2',
    'Movimento de Massa': '#9D755D',
    'Chuvas Intensas': '#4C78A8',
    'Vendavais e Ciclones': '#54A24B',
    'Granizo': '#BAB0AC',
    'Tornado': '#4C78A8',
    'Onda de Frio': '#72B7B2',
    'Doenças infecciosas': '#54A24B',
    'Erosão': '#9D755D',
    'Outros': '#FF9DA6',
    'Rompimento/Colapso de barragens': '#BAB0AC'
}


# --- LAYOUT
col_mapa, col_dados = st.columns([1, 1], gap='large')
# aba_br, aba_uf = st.tabs(['Brasil', 'Estados'])


# selecionando DADOS
uf_selecionado = col_dados.selectbox('Selecione o estado', estados, index = 23)
grupo_desastre_selecionado = col_dados.selectbox('Selecione o grupo de desastre', dados_atlas.grupo_de_desastre.unique(), index = 0)
ano_inicial, ano_final = col_dados.select_slider('Selecione o período', anos, value=(anos[0], anos[-1]))


# aplicando FILTROS
dados_atlas_periodo = filtra_ano(dados_atlas, ano_inicial, ano_final)
dados_atlas_uf = filtra_estado(dados_atlas_periodo, uf_selecionado)
grupo_desastre = filtra_grupo_desastre(dados_atlas_uf, grupo_desastre_selecionado)

disaster_ano = filtra_ano(disaster, ano_inicial, ano_final)
disaster_tipo = filtra_grupo_desastre(disaster_ano, grupo_desastre_selecionado)


# carregando GRÁFICO
grupo_desastre['ano'] = grupo_desastre.data.dt.year
# print(grupo_desastre.columns)
# print(grupo_desastre.head())
atlas_year = grupo_desastre.groupby(['ano', 'descricao_tipologia'], as_index=False)['protocolo'].count().rename(columns={'protocolo': 'ocorrencias'})

fig_grupo_desastre = px.scatter(atlas_year, x="ano", y='descricao_tipologia', size='ocorrencias', 
    color='descricao_tipologia', size_max=40, color_discrete_map=mapa_de_cores, 
    labels={
        "descricao_tipologia": "",
        "ano": "", 
        "descricao_tipologia": ""
    }
)
fig_grupo_desastre.update_layout(showlegend=False, legend_orientation='h', margin={"r":0,"t":0,"l":0,"b":0})
fig_grupo_desastre.update_xaxes(showgrid=True)
col_dados.plotly_chart(fig_grupo_desastre)


# carregando MAPA
# ocorrencias_uf = calcula_ocorrencias(grupo_desastre, ['protocolo'], ['ibge', 'municipio']).drop_duplicates(subset='ibge', keep='first')

cols_importantes1 = ['municipio', 'uf', 'ibge', 'descricao_tipologia', 'grupo_de_desastre']
ocorrencias_uf = grupo_desastre.groupby(cols_importantes1, as_index=False).size().rename(columns={'size': 'ocorrencias'})

tipologias_mais_comuns_por_muni = grupo_desastre.groupby(['ibge', 'descricao_tipologia'], as_index=False)['protocolo'].count().sort_values('protocolo', ascending=False).drop_duplicates(subset='ibge', keep='first').drop('protocolo', axis=1)
ocorrencias_uf = ocorrencias_uf.merge(tipologias_mais_comuns_por_muni, on='ibge', suffixes=('_com', '_ocor'))
print(ocorrencias_uf.head())
col_mapa.caption('Mapa colorido por tipologia de desastre mais comum em cada município')


# ----- CLOROPLETH
malha_municipal = carrega_malha(tipo='estados', uf=uf_selecionado)
col_mapa.plotly_chart(cria_mapa(ocorrencias_uf, malha_municipal, locais='ibge', cor='descricao_tipologia_ocor', lista_cores=mapa_de_cores, nome_hover='municipio', dados_hover=['descricao_tipologia_ocor']))


# ----- SCATTER
# cols_importantes2 = ['municipio', 'cor', 'uf', 'codarea', 'lat', 'lon', 'descricao_tipologia', 'grupo_de_desastre']
# print(disaster_tipo.head())
# atlas_disaster = disaster_tipo.groupby(cols_importantes2, as_index=False).size()

# col_mapa.map(atlas_disaster, latitude='lat', longitude='lon', color='cor', zoom=3, use_container_width=True)


col_mapa.download_button('Baixar dados', grupo_desastre.to_csv(index=False), file_name='dados_atlas.csv', mime='text/csv', use_container_width=True)
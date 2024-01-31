import json
import math
import requests
import numpy as np
import pandas as pd
import streamlit as st
import geopandas as gpd
import plotly.express as px

# -------------------- CONFIGURAÇÕES ----------------------
titulo_pagina = 'Mapa de Desastres Climáticos'
layout = 'wide'
st.set_page_config(page_title=titulo_pagina, layout=layout)
st.title(titulo_pagina)
# ---------------------------------------------------------



# FUNÇÕES
@st.cache_data
def carrega_geojson(caminho):
    with open(caminho, 'r') as f:
        geoj = json.load(f)
    return geoj

@st.cache_data
def filtra_geojson(geojson, iso, prop='codarea'):
    gdf = gpd.GeoDataFrame.from_features(geojson)
    return json.loads(gdf[gdf[prop] == iso].to_json())

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

def classifica_risco2(df, col_ocorrencias):
    media = df[col_ocorrencias].mean()
    desvio = df[col_ocorrencias].std()
    risco = []
    for valor in df[col_ocorrencias]:
        if valor > media + 2 * desvio:
            risco.append('Muito Alto')
        elif valor > media + desvio:
            risco.append('Alto')
        elif valor > media - desvio and valor < media + desvio:
            risco.append('Moderado')
        elif valor > media - desvio:
            risco.append('Baixo')
        else:
            risco.append('Muito Baixo')
    df['risco'] = risco
    return df

def cria_mapa(df, malha, locais='ibge', cor='ocorrencias', tons=None, tons_midpoint=None, nome_hover=None, dados_hover=None, lista_cores=None, lat=-14, lon=-53, zoom=3, titulo_legenda='Risco', featureid='properties.codarea'):
    fig = px.choropleth_mapbox(
        df, geojson=malha, color=cor,
        color_continuous_scale=tons,
        color_continuous_midpoint=tons_midpoint,
        color_discrete_map=lista_cores,
        category_orders={cor: list(lista_cores.keys())},
        labels={'risco': 'Risco', 'ocorrencias': 'Ocorrências', 'code_muni': 'Código Municipal',
                 'code_state': 'Código País', 'desastre_mais_comum': 'Desastre mais comum'},
        locations=locais, featureidkey=featureid,
        center={'lat': lat, 'lon': lon}, zoom=zoom, 
        mapbox_style='carto-positron', height=500,
        hover_name=nome_hover, hover_data=dados_hover
    )

    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        mapbox_bounds={"west": -150, "east": -20, "south": -60, "north": 60},
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgb(250, 250, 250)',
            font=dict(size=14),
            title=dict(
                font=dict(size=16),
                text=titulo_legenda
            ),
            traceorder="normal"
        )
    )
    
    return fig



# VARIAVEIS
dados_atlas = carrega_parquet('desastres_latam.parquet')
dados_merge = carrega_parquet('area.parquet')
coord_uf = carrega_parquet('coord_uf.parquet')
pop_pib = carrega_parquet('pop_pib_muni.parquet')
pop_pib_uf = carrega_parquet('pop_pib_latam.parquet')
malha_america = carrega_geojson('malha_latam.json')

estados = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
anos = dados_atlas.ano.unique()
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
    'Granizo': 'rgb(102, 102, 102)',
    'Tornado': '#4C78A8',
    'Onda de Frio': '#72B7B2',
    'Doenças infecciosas': '#54A24B',
    'Erosão': '#9D755D',
    'Outros': '#FF9DA6',
    'Rompimento/Colapso de barragens': 'rgb(102, 102, 102)',
    'Sem Dados': '#BAB0AC'
}
cores_risco = {
    'Muito Alto': '#E45756',
    'Alto': '#F58518',
    'Moderado': '#EECA3B',
    'Baixo': '#72B7B2',
    'Muito Baixo': '#4C78A8'
}
desastres = {
    'Hidrológico': ['Alagamentos', 'Chuvas Intensas', 'Enxurradas', 'Inundações', 'Movimento de Massa'],
    'Climatológico': ['Estiagem e Seca', 'Incêndio Florestal', 'Onda de Calor e Baixa Umidade', 'Onda de Frio'],
    'Meteorológico': ['Granizo', 'Onda de Frio', 'Tornado', 'Vendavais e Ciclones'],
    'Outros': ['Doenças infecciosas', 'Erosão', 'Onda de Calor e Baixa Umidade', 'Outros', 'Rompimento/Colapso de barragens']
}

# COLUNAS
tabs = st.tabs(['UF do Brasil', "América Latina", 'Créditos'])

with tabs[0]:
    col_mapa, col_dados = st.columns([1, 1], gap='large')
    select1, select2 = col_dados.columns([1, 1])



    # SELECTBOX
    uf_selecionado = select1.selectbox('Selecione o estado', estados, index = 23)
    grupo_desastre_selecionado = select2.selectbox('Selecione o grupo de desastre', list(desastres.keys()), index=0)
    ano_inicial, ano_final = col_dados.select_slider('Selecione o período', anos, value=(anos[0], anos[-1]))



    # BUBBLE PLOT
    atlas_year = dados_atlas.query("grupo_de_desastre == @grupo_desastre_selecionado & uf == @uf_selecionado & ano >= @ano_inicial & ano <= @ano_final").groupby(['ano', 'descricao_tipologia'], as_index=False).size().rename(columns={'size': 'ocorrencias'})



    fig_grupo_desastre = px.scatter(atlas_year, x="ano", y='descricao_tipologia', size='ocorrencias', 
        color='descricao_tipologia', size_max=50, color_discrete_map=mapa_de_cores,
        labels={
            "descricao_tipologia": "",
            "ano": "", 
            "descricao_tipologia": ""
        }
    )
    fig_grupo_desastre.update_layout(showlegend=False, legend_orientation='h', margin={"r":0,"t":0,"l":0,"b":0})
    fig_grupo_desastre.update_xaxes(showgrid=True)
    col_dados.caption('Quanto maior o círculo, maior o número de ocorrências do desastre')
    col_dados.plotly_chart(fig_grupo_desastre)



    # selecionando estado
    tipologia_selecionada = col_dados.selectbox('Selecione a tipologia do desastre', desastres[grupo_desastre_selecionado], index=0)



    # MALHA
    malha_mun_estados = carrega_malha(uf=uf_selecionado)
    lat, lon = coord_uf.query("abbrev_state == @uf_selecionado")[['lat', 'lon']].values[0]



    # MAPA DE DESASTRES COMUNS
    tipologias_mais_comuns_por_muni = dados_atlas.query("grupo_de_desastre == @grupo_desastre_selecionado & uf == @uf_selecionado & ano >= @ano_inicial & ano <= @ano_final").groupby(['ibge', 'descricao_tipologia'], as_index=False).size().sort_values('size', ascending=False).drop_duplicates(subset='ibge', keep='first').rename(columns={'size': 'ocorrencias', 'descricao_tipologia': 'desastre_mais_comum'})
    merge_muni_2 = dados_merge.query("abbrev_state == @uf_selecionado").groupby(['code_muni', 'name_muni'], as_index=False).size().drop('size', axis=1)
    tipol_merge = merge_muni_2.merge(tipologias_mais_comuns_por_muni, how='left', left_on='code_muni', right_on='ibge').drop('ibge', axis=1)
    tipol_merge.loc[np.isnan(tipol_merge["ocorrencias"]), 'ocorrencias'] = 0
    tipol_merge.desastre_mais_comum = tipol_merge.desastre_mais_comum.fillna('Sem Dados')
    col_mapa.subheader('Desastre mais comum por Município')
    col_mapa.plotly_chart(cria_mapa(tipol_merge, malha_mun_estados, locais='code_muni', cor='desastre_mais_comum', lista_cores=mapa_de_cores, nome_hover='name_muni', dados_hover=['desastre_mais_comum', 'ocorrencias'], zoom=5, lat=lat, lon=lon, titulo_legenda='Desastre mais comum'), use_container_width=True)



    # QUERY
    dados_atlas_query = dados_atlas.query("descricao_tipologia == @tipologia_selecionada & uf == @uf_selecionado & ano >= @ano_inicial & ano <= @ano_final")



    # MAPA RISCO
    ocorrencias = dados_atlas_query.groupby(['ibge', 'municipio'], as_index=False).size().rename(columns={'size': 'ocorrencias'}).sort_values('ocorrencias', ascending=False).drop_duplicates(subset='ibge', keep='first')
    merge_muni = dados_merge.query("abbrev_state == @uf_selecionado").groupby(['code_muni', 'name_muni', 'AREA_KM2'], as_index=False).size().drop('size', axis=1).drop_duplicates(subset='code_muni', keep='first')
    ocorrencias_merge = merge_muni.merge(ocorrencias, how='left', left_on='code_muni', right_on='ibge')
    ocorrencias_merge.loc[np.isnan(ocorrencias_merge["ocorrencias"]), 'ocorrencias'] = 0
    classificacao_ocorrencias = classifica_risco(ocorrencias_merge, 'ocorrencias')  # mudadr classficador
    fig_mapa = cria_mapa(classificacao_ocorrencias, malha_mun_estados, locais='code_muni', cor='risco', lista_cores=cores_risco, dados_hover='ocorrencias', nome_hover='name_muni', lat=lat, lon=lon, zoom=5, titulo_legenda=f'Risco de {tipologia_selecionada}')
    # fig_mapa = cria_mapa(classificacao_ocorrencias, malha_mun_estados, locais='code_muni', cor='ocorrencias', tons=list(cores_risco.values()), dados_hover='ocorrencias', nome_hover='name_muni', lat=lat, lon=lon, zoom=5, titulo_legenda=f'Risco de {tipologia_selecionada}')
    col_mapa.divider()
    col_mapa.subheader(f'Risco de {tipologia_selecionada} em {uf_selecionado}')
    col_mapa.plotly_chart(fig_mapa, use_container_width=True)



    # MÉTRICAS
    met1, met2 = col_dados.columns([1, 1])
    met3, met4 = col_dados.columns([1, 1])

    met1.metric('Total de Ocorrências', len(dados_atlas_query))
    met2.metric('Média de Ocorrências por Ano', dados_atlas_query.groupby('ano').size().mean().astype(int))
    muni_ocorr = math.ceil(len(classificacao_ocorrencias.query("ocorrencias > 0")) / len(classificacao_ocorrencias) * 100)
    met3.metric('% dos Municípios com Ocorrências', f'{muni_ocorr}%')
    area_risco = math.ceil(classificacao_ocorrencias.loc[classificacao_ocorrencias.query("risco == 'Muito Alto' | risco == 'Alto'").index, "AREA_KM2"].sum() / classificacao_ocorrencias.AREA_KM2.sum() * 100)
    met4.metric('% de Área com Risco *Alto* e *Muito Alto*', f'{area_risco}%')


    # DATAFRAME E DOWNLOAD
    tabela = ocorrencias.copy().reset_index(drop=True).sort_values('ocorrencias', ascending=False).rename(columns={'ibge': 'codigo_municipal'})
    tabela['ocorrencias_por_ano'] = tabela.ocorrencias / (ano_final - ano_inicial + 1)
    tabela_merge = tabela.merge(pop_pib, how='left', left_on='codigo_municipal', right_on='code_muni').drop('code_muni', axis=1)
    expander = col_dados.expander(f'Municípios com o maior risco de *{tipologia_selecionada}* em {uf_selecionado}', expanded=True)
    expander.dataframe(tabela_merge.head(), hide_index=True,
                       column_config={
                            'codigo_municipal': None,
                            'municipio': st.column_config.TextColumn('Município'),
                            'ocorrencias': st.column_config.TextColumn('Total ocorrências'),
                            'pib_per_capita': st.column_config.NumberColumn(
                                'PIB per Capita',
                                format="R$ %.2f",
                            ),
                            'populacao': st.column_config.NumberColumn('Pop.', format='%d'),
                            'ocorrencias_por_ano': st.column_config.NumberColumn('Média ocorrências/ano', format='%.1f')
                        })
    col_dados.download_button('Baixar tabela', tabela_merge.to_csv(sep=';', index=False), file_name=f'ocorrencias_{uf_selecionado}.csv', mime='text/csv', use_container_width=True)



    # LINEPLOT
    ocorrencias_ano = dados_atlas_query.groupby('ano', as_index=False).size().rename(columns={'size': 'ocorrencias'})
    st.divider()
    st.subheader(f'Ocorrências de *{tipologia_selecionada}* em *{uf_selecionado}* ao longo dos anos')
    fig_line = px.line(ocorrencias_ano, 'ano', 'ocorrencias', markers=True, labels={'ocorrencias': f'Casos de {tipologia_selecionada}', 'ano': 'Ano'}, color_discrete_sequence=[mapa_de_cores[tipologia_selecionada]])
    st.plotly_chart(fig_line, use_container_width=True)    



with tabs[1]:
    col_mapa_br, col_dados_br = st.columns([1, 1], gap='large')
 


    # SELECTBOX
    grupo_desastre_selecionado_br = col_dados_br.selectbox('Selecione o grupo de desastre', list(desastres.keys()), index=0, key='gp_desastre_br')
    ano_inicial_br, ano_final_br = col_dados_br.select_slider('Selecione o período', anos, value=(anos[0], anos[-1]), key='periodo_br')



    # QUERY
    dados_atlas_query_br_1 = dados_atlas.query("grupo_de_desastre == @grupo_desastre_selecionado_br & ano >= @ano_inicial_br & ano <= @ano_final_br")
    print(dados_atlas_query_br_1.tail(20))


    # BUBBLE PLOT
    atlas_year_br = dados_atlas_query_br_1.groupby(['ano', 'descricao_tipologia'], as_index=False).size().rename(columns={'size': 'ocorrencias'})



    fig_grupo_desastre_br = px.scatter(atlas_year_br, x="ano", y='descricao_tipologia', size='ocorrencias', 
        color='descricao_tipologia', size_max=50, color_discrete_map=mapa_de_cores,
        labels={
            "descricao_tipologia": "",
            "ano": "", 
            "descricao_tipologia": ""
        }
    )
    fig_grupo_desastre_br.update_layout(showlegend=False, legend_orientation='h', margin={"r":0,"t":0,"l":0,"b":0})
    fig_grupo_desastre_br.update_xaxes(showgrid=True)
    col_dados_br.caption('Quanto maior o círculo, maior o número de ocorrências do desastre')
    col_dados_br.plotly_chart(fig_grupo_desastre_br)



    # selecionando estado
    col_pais, col_desastre = col_dados_br.columns([1, 1])

    pais_selecionado = col_pais.selectbox('Selecione o país', sorted(dados_merge.iloc[-45:].name_state.unique()), index=7, key='pais_br')
    iso = dados_merge.loc[dados_merge.name_state == pais_selecionado, 'code_state'].values[0]
    malha_pais_selecionado = filtra_geojson(malha_america, iso)

    tipologia_selecionada_br = col_desastre.selectbox('Selecione a tipologia do desastre', desastres[grupo_desastre_selecionado_br], index=2, key='tipol_br')



    # MAPA DE DESASTRES COMUNS
    tipologias_mais_comuns_por_estado = dados_atlas_query_br_1.groupby(['cod_uf', 'descricao_tipologia'], as_index=False).size().sort_values('size', ascending=False).drop_duplicates(subset='cod_uf', keep='first').rename(columns={'size': 'ocorrencias', 'descricao_tipologia': 'desastre_mais_comum'})
    tipol_br = dados_merge.groupby(['code_state', 'name_state'], as_index=False).size().drop('size', axis=1)
    tipol_merge_br = tipol_br.merge(tipologias_mais_comuns_por_estado, how='left', left_on='code_state', right_on='cod_uf').drop('cod_uf', axis=1)
    tipol_merge_br.loc[np.isnan(tipol_merge_br['ocorrencias']), 'ocorrencias'] = 0
    tipol_merge_br.desastre_mais_comum = tipol_merge_br.desastre_mais_comum.fillna('Sem Dados')
    col_mapa_br.subheader('Desastres mais comuns na América Latina')
    col_mapa_br.plotly_chart(cria_mapa(tipol_merge_br, malha_america, locais='code_state', cor='desastre_mais_comum', lista_cores=mapa_de_cores, nome_hover='name_state', dados_hover=['desastre_mais_comum', 'ocorrencias'], zoom=1, titulo_legenda='Desastre mais comum'), use_container_width=True)



    dados_atlas_query_br_2 = dados_atlas_query_br_1.query("descricao_tipologia == @tipologia_selecionada_br & cod_uf == @iso")



    # MAPA RISCO 
    col_mapa_br.divider()  
    col_mapa_br.subheader(f'Risco de {tipologia_selecionada_br} na América Latina')
    ocorrencias_br = dados_atlas_query_br_2.groupby(['cod_uf'], as_index=False).size().rename(columns={'size': 'ocorrencias'})
    merge_br = dados_merge.iloc[-45:].groupby(['code_state', 'name_state', 'AREA_KM2'], as_index=False).size().drop('size', axis=1)  # "-71" é o índice que começam os países da América Latina e os estados brasileiros
    ocorrencias_merge_br = merge_br.merge(ocorrencias_br, how='left', left_on='code_state', right_on='cod_uf')
    ocorrencias_merge_br.loc[np.isnan(ocorrencias_merge_br["ocorrencias"]), 'ocorrencias'] = 0
    # print(ocorrencias_merge_br.head(20))
    classificacao_ocorrencias_br = classifica_risco(ocorrencias_merge_br, 'ocorrencias')  # mudar classificador
    fig_mapa_br = cria_mapa(classificacao_ocorrencias_br, malha_pais_selecionado, locais='code_state', cor='risco', lista_cores=cores_risco, dados_hover='ocorrencias', nome_hover='name_state', titulo_legenda=f'Risco de {tipologia_selecionada_br}', zoom=1)
    # fig_mapa_br = cria_mapa(classificacao_ocorrencias_br, malha_america, locais='code_state', cor='ocorrencias', tons=list(cores_risco.values()), dados_hover='ocorrencias', nome_hover='name_state', titulo_legenda=f'Risco de {tipologia_selecionada_br}')
    col_mapa_br.plotly_chart(fig_mapa_br, use_container_width=True)

 

    # MÉTRICAS
    met1_br, met2_br = col_dados_br.columns([1, 1])
    # met3_br, _ = col_dados_br.columns([1, 1])

    met1_br.metric('Total de ocorrências', len(dados_atlas_query_br_2))
    met2_br.metric('Média de ocorrências por ano', round(len(dados_atlas_query_br_2) / (ano_final_br - ano_inicial_br + 1), 1))
    # area_risco_br = math.ceil(classificacao_ocorrencias_br.loc[classificacao_ocorrencias_br.query("risco == 'Muito Alto' | risco == 'Alto'").index, "AREA_KM2"].sum() / classificacao_ocorrencias_br.AREA_KM2.sum() * 100)
    # met3_br.metric('% de Área com Risco *Alto* e *Muito Alto*', f'{area_risco_br}%')



    # DATAFRAME E DOWNLOAD
    dados_tabela = dados_atlas_query_br_1.query("descricao_tipologia == @tipologia_selecionada_br").groupby(['cod_uf'], as_index=False).size().rename(columns={'size': 'ocorrencias'})
    tabela_br = dados_tabela.copy().reset_index(drop=True).sort_values('ocorrencias', ascending=False)
    tabela_br['ocorrencias_por_ano'] = round(tabela_br.ocorrencias.div(ano_final_br - ano_inicial_br + 1), 1)
    # print(tabela_br.head())
    tabela_merge_br = pop_pib_uf.merge(tabela_br, how='right', left_on='cod_uf', right_on='cod_uf').drop(['cod_uf'], axis=1)
    # print(tabela_merge_br.head())
    expander_br = col_dados_br.expander(f'Países com o maior risco de *{tipologia_selecionada_br}* na América Latina', expanded=True)
    expander_br.dataframe(tabela_merge_br.head(), hide_index=True, 
                          column_config={
                            'pais': st.column_config.TextColumn('País'),
                            'ocorrencias': st.column_config.TextColumn('Total ocorrências'),
                            'pib_per_capita': st.column_config.NumberColumn(
                                'PIB per Capita',
                                format="R$ %.2f",
                            ),
                            'populacao': st.column_config.NumberColumn('Pop.', format='%d'),
                            'ocorrencias_por_ano': st.column_config.NumberColumn('Média ocorrências/ano', format='%.1f')
                        })

    col_dados_br.download_button('Baixar tabela', tabela_merge_br.to_csv(sep=';', index=False), file_name=f'{tipologia_selecionada_br.replace(" ", "_").lower()}_americalatina.csv', mime='text/csv', use_container_width=True)



    # LINEPLOT
    ocorrencias_ano_br = dados_atlas_query_br_2.groupby('ano', as_index=False).size().rename(columns={'size': 'ocorrencias'})
    st.divider()
    st.subheader(f'Ocorrências de *{tipologia_selecionada_br}* na América Latina ao longo dos anos')
    fig_line_br = px.line(ocorrencias_ano_br, 'ano', 'ocorrencias', markers=True, labels={'ocorrencias': f'Casos de {tipologia_selecionada_br}', 'ano': 'Ano'}, color_discrete_sequence=[mapa_de_cores[tipologia_selecionada_br]])
    st.plotly_chart(fig_line_br, use_container_width=True)



# creditos
with tabs[2]:
    col_creditos1, col_creditos2 = st.columns([1, 1], gap='large')

    col_creditos1.subheader('Founded by [IRB(Re)](https://www.irbre.com/)')
    col_creditos1.caption('A leading figure in the Brazilian reinsurance market, with over 80 years of experience and a complete portfolio of solutions for the market.')
    col_creditos1.image('irb.jpg', use_column_width=True)

    col_creditos2.subheader('Developed by Instituto de Riscos Climáticos')
    col_creditos2.markdown('''
    **Supervisors:** Carlos Teixeira, Reinaldo Marques & Roberto Westenberger

    **Researchers:** Luiz Otavio & Karoline Branco

    **Data Scientists:**  Lucas Lima & Paulo Cesar
                        
    **Risk Scientists:** Ana Victoria & Beatriz Pimenta
                        
    #### Source
    - **The Emergency Events Database (EM-DAT)** , Centre for Research on the Epidemiology of Disasters (CRED) / Université catholique de Louvain (UCLouvain), Brussels, Belgium – [www.emdat.be](https://www.emdadt.be/).
    - **Atlas Digital de Desastres no Brasil** - [www.atlasdigital.mdr.gov.br/](http://atlasdigital.mdr.gov.br/).
    ''')
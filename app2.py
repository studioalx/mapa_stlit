import json
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# -------------------- CONFIGURAÇÕES ----------------------
titulo_pagina = 'Mapa de Desastres Climáticos no Brasil'
layout = 'wide'
st.set_page_config(page_title=titulo_pagina, layout=layout)
st.title(titulo_pagina)
# ---------------------------------------------------------



# ----- FUNÇÕES
@st.cache_data
def carrega_geojson(caminho):
    with open(caminho, 'r') as f:
        geoj = json.load(f)
    return geoj

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


def cria_mapa(df, malha, locais='ibge', cor='ocorrencias', tons=None, nome_hover=None, dados_hover=None, lista_cores=None, lat=-14, lon=-53, zoom=3, titulo_legenda='Risco', featureid='properties.codarea'):
    fig = px.choropleth_mapbox(
        df, geojson=malha, color=cor,
        color_continuous_scale=tons,
        color_discrete_map=lista_cores,
        locations=locais, featureidkey=featureid,
        center={'lat': lat, 'lon': lon}, zoom=zoom, 
        mapbox_style='carto-positron', height=500,
        hover_name=nome_hover, hover_data=dados_hover
    )

    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        mapbox_bounds={"west": -100, "east": -20, "south": -60, "north": 20},
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
            )
        )
    )
    #mapbox_bounds={"west": -180, "east": -50, "south": 20, "north": 90}) 
    
    return fig



# VARIAVEIS
dados_atlas = carrega_parquet('dados_desastres_ams.parquet')
dados_merge = carrega_parquet('ams+muni_br.parquet')
coord_uf = carrega_parquet('coord_uf.parquet')
pop_pib = carrega_parquet('pop_pib_muni.parquet')
pop_pib_uf = carrega_parquet('pop_pib_uf.parquet')
malha_america = carrega_geojson('ams+br_uf.json')

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
    'Muito Alto': '#DC3912',
    'Alto': '#FF9900',
    'Moderado': '#FECB52',
    'Baixo': '#0099C6',
    'Muito Baixo': '#3366CC'
}
codigo_estados = {
    'AC': '12', 'AL': '27', 'AM': '13', 'AP': '16', 'BA': '29', 'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52',
    'MA': '21', 'MG': '31', 'MS': '50', 'MT': '51', 'PA': '15', 'PB': '25', 'PE': '26', 'PI': '22', 'PR': '41',
    'RJ': '33', 'RN': '24', 'RO': '11', 'RR': '14', 'RS': '43', 'SC': '42', 'SE': '28', 'SP': '35', 'TO': '17'
}
desastres = {
    'Hidrológico': ['Alagamentos', 'Chuvas Intensas', 'Enxurradas', 'Inundações', 'Movimento de Massa'],
    'Climatológico': ['Estiagem e Seca', 'Incêndio Florestal', 'Onda de Calor e Baixa Umidade', 'Onda de Frio'],
    'Meteorológico': ['Granizo', 'Onda de Frio', 'Tornado', 'Vendavais e Ciclones'],
    'Outros': ['Doenças infecciosas', 'Erosão', 'Onda de Calor e Baixa Umidade', 'Outros', 'Rompimento/Colapso de barragens']
}

# COLUNAS
tabs = st.tabs(['UF', "Brasil"])

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
    col_mapa.subheader('Desastre mais comum por município	')
    col_mapa.plotly_chart(cria_mapa(tipol_merge, malha_mun_estados, locais='code_muni', cor='desastre_mais_comum', lista_cores=mapa_de_cores, nome_hover='name_muni', dados_hover=['desastre_mais_comum', 'ocorrencias'], zoom=5, lat=lat, lon=lon, titulo_legenda='Desastre mais comum'), use_container_width=True)



    # QUERY
    dados_atlas_query = dados_atlas.query("descricao_tipologia == @tipologia_selecionada & uf == @uf_selecionado & ano >= @ano_inicial & ano <= @ano_final")



    # MAPA RISCO
    ocorrencias = dados_atlas_query.groupby(['ibge', 'municipio'], as_index=False).size().rename(columns={'size': 'ocorrencias'}).sort_values('ocorrencias', ascending=False).drop_duplicates(subset='ibge', keep='first')
    merge_muni = dados_merge.query("abbrev_state == @uf_selecionado").groupby(['code_muni', 'name_muni'], as_index=False).size().drop('size', axis=1)
    ocorrencias_merge = merge_muni.merge(ocorrencias, how='left', left_on='code_muni', right_on='ibge')
    ocorrencias_merge.loc[np.isnan(ocorrencias_merge["ocorrencias"]), 'ocorrencias'] = 0
    classificacao_ocorrencias = classifica_risco(ocorrencias_merge, 'ocorrencias')
    fig_mapa = cria_mapa(classificacao_ocorrencias, malha_mun_estados, locais='code_muni', cor='risco', lista_cores=cores_risco, dados_hover='ocorrencias', nome_hover='name_muni', lat=lat, lon=lon, zoom=5, titulo_legenda=f'Risco de {tipologia_selecionada}')
    col_mapa.divider()
    col_mapa.subheader(f'Risco de {tipologia_selecionada} em {uf_selecionado}')
    col_mapa.plotly_chart(fig_mapa, use_container_width=True)



    # MÉTRICAS
    met1, met2, met3 = col_dados.columns([1, 1, 1])
    met1.metric('Total de ocorrências', len(dados_atlas_query))
    met2.metric('Média de ocorrências por ano', dados_atlas_query.groupby('ano').size().mean().astype(int))
    met3.metric('% de municípios afetados', f'{round(1 - (len(ocorrencias_merge.query("ocorrencias == 0")) / len(ocorrencias_merge)), 2) * 100} %')



    # DATAFRAME E DOWNLOAD
    tabela = ocorrencias.copy().reset_index(drop=True).sort_values('ocorrencias', ascending=False)
    tabela['ocorrencias_por_ano'] = tabela.ocorrencias / (ano_final - ano_inicial + 1)
    tabela_merge = tabela.merge(pop_pib, how='left', left_on='ibge', right_on='code_muni').drop('code_muni', axis=1)
    expander = col_dados.expander(f'Tabela dos 5 municípios com o maior risco de *{tipologia_selecionada}* em {uf_selecionado}', expanded=True)
    expander.dataframe(tabela_merge.head())
    col_dados.download_button('Baixar tabela', tabela_merge.to_csv(sep=';', index=False), file_name=f'ocorrencias_{uf_selecionado}.csv', mime='text/csv', use_container_width=True)



    # LINEPLOT
    ocorrencias_ano = dados_atlas_query.groupby('ano', as_index=False).size().rename(columns={'size': 'ocorrencias'})
    st.divider()
    st.subheader(f'Ocorrências de *{tipologia_selecionada}* em *{uf_selecionado}* ao longo dos anos')
    fig_line = px.line(ocorrencias_ano, 'ano', 'ocorrencias', markers=True, labels={'ocorrencias': f'Casos de {tipologia_selecionada}', 'ano': 'Ano'}, color_discrete_sequence=[mapa_de_cores[tipologia_selecionada]])
    # fig_line.update_layout(
    #     title_x=0.15,
    #     title_y=0.9
    # )
    st.plotly_chart(fig_line, use_container_width=True)    



with tabs[1]:
    col_mapa_br, col_dados_br = st.columns([1, 1], gap='large')
    # select1_br, select2_br = col_dados_br.columns([1, 1])

    # SELECTBOX
    grupo_desastre_selecionado_br = col_dados_br.selectbox('Selecione o grupo de desastre', list(desastres.keys()), index=0, key='gp_desastre_br')
    ano_inicial_br, ano_final_br = col_dados_br.select_slider('Selecione o período', anos, value=(anos[0], anos[-1]), key='periodo_br')

    # QUERY
    dados_atlas_query_br_1 = dados_atlas.query("grupo_de_desastre == @grupo_desastre_selecionado_br & ano >= @ano_inicial_br & ano <= @ano_final_br")

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
    tipologia_selecionada_br = col_dados_br.selectbox('Selecione a tipologia do desastre', desastres[grupo_desastre_selecionado_br], index=0, key='tipol_br')


    # MALHA
    malha_estados_br = carrega_malha(tipo='paises', uf='BR', intrarregiao='UF')


    # MAPA DE DESASTRES COMUNS
    tipologias_mais_comuns_por_estado = dados_atlas_query_br_1.groupby(['cod_uf', 'descricao_tipologia'], as_index=False).size().sort_values('size', ascending=False).drop_duplicates(subset='cod_uf', keep='first').rename(columns={'size': 'ocorrencias', 'descricao_tipologia': 'desastre_mais_comum'})
    # tipologias_mais_comuns_por_estado['cod_uf'] = tipologias_mais_comuns_por_estado.uf.map(codigo_estados)
    tipol_br = dados_merge.groupby(['code_state', 'name_state'], as_index=False).size().drop('size', axis=1)
    print(tipol_br.name_state.unique())
    tipol_merge_br = tipol_br.merge(tipologias_mais_comuns_por_estado, how='left', left_on='code_state', right_on='cod_uf').drop('cod_uf', axis=1)
    tipol_merge_br.loc[np.isnan(tipol_merge_br['ocorrencias']), 'ocorrencias'] = 0
    tipol_merge_br.desastre_mais_comum = tipol_merge_br.desastre_mais_comum.fillna('Sem Dados')
    col_mapa_br.subheader('Desastre mais comum por estado')
    col_mapa_br.plotly_chart(cria_mapa(tipol_merge_br, malha_america, locais='code_state', cor='desastre_mais_comum', lista_cores=mapa_de_cores, nome_hover='name_state', dados_hover=['desastre_mais_comum', 'ocorrencias'], zoom=3, titulo_legenda='Desastre mais comum'), use_container_width=True)


    dados_atlas_query_br_2 = dados_atlas_query_br_1.query("descricao_tipologia == @tipologia_selecionada_br")


    # MAPA RISCO 
    col_mapa_br.divider()  
    col_mapa_br.subheader(f'Risco de {tipologia_selecionada_br} no Brasil')
    # malha_estados_br = carrega_malha(tipo='paises', uf='BR', intrarregiao='UF')
    # modifiquei uf para cod_uf
    ocorrencias_br = dados_atlas_query_br_2.groupby(['cod_uf'], as_index=False).size().rename(columns={'size': 'ocorrencias'})
    # ocorrencias_br['cod_uf'] = ocorrencias_br.uf.map(codigo_estados)
    merge_br = dados_merge.groupby(['code_state', 'name_state'], as_index=False).size().drop('size', axis=1)
    ocorrencias_merge_br = merge_br.merge(ocorrencias_br, how='left', left_on='code_state', right_on='cod_uf')
    ocorrencias_merge_br.loc[np.isnan(ocorrencias_merge_br["ocorrencias"]), 'ocorrencias'] = 0
    classificacao_ocorrencias_br = classifica_risco(ocorrencias_merge_br, 'ocorrencias')
    fig_mapa_br = cria_mapa(classificacao_ocorrencias_br, malha_america, locais='code_state', cor='risco', lista_cores=cores_risco, dados_hover='ocorrencias', nome_hover='name_state', titulo_legenda=f'Risco de {tipologia_selecionada_br}')
    col_mapa_br.plotly_chart(fig_mapa_br, use_container_width=True)


    # MÉTRICAS
    met1_br, met2_br = col_dados_br.columns([1, 1])
    met1_br.metric('Total de ocorrências', len(dados_atlas_query_br_2))
    met2_br.metric('Média de ocorrências por ano', dados_atlas_query_br_2.groupby('ano').size().mean().astype(int))



    # DATAFRAME E DOWNLOAD
    tabela_br = ocorrencias_br.copy().reset_index(drop=True).sort_values('ocorrencias', ascending=False)
    tabela_br['ocorrencias_por_ano'] = tabela_br.ocorrencias / (ano_final_br - ano_inicial_br + 1)
    tabela_merge_br = tabela_br.merge(pop_pib_uf, how='left', left_on='cod_uf', right_on='code_state').drop(['code_state', 'cod_uf'], axis=1)
    expander_br = col_dados_br.expander(f'Tabela dos 5 estados com o maior risco de *{tipologia_selecionada_br}* no Brasil', expanded=True)
    expander_br.dataframe(tabela_merge_br.head())
    col_dados_br.download_button('Baixar tabela', tabela_merge_br.to_csv(sep=';', index=False), file_name=f'ocorrencias_{tipologia_selecionada_br.replace(" ", "_")}_BR.csv', mime='text/csv', use_container_width=True)



    # LINEPLOT
    ocorrencias_ano_br = dados_atlas_query_br_2.groupby('ano', as_index=False).size().rename(columns={'size': 'ocorrencias'})
    st.divider()
    st.subheader(f'Ocorrências de *{tipologia_selecionada_br}* no Brasil ao longo dos anos')
    fig_line_br = px.line(ocorrencias_ano_br, 'ano', 'ocorrencias', markers=True, labels={'ocorrencias': f'Casos de {tipologia_selecionada_br}', 'ano': 'Ano'}, color_discrete_sequence=[mapa_de_cores[tipologia_selecionada_br]])
    # fig_line.update_layout(
    #     title_x=0.15,
    #     title_y=0.9
    # )
    st.plotly_chart(fig_line_br, use_container_width=True)    


# with tabs[1]:
#     col_mapa_br, col_dados_br = st.columns([1, 1], gap='large')


#     # SELECTBOX
#     grupo_desastre_selecionado_br = col_dados_br.selectbox('Selecione o grupo de desastre', list(desastres.keys()), index=0, key='gp_desastre_br')
#     tipologia_selecionada_br = col_dados_br.selectbox('Selecione o grupo de desastre', desastres[grupo_desastre_selecionado_br], index=0, key='tipol_br')
#     ano_inicial_br, ano_final_br = col_mapa_br.select_slider('Selecione o período', anos, value=(anos[0], anos[-1]), key='periodo_br', use_container_width=True)


#     # QUERY
#     dados_atlas_query_br = dados_atlas.query("descricao_tipologia == @tipologia_selecionada_br & ano >= @ano_inicial_br & ano <= @ano_final_br")


    # # MAPA
    # malha_estados_br = carrega_malha(tipo='paises', uf='BR', intrarregiao='UF')
    # ocorrencias_br = dados_atlas_query_br.groupby(['uf'], as_index=False).size().rename(columns={'size': 'ocorrencias'})
    # ocorrencias_br['cod_uf'] = ocorrencias_br.uf.map(codigo_estados)
    # merge_br = dados_merge.groupby(['code_state', 'name_state'], as_index=False).size().drop('size', axis=1)
    # ocorrencias_merge_br = merge_br.merge(ocorrencias_br, how='left', left_on='code_state', right_on='cod_uf')
    # ocorrencias_merge_br.loc[np.isnan(ocorrencias_merge_br["ocorrencias"]), 'ocorrencias'] = 0
    # classificacao_ocorrencias_br = classifica_risco(ocorrencias_merge_br, 'ocorrencias')
    # # print(classificacao_ocorrencias_br.head())
    # fig_mapa_br = cria_mapa(classificacao_ocorrencias_br, malha_estados_br, locais='code_state', cor='risco', lista_cores=cores_risco, dados_hover='ocorrencias', nome_hover='name_state')
    # col_mapa_br.plotly_chart(fig_mapa_br, use_container_width=True)


#     # ABAS DOS GRAFICOS
#     grafico_linha, grafico_barra = col_dados_br.tabs(['Ocorrências ao longo dos anos', 'Outros desastres'])


#     # LINEPLOT
#     ocorrencias_ano_br = dados_atlas_query_br.groupby('ano', as_index=False).size().rename(columns={'size': 'ocorrencias'})
#     titulo_line_br = f'Ocorrências de {tipologia_selecionada} ao longo dos anos no Brasil'
#     fig_line_br = px.line(ocorrencias_ano_br, 'ano', 'ocorrencias', markers=True, title=titulo_line_br, labels={'ocorrencias': f'Casos de {tipologia_selecionada_br}', 'ano': 'Ano'}, color_discrete_sequence=['#6E899C'])
#     fig_line_br.update_layout(
#         title_x=0.15,
#         title_y=0.9
#     )
#     with grafico_linha:
#         st.plotly_chart(fig_line_br)
    
#     with grafico_barra:
#         atlas_year_br = dados_atlas.query("grupo_de_desastre == @grupo_desastre_selecionado_br & ano >= @ano_inicial_br & ano <= @ano_final_br").groupby(['ano', 'descricao_tipologia'], as_index=False).size().rename(columns={'size': 'ocorrencias'})

#         fig_grupo_desastre_br = px.scatter(atlas_year_br, x="ano", y='descricao_tipologia', size='ocorrencias', 
#             color='descricao_tipologia', size_max=50, color_discrete_sequence=['#6E899C'],
#             labels={
#                 "descricao_tipologia": "",
#                 "ano": "", 
#                 "descricao_tipologia": ""
#             }
#         )
#         fig_grupo_desastre_br.update_layout(showlegend=False, legend_orientation='h', margin={"r":0,"t":0,"l":0,"b":0})
#         fig_grupo_desastre_br.update_xaxes(showgrid=True)
#         st.plotly_chart(fig_grupo_desastre_br)

#     # DATAFRAME E DOWNLOAD
#     muni_ocorrencias = dados_atlas_query_br.groupby(['ibge', 'municipio'], as_index=False).size().rename(columns={'size': 'ocorrencias'}).sort_values('ocorrencias', ascending=False).drop_duplicates(subset='ibge', keep='first')
#     merge_tabela = dados_merge.groupby(['code_muni', 'abbrev_state'], as_index=False).size().drop('size', axis=1).merge(muni_ocorrencias, how='right', left_on='code_muni', right_on='ibge').drop('code_muni', axis=1)
#     tabela_br = merge_tabela.head().copy().reset_index(drop=True)
#     tabela_br['populacao'] = np.nan
#     tabela_br['pib_per_capita'] = np.nan
#     expander_br = col_dados_br.expander(f'Tabela dos 5 municípios com o maior risco de *{tipologia_selecionada_br}* no Brasil')
#     expander_br.dataframe(tabela_br)
#     col_dados_br.download_button('Baixar tabela', tabela_br.to_csv(index=False), file_name=f'ocorrencias_BR.csv', mime='text/csv', use_container_width=True)
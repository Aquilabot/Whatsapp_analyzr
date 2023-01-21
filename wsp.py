import datetime
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
from wordcloud import STOPWORDS, WordCloud
from collections import Counter
import calendar
import re
import unidecode
import dateutil.parser as parser
import logging

# loggers
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_chat(file_path):
    logger.info("Procesando archivo de chat")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        logger.info("Leyendo archivo")
        lines = [unidecode.unidecode(line) for line in lines]
        logger.info("Sanitizando archivo")
    messages = []
    current_line = ""
    for line in lines:
        if re.search(r'\d{1,2}/\d{1,2}/\d{2}[,]? \d{1,2}:\d{2}[\s]?[ap]\.', line):
            messages.append(current_line)
            logger.info(current_line)
            current_line = line
        else:
            current_line += line
    messages.append(current_line)
    logger.info(current_line)
    logger.info("Procesando mensajes")
    df = pd.DataFrame(columns=['date', 'sender', 'content'])
    for message in messages:
        logger.info("Procesando mensaje: %s", message)
        if not re.search(r'\w', message):
            logger.info("Mensaje vacío")
            continue
        date_time_str, rest = message.split(' - ', 1)
        try:
            sender, content = rest.split(': ', 1)
        except ValueError:
            sender = rest
            content = ''

        if "p" in date_time_str.lower():
            # extraer minutos, hora, día, mes y año
            minute = int(
                re.search(r'(\d{1,2}):(\d{2})', date_time_str).group(2))
            hour = int(re.search(r'(\d{1,2}):(\d{2})', date_time_str).group(1))
            day = int(re.search(r'(\d{1,2})/(\d{1,2})/(\d{2})',
                                date_time_str).group(1))
            month = int(re.search(
                r'(\d{1,2})/(\d{1,2})/(\d{2})', date_time_str).group(2))
            year = int(re.search(
                r'(\d{1,2})/(\d{1,2})/(\d{2})', date_time_str).group(3))
            if hour != 12:
                # agregar 12 a la hora
                hour = hour + 12
            # agregar 2000 al año
            year = year + 2000
            # creamos el objeto datetime
            date_time_obj = datetime.datetime(year,
                                              month, day, hour, minute)
        else:
            date_time_obj = parser.parse(date_time_str)
        new_row = pd.DataFrame(
            {'date': date_time_obj, 'sender': sender, 'content': content}, index=[0])
        df = pd.concat([df, new_row], ignore_index=True)

    df['date'] = pd.to_datetime(df['date'])
    df['content_length'] = df['content'].str.len()
    return df


def plot_sender_chart(df):
    logger.info("Creando gráfica de sender")
    df_sender = df.groupby(['sender']).sum(numeric_only=True)
    fig = go.Figure(data=[go.Pie(labels=df_sender.index,
                    values=df_sender['content_length'])])
    fig.update_layout(title='Cantidad de texto por persona')
    logger.info("Mostrando gráfica")
    fig.show()


def plot_month_chart(df):
    logger.info("Creando gráfica de mes")
    df['month_name'] = df['date'].dt.month.apply(
        lambda x: calendar.month_name[x])
    df_month = df.groupby(['month_name']).sum(numeric_only=True)
    x = df_month.index
    y = df_month['content_length']
    x, y = zip(
        *sorted(zip(x, y), key=lambda x: list(calendar.month_name).index(x[0])))
    fig = go.Figure(data=[go.Bar(x=x, y=y)])
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=x,
            ticktext=x
        ),
    )
    logger.info("Mostrando gráfica")
    fig.show()


def plot_hour_chart(df):
    logger.info("Creando gráfica de hora")
    hour_counts = [0]*24
    for i in range(24):
        hour_counts[i] = df[df['date'].dt.hour == i]['content_length'].sum()
    data = [go.Bar(x=list(range(24)), y=hour_counts)]
    layout = go.Layout(title='Cantidad de texto por hora del día', xaxis=dict(
        title='Hora del día'), yaxis=dict(title='Cantidad de texto'))
    fig = go.Figure(data=data, layout=layout)
    logger.info("Mostrando gráfica")
    fig.show()


def plot_month_hour_chart(df):
    logger.info("Creando gráfica de mes y hora")
    df['month_name'] = df['date'].dt.month.apply(
        lambda x: calendar.month_name[x])
    df_month = df.groupby(['month_name']).sum(numeric_only=True)
    x_month = df_month.index
    y_month = df_month['content_length']
    x_month, y_month = zip(
        *sorted(zip(x_month, y_month), key=lambda x: list(calendar.month_name).index(x[0])))

    hour_counts = [0]*24
    for i in range(24):
        hour_counts[i] = df[df['date'].dt.hour == i]['content_length'].sum()
    x_hour = list(range(24))

    fig = sp.make_subplots(rows=1, cols=2, subplot_titles=(
        "Cantidad de texto por mes", "Cantidad de texto por hora del día"))
    fig.append_trace(go.Bar(x=x_month, y=y_month), 1, 1)
    fig.append_trace(go.Bar(x=x_hour, y=hour_counts), 1, 2)
    fig.update_layout(xaxis=dict(title='Meses'),
                      yaxis=dict(title='Cantidad de texto'))

    logger.info("Mostrando gráfica")
    fig.show()


def plot_word_cloud_heatmap(df):
    logger.info("Creando nube de palabras y heatmap")
    # Crear la nube de palabras
    text = df["content"].str.cat(sep=" ")
    stopwords = set(STOPWORDS)
    # añadir palabras desde el archivo de stopwords.json
    with open('stopwords.json') as f:
        data = json.load(f)
        for word in data['stopwords']:
            stopwords.add(word)

    wordcloud = WordCloud(width=800, height=800,
                          background_color='white',
                          stopwords=stopwords,
                          min_font_size=10).generate(text)
    # Guardar la nube de palabras como imagen para usarlo luego en el plot
    wordcloud.to_file("wordcloud.png")
    word_freq = dict(Counter(wordcloud.words_))
    wordcloud_plot = go.Figure(go.Scatter(
        x=list(word_freq.keys()), y=list(word_freq.values())))

    # Crear el heatmap de palabras
    df_copy = df.copy()
    df_copy['hour'] = df_copy['date'].dt.hour
    df_grouped = df_copy.groupby(['sender', 'hour']).count()
    df_pivot = df_grouped.pivot_table(
        values='content', index='sender', columns='hour')

    heatmap = go.Figure(data=go.Heatmap(z=df_pivot.values,
                                        x=df_pivot.index,
                                        y=df_pivot.columns,
                                        colorscale='Viridis'))
    heatmap.update_layout(title='Cantidad de mensajes enviados por remitente y hora del día',
                          xaxis_title='Remitente',
                          yaxis_title='Hora del día')

    wordcloud_plot.update_layout(title='Nube de palabras',
                                 xaxis_title='Palabra',
                                 yaxis_title='Frecuencia')
    fig = sp.make_subplots(rows=1, cols=2, subplot_titles=(
        "Nube de palabras", "Heatmap"))
    fig.append_trace(wordcloud_plot.data[0], 1, 1)
    fig.append_trace(heatmap.data[0], 1, 2)
    fig.update_layout(xaxis=dict(title='Meses'),
                      yaxis=dict(title='Cantidad de texto'))

    logger.info("Mostrando gráficas")
    fig.show()


# Ejemplo de uso
# logging.disable(logging.INFO)
logger.info("Iniciando programa")
file_path = "Anibal.txt"  # <--- Aquí va el path del archivo de chat
df = process_chat(file_path)
plot_sender_chart(df)
plot_month_chart(df)
plot_hour_chart(df)
plot_month_hour_chart(df)
plot_word_cloud_heatmap(df)

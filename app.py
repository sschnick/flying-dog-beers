# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import json
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import csv
import math
from io import StringIO
from http import cookiejar  # Python 2: import cookielib as cookiejar
import requests
from bs4 import BeautifulSoup
from locale import atof, setlocale, LC_NUMERIC

outputFile = 'output_suv_wagon_20201205.csv'
dataFile = outputFile[:-4]+".pkl"

def scrape_autotrader(outputFile):
    class BlockAll(cookiejar.CookiePolicy):
        return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
        netscape = True
        rfc2965 = hide_cookie2 = False
    s = requests.Session()
    s.cookies.set_policy(BlockAll())
    
    setlocale(LC_NUMERIC, 'English_Canada.1252')
    
    urlHeaders = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
        }
    
    urlRoot = 'https://www.autotrader.ca'
    urlBase = urlRoot + '/cars/ab/calgary/'
    #urlBase = urlRoot + '/cars/kia/ab/calgary/'
    urlParams = '?srt=4&yRng=2017%2C&pRng=15000%2C40000&prx=250&prv=Alberta&loc=T2E%201C4&body=SUV%2CWagon&hprc=True&wcp=True&sts=New-Used&inMarket=advancedSearch&'
    
    recPerPage = 100
    recStart = 0
    
    
    urlPage = 'rcp=' + str(recPerPage) + '&rcs=' + str(recStart)
    urlFull = urlBase + urlParams + urlPage
    
    print('Retrieving records from url: {}'.format(urlFull))
    
    page = requests.get(urlFull, headers=urlHeaders)
    soup = BeautifulSoup(page.content, 'html.parser')
    recTotal = int(atof(soup.find(id="titleCount").text))
    
    # DEBUG: Comment out this value
    # recTotal = 10
    
    print('Total records: {}'.format(recTotal))
    
    items = []
    
    csvHeaders = ["ItemId", "Title", "Year", "Make", "Model", "Trim", "Price", "Link", "Details", "Mileage", "price_delta"]
    
    # with open(outputFile, 'w', newline='') as csvfile:
    #     writer = csv.DictWriter(csvfile, csvHeaders)
    #     writer.writeheader()
    
    for recCurrent in range(recStart,recTotal,recPerPage):
        print('Parsing records {} of {}'.format(recCurrent, recTotal))
        urlPage = 'rcp=' + str(recPerPage) + '&rcs=' + str(recCurrent)
        urlFull = urlBase + urlParams + urlPage
        #print(urlFull)
        page = requests.get(urlFull, headers=urlHeaders)
        soup = BeautifulSoup(page.content, 'html.parser')
        results = soup.find_all(class_="col-xs-12 result-item")
    
        for result in results:
            item = {}
            #print(result)
            item["ItemId"] = result["id"]
            item["Title"] = result.find(class_="result-title click").text.strip()
            
            try:
                item["Year"], item["Make"], item["Model"], item["Trim"] = item["Title"].split(' ',4)
            except:
                item["Year"], item["Make"], item["Model"] = item["Title"].split(' ',4)[:3]
                item["Trim"] = ""
                
            #item["title"][:4]
            #item["make"] = item["title"][:4]
            item["Price"] = atof(result.find(class_="price-amount").text.strip()[1:])
            item["Link"] = urlRoot + result.find(class_="result-title click")['href']
            item["Details"] = result.find(class_="listing-details").p.text.strip()
            
            try:
                item["Mileage"] = atof(result.find(class_="kms").text.strip().split(' ',2)[1])
            except:
                item["Mileage"] = 0.0
                
            #item.values()
            try:
                item["price_delta"] = result.find(class_="price-delta-text").text.strip()
            except:
                item["price_delta"] = ""
            
            image_url = result.find(class_='main-photo click').img['data-original']
            item["photoUrl"] = image_url
            # item["photoData"] = Image.open(requests.get(image_url, stream = True).raw)

            items.append(item)
    
    print('Creating DataFrame...')
    df = pd.DataFrame(items)
    
    df = df.sort_values(by=['Make','Model','Year','Price'])
    df['Make-Model'] = df['Make'] + ' ' + df['Model']
    
    df['Fuel'] = 'Gas'
    df.loc[df['Title'].str.contains('Hybrid'), 'Fuel'] = 'Hybrid'
    df.loc[df['Title'].str.contains('Prius'), 'Fuel'] = 'Hybrid'
    df.loc[df['Title'].str.contains('Niro'), 'Fuel'] = 'Hybrid'
    df.loc[df['Title'].str.contains('EV'), 'Fuel'] = 'EV'
    df.loc[df['Title'].str.contains('Electric'), 'Fuel'] = 'EV'
    df.loc[df['Title'].str.contains('PHEV'), 'Fuel'] = 'PHEV'
    
    # df['Year'] = df['Year'].apply(str)
    
    # df = df[df.Model.isin([
    #     'Niro',
    #     #'Soul',
    #     'RAV4',
    #     'Prius',
    #     'Qashqai',
    #     'Rogue',
    #     'Kona',
    # #    'Ioniq',
    #     'Outlander',
    #     'Crosstrek'
    # ])]
    
    df.sort_values(by=['Year'], inplace=True)
    
    # Save as pickle
    print('Saving as pickle...')
    df.to_pickle(dataFile)
    
    print('Done.')
    
    # # Saving CSV file
    # print('Outputting CSV file: {}'.format(outputFile))
    
    # with open(outputFile, 'w', newline='') as csvfile:
    #     writer = csv.DictWriter(csvfile, csvHeaders, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
    #     writer.writeheader()
    #     writer.writerows(items)
    
    # print('Done outputting CSV file.')

    
def read_autotrader_csv(outputFile):
    # outputFile = 'output.csv'
    print('Reading CSV file: {}'.format(outputFile))
    
    import chardet
    outputFileEnc = chardet.detect(open(outputFile, 'rb').read())['encoding']
        
    df = pd.read_csv(outputFile, encoding=outputFileEnc, na_filter=False, index_col=False)
    
    print('Creating DataFrame...')
    
    df = df.sort_values(by=['Make','Model','Year','Price'])
    df['Make-Model'] = df['Make'] + ' ' + df['Model']
    
    df['Fuel'] = 'Gas'
    df.loc[df['Title'].str.contains('Hybrid'), 'Fuel'] = 'Hybrid'
    df.loc[df['Title'].str.contains('Prius'), 'Fuel'] = 'Hybrid'
    df.loc[df['Title'].str.contains('Niro'), 'Fuel'] = 'Hybrid'
    df.loc[df['Title'].str.contains('EV'), 'Fuel'] = 'EV'
    df.loc[df['Title'].str.contains('Electric'), 'Fuel'] = 'EV'
    df.loc[df['Title'].str.contains('PHEV'), 'Fuel'] = 'PHEV'
    
    # df['Year'] = df['Year'].apply(str)
    
    df = df[df.Model.isin([
        'Niro',
        #'Soul',
        'RAV4',
        'Prius',
        'Qashqai',
        'Rogue',
        'Kona',
    #    'Ioniq',
        'Outlander',
        'Crosstrek'
    ])]
    
    df.sort_values(by=['Year'], inplace=True)
    
    # Save as pickle
    print('Saving as pickle...')
    df.to_pickle(dataFile)
    
    print('Done.')
    
    return df




scrape_autotrader(outputFile)
# df1 = read_autotrader_csv(outputFile)
df = pd.read_pickle(dataFile)

df = df[df.Model.isin([
    # 'Escape',
    # 'Edge',
    # 'CR-V',
    'QX50',
    'QX30',
    'Niro',
    # 'Soul',
    'RAV4',
    'Prius',
    'Qashqai',
    'Rogue',
    'Kona',
#    'Ioniq',
    # 'Outlander',
    # 'Crosstrek'
])]

available_models = df['Make-Model'].unique()

#%%
# itemId = '68762846'
# tempDf = df[df['ItemId'] == itemId]

# cardTitle = tempDf['Title'].iloc[0]
# cardDetails = tempDf['Details'].iloc[0]
# cardImg = tempDf['photoData'].iloc[0]

#%%
stepMileage = 5000
minMileage = 0
# maxMileage = int(math.ceil(df['Mileage'].max()/stepMileage)*stepMileage)
maxMileage = 65000
dictMarksMileage = {mileage:str(int(mileage/1000))+"k" for mileage in range(minMileage,maxMileage,stepMileage)}
dictMarksMileage[0] = 'New/Used'
dictMarksMileage[500] = ''

stepPrice = 1000
minPrice = int(math.floor(df['Price'].min()/stepPrice)*stepPrice)
maxPrice = int(math.ceil(df['Price'].max()/stepPrice)*stepPrice)
dictMarksPrice = {price:str(int(price/1000))+"k" for price in range(minPrice,maxPrice,stepPrice)}

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Build the layout
app.layout = dbc.Container(
    [
        dbc.Row(dbc.Col(html.H1('Cars on Autotrader'))),
        
        dbc.Row([
            dbc.Col([
                dbc.Row(dbc.Col(html.Label('Price'))),
                dbc.Row(dbc.Col(dcc.RangeSlider(
                        id='slider-price',
                        min=minPrice,
                        max=maxPrice,
                        step=stepPrice,
                        value=[minPrice,maxPrice],
                        marks=dictMarksPrice),
                    )),
                dbc.Row(dbc.Col(html.Label('Mileage'))),
                dbc.Row(dbc.Col(dcc.RangeSlider(
                        id='slider-mileage',
                        min=minMileage,
                        max=maxMileage,
                        step=stepMileage,
                        value=[minMileage,maxMileage],
                        marks=dictMarksMileage),
                    )),
                dbc.Row(dbc.Col(dcc.Graph(id='price-vs-mileage'))),
                ],width=8),
            dbc.Col([
                dbc.Row(dbc.Col(dbc.Card(id='click-data'))),
                dbc.Row(dbc.Col(dcc.Graph(id='model-year')))
                ]),
            ]),
    ],
    fluid=True,
)

@app.callback(
    Output('price-vs-mileage', 'figure'),
    Input('slider-mileage', 'value'),
    Input('slider-price', 'value'))
def update_figure(mileageVal, priceVal):
    
    dfTemp = df.query(
        ' Mileage >= ' + str(mileageVal[0]) + ' & Mileage <= ' + str(mileageVal[1]) + ' & ' +
        ' Price >= ' + str(priceVal[0]) + ' & Price <= ' + str(priceVal[1])
        )
    
    fig = px.scatter(
        data_frame=dfTemp,
        x='Mileage', 
        y='Price', 
        color='Make-Model',
        marginal_x='rug',
        marginal_y='rug',
        # hover_name='Title',
        # text='Title',
        hover_data=['ItemId'],
    )
    # fig.update_traces(marker=dict(size=6), hovertemplate=None)
    # fig.update_xaxes(rangeslider_visible=True)
    fig.update_layout(transition_duration=500)
    fig.update_layout(clickmode='event')

    return fig

@app.callback(
    Output('model-year', 'figure'),
    Input('price-vs-mileage', 'clickData'),
    Input('model-year', 'clickData'), prevent_initial_call=True)
def update_figure_model(inData1, inData2):
    ctx = dash.callback_context
    if ctx.triggered:
        input_id = ctx.triggered[0]['prop_id'].split(".")[0]
    
        if input_id == 'price-vs-mileage':
            hoverDataFromPriceMileage = inData1
        elif input_id == 'model-year':
            hoverDataFromPriceMileage = inData2
        else:
            hoverDataFromPriceMileage = None

    if hoverDataFromPriceMileage is None:
        itemId = ''
    else:
        pointData = hoverDataFromPriceMileage['points'][0]
        
        itemId = pointData['customdata'][0]
        dfSelectedPoint = df[df['ItemId'] == itemId]
        
    itemMakeModel = dfSelectedPoint['Make-Model'].iloc[0]
    dfSameMakeModel = df[df['Make-Model'] == itemMakeModel]

    figAllPoints = px.scatter(
        data_frame=dfSameMakeModel,
        x='Mileage', 
        y='Price', 
        color='Mileage',
        facet_col='Year',
        hover_name='Title',
        hover_data=['ItemId'],
    )
    
    figSelectedPoint = px.scatter(
        data_frame=dfSelectedPoint,
        x='Mileage', 
        y='Price', 
        # color='Mileage',
        color_discrete_sequence=['red'],
        # facet_col='Year',
        # hover_name='Title',
        hover_data=['ItemId'],
    )
    figSelectedPoint.update_traces(marker=dict(size=10, line=dict(width=2, color='DarkSlateGrey')), selector=dict(mode='markers'))
    
    selectedYear = dfSelectedPoint['Year'].iloc[0]
    allYears = sorted(dfSameMakeModel.Year.unique())
    colYear = allYears.index(selectedYear)+1
    figAllPoints.add_trace(figSelectedPoint.data[0], row=1, col=colYear)
    
    figAllPoints.update_layout(transition_duration=500)
    figAllPoints.update_layout(clickmode='event')

    return figAllPoints

@app.callback(
    Output('click-data', 'children'),
    Input('price-vs-mileage', 'clickData'),
    Input('model-year', 'hoverData'), prevent_initial_call=True)
def display_click_data(inData1, inData2):
    ctx = dash.callback_context
    if ctx.triggered:
        input_id = ctx.triggered[0]['prop_id'].split(".")[0]
    
        if input_id == 'price-vs-mileage':
            clickData = inData1
        elif input_id == 'model-year':
            clickData = inData2
        else:
            clickData = None
            
    if clickData is None:
        cardTitle = 'No point clicked yet'
        itemId = 'No ItemId'
        cardDetails = 'No point data'
        cardImgFile = 'No image'
        itemUrl = ''
        itemPrice = ''
        itemMileage = ''
    else:
        pointData = clickData['points'][0]
        # title = pointData['hovertext']
        itemId = pointData['customdata'][0]
        # cardText = json.dumps(clickData, indent=2)
        
        tempDf = df[df['ItemId'] == itemId]
        cardTitle = tempDf['Title'].iloc[0]
        cardDetails = tempDf['Details'].iloc[0]
        cardImgFile = tempDf['photoUrl'].iloc[0]
        itemUrl = tempDf['Link'].iloc[0]
        itemPrice = tempDf['Price'].iloc[0]
        itemMileage = tempDf['Mileage'].iloc[0]
        
        # cardImg = dbc.CardImg(src=cardImgFile, bottom=True)
        
    card = [
        dbc.CardBody([
            html.H5(cardTitle, className="card-title"),
            dbc.Row([
                dbc.Col(dbc.NavLink(itemId, href=itemUrl)),
                dbc.Col(html.H6(itemPrice)),
                dbc.Col(html.H6(itemMileage)),
                ]),
            
            dbc.Row([
                dbc.Col(dbc.CardImg(src=cardImgFile, top=True)),
                dbc.Col(html.P(cardDetails, className="card-text")),
            ])
        ], className="card-body")
    ]
    
    # return json.dumps(clickData, indent=2)
    return card



if __name__ == '__main__':
    app.run_server(debug=True)

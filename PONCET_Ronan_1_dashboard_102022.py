# Import des librairies
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import streamlit as st
import seaborn as sns
import os
from sklearn import metrics
from sklearn.metrics import f1_score, roc_auc_score, PrecisionRecallDisplay, RocCurveDisplay, log_loss
import joblib
import shap
import pickle
from io import BytesIO
import requests
import json
st.set_option('deprecation.showPyplotGlobalUse', False)




@st.cache
def read(): 
    path= "./" 
    data=pd.read_csv(os.path.join(path,'df_prepro.csv'))
    data = data[data['TARGET'].notnull()].dropna(1).drop(['index','Unnamed: 0.1','Unnamed: 0'],1)
    results=pd.read_csv(os.path.join(path,'prediction.csv'))
    loaded_model = joblib.load('model_lgbm.pkl')
    results['TARGET']=results.TARGET.round(2)
    
    shap_values = np.load('shap_value.npy')    
    expected_values =np.load('explainer.npy')
    return data , results , loaded_model,shap_values,expected_values  

def plot(df,options,number ):
    value_client=df.query('SK_ID_CURR == @number')[options]
    if len(df[options].unique())<20:
        fig, ax = plt.subplots()
        df_0=df[df['TARGET']==0]
        df_1=df[df['TARGET']==1]
        d = {'0': df_0[options].value_counts().sort_index(axis=0),
             '1': df_1[options].value_counts().sort_index(axis=0),
             }
        cat_plot= pd.DataFrame(data=d)
        cat_plot.plot(kind='bar',ax=ax)
        value_client=df.query('SK_ID_CURR == @number')[options]
        ax.plot(value_client,1 , marker = '|', linestyle = '' , color='green')
    else:     
        fig=sns.displot(x=options,data=df,hue='TARGET')
        ymax=df.groupby(options).count().max()[0]
        
        st.write(df.groupby(options).count())
        plt.vlines(value_client,0,ymax, color='r', label='client')
    
    return fig
    
    
def client_plot(df,number):
    columns=list(df.drop(['SK_ID_CURR','TARGET'],1).columns)
    columns.insert(0,'Aucun')
    option = st.selectbox(
            'choix de la variable',
            columns)

    if option=='Aucun' :
        st.write('Choisissez une variable')
        st.stop()
    st.write('You selected:', option)
    fig = plot(df , option,number)
    st.pyplot(fig)

def explo_plot(df,clf,shap_values,expected_values):
    tresh=50
    number = st.number_input('Inserez le numero de client',min_value=0, max_value=999999)
    if number==0:
        st.stop()
    elif number not in df['SK_ID_CURR'].unique():
        st.error('Id client non valide')
        st.stop()

    st.write('Numero de client ', number)

    st.dataframe(df[df['SK_ID_CURR']==number])
    (X,y,y_pred)=result_pred(df,clf)
    index=df.query("SK_ID_CURR == @number").index.values[0]
    col1, col2 = st.columns(2)
    
    col1.metric("TARGET", df.query("SK_ID_CURR == @number")['TARGET'])
    col2.metric("Prediction", round(y_pred[index,1],2))
    if st.radio(
    "",
    ('Informations général', 'Importance des features dans la prediction'),horizontal=True )=='Informations général':
        client_plot(df,number)
    else:
        (X,y,y_pred)=result_pred(df,clf)
        shap_values_explaination = shap.Explanation(shap_values[index,:], feature_names=X.columns.tolist()) 
        fig, ax = plt.subplots()
        ax=shap.plots._waterfall.waterfall_legacy(expected_values[1],shap_values_explaination.values,
                                                  feature_names=X.columns.tolist(),max_display=20)
        st.pyplot(fig)



def button(df):
    page = st.sidebar.radio(
    "selectionnez",
    ('acceuil','client', 'model','obtenir une prediction'),index=0)
    return page

def result_pred(df,clf):
    
    X=df.drop(['TARGET','SK_ID_CURR'],1).copy()
    y=df['TARGET'].copy()
    results=clf.predict_proba(X)
    return X,y,results

    return plt

def metrique(X,y,clf,y_pred,y_tresh):


    
    
    log_loss_score=log_loss(y,y_pred)
    auc_score=roc_auc_score(y_tresh,y)
    score_f1=f1_score(y_tresh,y)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("log loss", log_loss_score)
    col2.metric("auc score",auc_score)
    col3.metric("f1 score", score_f1)
    
def shap_plot_mdl(shap_values,X,df):
    shap.initjs()
    columns=list(df.drop(['SK_ID_CURR','TARGET'],1).columns)
    columns.insert(0,'Informations générales')
    option = st.selectbox(
            'choix de la variable',
            columns)
    if option=='Informations générales':
        st.write(shap_values.shape)
        fig, ax = plt.subplots()
        ax=shap.summary_plot(shap_values, X,max_display=10)
        st.pyplot(fig)
    else:
        fig, ax = plt.subplots()
        fig = shap.dependence_plot(option, shap_values, X, display_features=X)
        st.pyplot(fig)
    
        
def pred_plot_mdl(y_tresh, y,df):
    #    shap_plot

    conf_mat = metrics.confusion_matrix(y_tresh, y)
    print(conf_mat)
    print()
    col1, col2 = st.columns(2)
    fig, ax = plt.subplots(figsize = (6,4))
    df_cm = pd.DataFrame(conf_mat, index = [label for label in set(y)],
                      columns = [i for i in "01"])
    ax=sns.heatmap(df_cm, annot=True, cmap="Blues")
    col1.pyplot(fig)
    number = col2.number_input("Entrez l'id client",min_value=0, max_value=999999)
    if number==0:
        st.stop()
    elif number not in df['SK_ID_CURR'].unique():
        st.error('Id client non valide')
        st.stop()
    x=df.query("SK_ID_CURR == @number").index.values[0]
    col2.metric("prediction",y_tresh[x])
    
    

    

def model(df,clf,shap_values,expected_values):
    
    st.title('Information général sur le modèle')
    
    (X,y,y_pred)=result_pred(df,clf)
    col1, col2 = st.columns(2)
    
    fig_ROC = RocCurveDisplay.from_estimator(clf, X, y)
    col1.pyplot(fig_ROC.figure_)
    fig_ROC = PrecisionRecallDisplay.from_estimator(clf, X, y)
    col2.pyplot(fig_ROC.figure_)
    tresh_min=round((y_pred[:,1].min()*100)+1)
    tresh_max=round((y_pred[:,1].max()*100)-2)
    st.write("Le treshold correspond à la probabilité minal pour que la prédiction d'un cliant pour que celui ci dans la catégorie 1")
    st.write("Ex: un client avoir un prediction de 0.4 pour la classe 1 sera predit:")
    st.write(" - Dans la classe 0 si le treshold est superieur a 20")
    st.write(" - Dans la classe 1 sinon")
    tresh = st.slider(
    'Select a range of values',
    tresh_min, tresh_max)
    st.write('Treshold:', tresh)
    w=lambda x : 0 if x < (tresh/100) else 1
    y_tresh=np.array([w(xi) for xi in y_pred[:,1]])
    st.write("Vous pouvez trouver ci dessous les résultats des différentes métriques ainsi que la matrice de confusion pour le treshold séléctionné")
    st.write("Dans la partie 'Features Importance' vous pourrez trouvez un summary plot montrant les features les plus importantes du model")
    st.write("Vous trouverez pour chaque variable le dependance plot de la variable avec laquelle elle est le plus corrélée")
    metrique(X,y,clf,y_pred,y_tresh)

    if st.radio(
    "",
    ('Predictions', 'Feature importances'),horizontal=True)=='Predictions':
        pred_plot_mdl(y_tresh, y,df)
    else:    
        shap_plot_mdl(shap_values,X,df)
    
    
    
def predict_new(df):
    data_name=['application_train.csv','application_test.csv', 'bureau.csv' ,'bureau_balance.csv' , 'credit_card_balance.csv', 'installments_payments.csv', 'POS_CASH_balance.csv', 'previous_application.csv']
    st.write("Pour obtenir la prédiction d'un nouveau client vous devez ajouter 7 Dataframes nommés : ")
    
    uploaded_files = st.file_uploader("Choose a CSV file", type = 'csv', accept_multiple_files=True)
    dicti={}
    for uploaded_file in uploaded_files:
        bytes_data = uploaded_file.read()
        st.write("filename:", uploaded_file.name)
        data=pd.read_csv(BytesIO(bytes_data))
        dicti[uploaded_file.name[:-4]]=data.to_json()
    st.write(dicti.keys())
    
    if len(dicti) == 8:
            
            response = requests.post('https://p7apirp.herokuapp.com/predict', json=dicti)
            st.write(response.content)
            
            
            response = requests.post('https://p7apirp.herokuapp.com/prepro', json=dicti)
            response=json.loads(response.content.decode("utf-8").replace("'",'"'))
            client_data=pd.DataFrame.from_dict(response,orient='index')

    if len(dicti) == 8:
        try:
            
            response = requests.post('https://p7apirp.herokuapp.com/predict', json=dicti)
            st.write(response.content)
            
            
            response = requests.post('https://p7apirp.herokuapp.com/prepro', json=dicti)
            response=json.loads(response.content.decode("utf-8").replace("'",'"'))
            client_data=pd.DataFrame.from_dict(response,orient='index')
            
        except:
            st.write('error')
            
    

    number=client_data['SK_ID_CURR'][0]
    df=df[client_data.columns]
    df=df.merge(client_data, left_on='SK_ID_CURR', right_on='SK_ID_CURR')
    st.write(df)
    
    client_plot(df,number)
    
    

            
    
        

    
    
 
            
def acceuil():
    st.title('Ronan PONCET')
    st.title('Projet 7 implementez un model de scoring')
    st.title('Dashboard')
        
    st.write('Bienvenue !')
    st.write("Dans la partie 'Client' vous trouverez toutes les informations des clients deja présent dans la base de donnée et leurs comparaison avec les autres clients")
    st.write("Dans la partie 'Modèle' vous trouverez toutes les informations relative au modèle (Métrique , features importances ...)")
    st.write("Dans la partie 'Prédiction' vous pourrez ajouter les données d'un nouveau clients obtenir sa prédtion pour le modèle ainsi qu'un résumé de ses informations général")
    
    
    
#    score_auc=roc_auc_score(y_pred,y,average='macro')
#    col1, col2 = st.columns(2)
#    col1.metric("TARGET", )
#    col2.metric("Prediction", 2)
#    st.write('goodbye')
    
    
        
def main():
    
    (df,result,clf,shap_values,expected_values)=read()
    page=button(df)
        
        
    if (page=='acceuil'):
        acceuil()
    elif (page=='client'):
        explo_plot(df,clf,shap_values,expected_values)
    elif(page=='model') :
        model(df,clf,shap_values,expected_values)
    else :
        predict_new(df)
    

if __name__ == '__main__':
    main()
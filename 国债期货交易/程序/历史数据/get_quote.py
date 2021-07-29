# -*- coding: utf-8 -*-
"""
Created on Tue May 12 00:58:44 2020

@author: Administrator
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt 
import time
import math
from datetime import datetime
import os
from scipy.stats import norm
import statsmodels.api as sm
from dateutil.relativedelta import relativedelta
from WindPy import w
w.start()

os.chdir('F:/phd/FI_HW') 
#设置需要计算的起始日
begindate='2018-12-20'
enddate='2020-04-30'
fut='T'

datelist=w.tdays(begindate, enddate, "").Data[0]
code_info=pd.read_hdf(fut+'_code_info.h5')


future_quote=pd.DataFrame()
bond_quote=pd.DataFrame()

#get quote data 
for date in datelist:
    t1=time.clock()
    future_code=code_info.loc[((code_info.contract_issue_date<=date) & (code_info.last_trade_date>=date)),'wind_code'].unique().tolist()
    bond_code=code_info.loc[((code_info.contract_issue_date<=date) & (code_info.last_trade_date>=date) & ((code_info.CARRYDATE<=date))),'bond_code'].unique().tolist()
    #get future settle_price and bond zhongzhai valuation
    settle=w.wsd(future_code, "settle", date, date, "",).Data[0]
    tmp1=pd.DataFrame()
    tmp1['settle']=settle
    tmp1['wind_code']=future_code
    tmp1['date']=date
    future_quote=pd.concat([future_quote,tmp1])
    tmp2=pd.DataFrame(columns=['bond_code','date','net_cnbd','dirty_cnbd'])
    net_cnbd=[]
    dirty_cnbd=[]
    #for code in bond_code:
    net_cnbd=w.wsd(bond_code, "net_cnbd", date, date, "credibility=1").Data[0]              
    dirty_cnbd=w.wsd(bond_code, "dirty_cnbd", date, date, "credibility=1").Data[0]
    tmp2['bond_code']=bond_code
    tmp2['date']=date
    tmp2['net_cnbd']=net_cnbd
    tmp2['dirty_cnbd']=dirty_cnbd
    bond_quote=pd.concat([bond_quote,tmp2])
    t2=time.clock()
    print(str(date)+" %0.3f seconds "%(t2-t1))
    
bond_quote.to_hdf(fut+'_bond.h5',key='quote',format='table',mode='w')
future_quote.to_hdf(fut+'_fut.h5',key='quote',format='table',mode='w')




##获取shibor数据
raw_data=w.wsd("SHIBORON.IR,SHIBOR1W.IR,SHIBOR2W.IR,SHIBOR1M.IR,SHIBOR3M.IR,SHIBOR6M.IR,SHIBOR9M.IR,SHIBOR1Y.IR", "close", begindate, enddate, "")
yield_curve=pd.DataFrame()
tmp1=[]
tmp2=[]
tmp3=[]
t_list=[0,7.0/365,14.0/365,1.0/12,0.25,0.5,0.75,1]
for i in range(0,np.shape(raw_data.Data)[1]):
    for j in range(0,np.shape(raw_data.Data)[0]):
        tmp1.append(datelist[i])
        tmp2.append(t_list[j])
        tmp3.append(raw_data.Data[j][i])
yield_curve['date']=tmp1
yield_curve['term']=tmp2
yield_curve['rate']=tmp3
yield_curve.to_hdf('yield_curve.h5',key='curve',mode='w',format='table')
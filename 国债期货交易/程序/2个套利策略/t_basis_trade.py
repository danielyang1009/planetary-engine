# -*- coding: utf-8 -*-
"""
Created on Thu May 28 16:04:25 2020

@author: Administrator
"""

# -*- coding: utf-8 -*-
"""
Created on Thu May 28 11:13:08 2020

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

os.chdir('F:/phd/FI_HW/') 
t_ctd=pd.read_excel('t_ctd.xlsx')
tf_ctd=pd.read_excel('tf_ctd.xlsx')
t_quota=pd.read_excel('t_quota.xlsx')
tf_quota=pd.read_excel('tf_quota.xlsx')

th_open=-0.01
th_close=0.25


###t trade
t_table0=t_ctd.loc[t_ctd.t_code=='T00']
t_table0=t_table0.drop(['t_code','F_theory'],axis=1)
t_open=t_table0.loc[t_table0.IRR>=th_open]
t_close=t_table0.loc[t_table0.IRR<=th_close]
trade_table=pd.DataFrame()
open_flag=0

for date in t_table0.date.unique():
    if open_flag==0:
        if((t_table0.loc[t_table0.date==date,'BNOC'].values[0]<=th_open) & (t_table0.loc[t_table0.date==date,'last_trade_date'].values[0]>date)):
            tmp=t_table0.loc[t_table0.date==date]
            tmp['open_flag']=1
            trade_table=pd.concat([trade_table,tmp])
            open_flag=1
            bond_code=tmp.bond_code.values[0]
            wind_code=tmp.wind_code.values[0]
    else:
       tmp=t_quota.loc[((t_quota.date==date) & (t_quota.bond_code==bond_code) & (t_quota.wind_code==wind_code))] 
       if((tmp.BNOC.values[0]>=th_close) | (tmp.last_trade_date.values[0]==tmp.date.values[0])):
           tmp['open_flag']=0
           trade_table=pd.concat([trade_table,tmp])
           open_flag=0
       else:
            tmp['open_flag']=1
            trade_table=pd.concat([trade_table,tmp])
           
            
trade_table=trade_table.reset_index(drop=True)
trade_table['ret']=0
trade_table['bf_open_flag']=trade_table.open_flag.shift(1)
trade_table['bf_BNOC']=trade_table.BNOC.shift(1)
trade_table=trade_table.fillna(0)
trade_table.loc[((trade_table.open_flag==1) & (trade_table.bf_open_flag==1)),'ret' ]=trade_table.BNOC-trade_table.bf_BNOC
trade_table['ret']=trade_table.ret/100
ret_table=trade_table[['date','ret']]
date_table=pd.DataFrame()
date_table['date']=t_table0['date']

ret_table=pd.merge(date_table,ret_table,how='left',on='date')
ret_table=ret_table.fillna(0)
ret_table=ret_table


plt.figure(figsize=(10,5))
plt.grid()
plt.plot(ret_table.date,ret_table.ret.cumsum())
plt.title('T00-Arbitrage')


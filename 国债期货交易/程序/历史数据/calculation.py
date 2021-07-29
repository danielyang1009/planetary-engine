# -*- coding: utf-8 -*-
"""
Created on Tue May 12 22:30:49 2020

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
#设置需要计算的起始日，以及期货的类别
begindate='2018-12-20'
enddate='2020-04-30'
fut='TF'
datelist=w.tdays(begindate, enddate, "").Data[0]

##导入债券、期货的行情以及基础数据，并且合并到quota里
bond_quote=pd.read_hdf(fut+'_bond.h5').reset_index(drop=True)
future_quote=pd.read_hdf(fut+'_fut.h5').reset_index(drop=True)
code_info=pd.read_hdf(fut+'_code_info.h5')
quota=pd.DataFrame()
for date in datelist:
    code_code=code_info.loc[((code_info.contract_issue_date<=date) & (code_info.last_trade_date>=date) & (code_info.CARRYDATE<=date))]
    code_code['date']=date
    quota=pd.concat([quota,code_code])

quota=pd.merge(quota,future_quote,how='left',on=['date','wind_code'])
quota=pd.merge(quota,bond_quote,how='left',on=['date','bond_code'])
##由于国债在银行间、沪深交易所交易，我们只选用银行间的即可
quota=quota.loc[quota.bond_code.str.contains('.IB')].reset_index(drop=True)
## 期货剩余到期时间
quota['T_t']=(quota.last_delivery_month-quota.date).apply(lambda x:x.days/365.0)
##计算期货到期时，债券的累计利息，fut_AI_T和fut_AI是期货到期日时的应计利息时长和利息，方法是用期货到期日-债券发行日除以付息频率的倒数，比如付息频率1，从发行日到期货到期日期限为1.2，
##那么我们认为到期应计利息时长为0.2，据此计算应计利息
quota['fut_AI_T']=(quota.last_delivery_month-quota.CARRYDATE).apply(lambda x:x.days/365.0)%(1.0/quota.INTERESTFREQUENCY)
quota['fut_AI']=quota['fut_AI_T']*quota['COUPONRATE']
quota['coupon_paid1']=((quota.last_delivery_month-quota.CARRYDATE).apply(lambda x:x.days/365.0)/(1.0/quota.INTERESTFREQUENCY)).apply(lambda x:int(x))
quota['coupon_paid2']=((quota.date-quota.CARRYDATE).apply(lambda x:x.days/365.0)/(1.0/quota.INTERESTFREQUENCY)).apply(lambda x:int(x))
quota['bond_coupon_paid']=(quota['coupon_paid1']-quota['coupon_paid2'])*quota['COUPONRATE']/quota.INTERESTFREQUENCY
#quota['IRR']=(quota.settle*quota.CF+quota.fut_AI-quota.dirty_cnbd)/quota.dirty_cnbd/quota.T_t
quota['Basis']=quota.net_cnbd-quota.settle*quota.CF
quota['IRR']=(quota.settle*quota.CF+quota.fut_AI-quota.dirty_cnbd+quota.bond_coupon_paid)/(quota.dirty_cnbd-quota.bond_coupon_paid)/quota.T_t

##导入shibor曲线用线性插值的方法求每天不同剩余期限对应的无风险利率
yield_curve=pd.read_hdf('yield_curve.h5')

date_term=quota[['date','wind_code','T_t']].drop_duplicates().reset_index(drop=True)

rf=[]
for i in range(0,date_term.shape[0]):
    date=date_term.date[i]
    term=date_term.T_t[i]
    lower_term=yield_curve.loc[((yield_curve.date==date) & (yield_curve.term<=term)),'term'].max()
    lower_rate=yield_curve.loc[((yield_curve.date==date) & (yield_curve.term==lower_term)),'rate'].values[0]
    upper_term=yield_curve.loc[((yield_curve.date==date) & (yield_curve.term>=term)),'term'].min()
    upper_rate=yield_curve.loc[((yield_curve.date==date) & (yield_curve.term==upper_term)),'rate'].values[0]
    if (upper_term==lower_term):
        rf.append(lower_rate)
    else:
        rf.append((lower_rate*(upper_term-term)+upper_rate*(term-lower_term))/(upper_term-lower_term))
        
date_term['rf']=rf

quota=pd.merge(quota,date_term,how='left',on=['wind_code','date','T_t'])
quota=quota.reset_index(drop=True)
quota['carry']=quota.COUPONRATE*quota.T_t-quota.dirty_cnbd*quota.rf/100*quota.T_t
quota['BNOC']=quota.Basis-quota.carry
ctd_table=quota.groupby(['date','wind_code']).agg({'IRR':'max'}).reset_index()
ctd_table=pd.merge(ctd_table,quota,how='left',on=['date','wind_code','IRR'])
##计算ctd券的理论期货价格，这里走个江湖，本应该将债券在期限内的派息折现，但是因为利息的折现值影响不大，所以这里就不折现了
ctd_table['F_theory']=((ctd_table.dirty_cnbd-ctd_table.bond_coupon_paid)*(1+ctd_table.rf/100.0*ctd_table.T_t)-ctd_table.fut_AI)/ctd_table.CF

ctd_table.to_hdf(fut+'_ctd_table.h5',key='ctd',format='table',mode='w')
quota.to_hdf(fut+'_quota.h5',key='ctd',format='table',mode='w')

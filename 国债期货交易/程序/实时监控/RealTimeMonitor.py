# -*- coding: utf-8 -*-
"""
Created on Wed May 20 11:02:44 2020

@author: Administrator
"""

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

#os.chdir('F:/phd/FI_HW/') 
#设置日期和期货代码,以及监控的结束时间
date=datetime.today()
pre_date=w.tdaysoffset(-1, date, "").Data[0][0]
fut=['TF','T']
endhour=15
endminute=15
##日期转换成日期型，然后获取这一期间存续的期货合约基础信息
code_info=pd.DataFrame()
for i in range(0,len(fut)):
    
    para='startdate='+str(date)+';enddate='+str(date)+';wind_code='+fut[i]+'.CFE'
    code_info=pd.concat([code_info,w.wset("futurecc",para,usedf = True)[1]])
CF_table=pd.DataFrame()
# get CF data
for f_code in code_info.code:
    string="windcode="+f_code+".CFE"
    data=w.wset("conversionfactor",string,userdf=True).Data
    tmp=pd.DataFrame()
    tmp['bond_code']=data[0]
    tmp['CF']=data[1]
    tmp['code']=f_code
    CF_table=pd.concat([CF_table,tmp])
    
code_info=pd.merge(CF_table,code_info,how='left',on='code')

## get bond info

raw_data=w.wss(code_info.bond_code.unique().tolist(), "carrydate,maturitydate,interestfrequency,couponrate")
    
data=raw_data.Data
fields=raw_data.Fields
bond_code=raw_data.Codes
bond_info=pd.DataFrame()
for i in range(0,len(fields)):    
    bond_info[fields[i]]=data[i]
bond_info['bond_code']=bond_code

code_info=pd.merge(code_info,bond_info,how='left',on='bond_code')
code_info=code_info.drop(['sec_name','delivery_month','change_limit','target_margin'],axis=1)
code_info=code_info.reset_index(drop=True)
code_info['bond_code']=code_info['bond_code'].apply(lambda x:x.encode("utf-8"))
code_info['code']=code_info['code'].apply(lambda x:x.encode("utf-8"))
code_info['wind_code']=code_info['wind_code'].apply(lambda x:x.encode("utf-8"))


### get quote 
future_quote=pd.DataFrame()
bond_quote=pd.DataFrame()
future_code=code_info['wind_code'].unique().tolist()
bond_code=code_info['bond_code'].unique().tolist()
future_quote['wind_code']=future_code
bond_quote['bond_code']=bond_code
bond_quote['net_cnbd']=w.wsd(bond_code, "net_cnbd", pre_date, pre_date, "credibility=1").Data[0]              
bond_quote['dirty_cnbd']=w.wsd(bond_code, "dirty_cnbd", pre_date, pre_date, "credibility=1").Data[0]


##获取shibor数据
raw_data=w.wsd("SHIBORON.IR,SHIBOR1W.IR,SHIBOR2W.IR,SHIBOR1M.IR,SHIBOR3M.IR,SHIBOR6M.IR,SHIBOR9M.IR,SHIBOR1Y.IR", "close", pre_date, pre_date, "")
yield_curve=pd.DataFrame()

t_list=[0,7.0/365,14.0/365,1.0/12,0.25,0.5,0.75,1]
yield_curve['term']=t_list
yield_curve['rate']=raw_data.Data[0]
yield_curve['date']=date


#对系统时间进行判断，15:15之前每10s刷新一次
tmp_time=datetime.today()
while (tmp_time.hour*60+tmp_time.minute<endhour*60+endminute): 
    future_quote['settle']=w.wsq(future_code, "rt_latest").Data[0]  
    
    
    ##将所有数据合并计算
    
    quota=pd.DataFrame()
    
    
    quota=pd.merge(code_info,future_quote,how='left',on=['wind_code'])
    quota=pd.merge(quota,bond_quote,how='left',on=['bond_code'])
    ##由于国债在银行间、沪深交易所交易，我们只选用银行间的即可
    quota=quota.loc[quota.bond_code.str.contains('.IB')].reset_index(drop=True)
    ## 期货剩余到期时间
    quota['date']=date
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
    
    
    print(ctd_table[['wind_code','bond_code','IRR',"Basis",'BNOC','carry','F_theory']])
    ###到了中午就休息110分钟
    if((datetime.today().hour==11) & (datetime.today().minute>30)):
        time.sleep(6600)
    time.sleep(30)
    tmp_time=datetime.today()

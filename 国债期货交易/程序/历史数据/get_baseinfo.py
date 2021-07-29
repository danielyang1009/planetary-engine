# -*- coding: utf-8 -*-
"""
Created on Mon May 11 16:33:09 2020

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

os.chdir('F:\\phd') 
#设置需要计算的起始日
begindate='2018-07-01'
enddate='2020-04-30'
datelist=w.tdays(begindate, enddate, "").Data[0]
fut='T'

##日期转换成日期型，然后获取这一期间存续的期货合约基础信息
para='startdate='+str(begindate)+';enddate='+str(enddate)+';wind_code='+fut+'.CFE'
code_info=w.wset("futurecc",para,usedf = True)[1]


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
code_info.to_hdf(fut+'_code_info.h5',key='code_info',mode='w',format='table')


##code_info 里面存储着所有期货和债券的基础信息



    
yield_curve.to_csv('yield_curve.h5',key='curve',mode='w',format='table')
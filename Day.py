import Public
import pymongo as pm
import cx_Oracle as co
import datetime as dt
import numpy as np
import os
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'


def Day(facNameList, colList, sql, endDate=None):
    if endDate is None:
        dtNow = dt.datetime.now() - dt.timedelta(days=1)
        endDate = dt.datetime(dtNow.year, dtNow.month, dtNow.day)
    else:
        endDate = dt.datetime(endDate.year, endDate.month, endDate.day)
        if endDate.date() >= dt.datetime.now().date():
            endDate = dt.datetime(dt.datetime.now().year, dt.datetime.now().month, dt.datetime.now().day) - \
                      dt.timedelta(days=1)

    connStr = Public.GetPara('connStr')
    conn = co.connect(connStr)
    cursor = conn.cursor()
    mongoConn = Public.GetPara('mongoConn')
    mc = pm.MongoClient(mongoConn)
    db = mc['factor']

    # for each factor
    for f in range(len(facNameList)):
        facName = facNameList[f]
        col = colList[f]
        lastUpdateDate = Public.GetLastUpdateDate(facName, mc)
        tradingDateSet = Public.GetCalendar(lastUpdateDate, endDate)
        mongoDoc = db[facName].find_one({'_id': lastUpdateDate})
        mongoDoc = {} if mongoDoc is None else mongoDoc
        # save data day by day.
        currentDate = lastUpdateDate + dt.timedelta(days=1)
        while currentDate <= endDate:
            cursor.execute(sql.replace('{TRADE_DATE}', currentDate.strftime('%Y-%m-%d')))
            dataList = cursor.fetchall()
            isTrade = (currentDate in tradingDateSet)
            mongoDoc = {}  # if this statement is executed, invalid data will not be filled by previous value
            mongoDoc['_id'] = currentDate
            mongoDoc['_isTrade'] = isTrade
            mongoDoc['_updateTime'] = dt.datetime.now()
            for record in dataList:
                symbol = record[1]
                data = record[col]
                if data is not None : # and np.isfinite(data):
                    mongoDoc[symbol] = data
            db[facName].save(mongoDoc)
            print(facName + ' ' + str(currentDate))
            currentDate += dt.timedelta(days=1)
        db.cfgUpdate.save({'_id': facName, 'lastUpdateDate': endDate})

    ddd = 0


sqlPrc = "SELECT M.TRADE_DATE, CONCAT(I.STK_CODE, '_CS'), M.END_DATE, CLOSE_PRICE, CLOSE_PRICE_RE, RISE_DROP_RANGE_RE / 100, " \
         "       OPEN_PRICE, OPEN_PRICE_RE, STK_TOT_VALUE, STK_CIR_VALUE, TRADE_VOL, TRADE_AMUT, TURNOVER_RATE, " \
         "       CASE WHEN M.TRADE_DATE = M.END_DATE THEN 1 ELSE 0 END  " \
         "FROM UPCENTER.STK_BASIC_PRICE_MID M JOIN  UPCENTER.STK_BASIC_INFO I " \
         "		ON M.STK_UNI_CODE = I.STK_UNI_CODE AND M.ISVALID = 1 AND I.ISVALID = 1 " \
         "WHERE M.TRADE_VOL > 0 AND M.TRADE_DATE = TO_DATE('{TRADE_DATE}', 'YYYY-MM-DD') "
facNameList = ['DAY_CLOSE', 'DAY_RTN', 'DAY_TV', 'DAY_CV', 'DAY_VOL', 'DAY_AMT', 'DAY_TOR', 'DAY_PAU', 'DAY_CLO']
colList = [4, 5, 8, 9, 10, 11, 12, 13, 3]
Day(facNameList, colList, sqlPrc, endDate=dt.datetime.now())

sqlName = "SELECT DATE'{TRADE_DATE}', CONCAT(I.STK_CODE, '_CS'), N.CHAN_DATE, N.STK_SHORT_NAME  " \
          "FROM UPCENTER.STK_SHORT_NAME_CHAN N JOIN UPCENTER.STK_BASIC_INFO I " \
          "	 	    ON N.ISVALID = 1 AND I.ISVALID = 1 AND N.STK_UNI_CODE = I.STK_UNI_CODE " \
          "WHERE CHAN_DATE < DATE'{TRADE_DATE}' AND  " \
          "	     NOT EXISTS(SELECT * FROM UPCENTER.STK_SHORT_NAME_CHAN N1 " \
          "	  			    WHERE N1.STK_UNI_CODE = N.STK_UNI_CODE AND  " \
          "	  			 	      N1.CHAN_DATE > N.CHAN_DATE AND  " \
          "	  			 	      N1.CHAN_DATE < DATE'{TRADE_DATE}' AND " \
          "	  			 	      N1.ISVALID = 1) "
Day(['STA_NAME'], [3], sqlName)

sqlList = "SELECT DATE'{TRADE_DATE}', CONCAT(I.STK_CODE, '_CS'), LIST_DATE, " \
          "       CEIL(DATE'{TRADE_DATE}' - LIST_DATE) AS LIST_DAYS " \
          "FROM UPCENTER.STK_BASIC_INFO I " \
          "WHERE I.ISVALID = 1 AND " \
          "	     LIST_DATE < DATE'{TRADE_DATE}' AND " \
          "	     (END_DATE > DATE'{TRADE_DATE}' OR END_DATE IS NULL) AND  " \
          "	     (SEC_MAR_PAR = 1 OR SEC_MAR_PAR = 2) "
Day(['STA_LIST'], [3], sqlList)
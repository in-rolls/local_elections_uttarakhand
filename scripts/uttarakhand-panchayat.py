#!/usr/bin/env python
# coding: utf-8

import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

s = requests.Session()

out_df = None

post_map = {0: 'Panchayat', 5: 'Block', 10: 'Dist'}

for np in ['gp2008', 'gp2014', 'gp2019']:
    print(np)
    r = s.get('https://secresult.uk.gov.in/', headers=headers, verify=False)
    #print(r.status_code)
    assert r.status_code == 200
    soup = BeautifulSoup(r.content)
    viewstategenerator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']
    viewstateencrypted = soup.find('input', {'id': '__VIEWSTATEENCRYPTED'})['value']
    viewstate = soup.select_one('#form1 input[name*="__VIEWSTATE"]')['value']
    data = {'__EVENTTARGET': np,
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__VIEWSTATEENCRYPTED': viewstateencrypted,
           }
    r = s.post('https://secresult.uk.gov.in/secresult.aspx', headers=headers, data=data, verify=True)
    #print(r.status_code)
    assert r.status_code == 200
    soup = BeautifulSoup(r.content)
    links = soup.find_all('a', {'id': re.compile('ContentPlaceHolder1_GridView1_hldist\d+_\d+')})
    districts = []
    for c in links[0].parent.parent.parent.find_all('th')[2:-1]:
        districts.append(c.text.strip())
    for l in links:
        href = None
        id = l.attrs['id']
        m = re.match('ContentPlaceHolder1_GridView1_hldist(\d+)_(\d+)', id)
        if m:
            row = int(m.group(2))
            col = int(m.group(1))
            if row not in [0, 5, 10]:
                continue
            tds = l.parent.parent.find_all('td')
            if len(tds) == 16:
                h1 = tds[0].text
                h2 = tds[1].text
            elif len(tds) == 15:
                h2 = tds[0].text
            if 'href' in l.attrs:
                href = 'https://secresult.uk.gov.in/panch_result/' + l.attrs['href']
            declare_result = l.text.strip()
            off = 3 if row in [0, 5] else 2
            unopposed_elected = soup.find('a', {'id': 'ContentPlaceHolder1_GridView1_hldist%d_%d' % (col, row + off)}).text.strip()
            district = districts[col - 1]
            print(href, row, col, '<%s>, <%s>' % (h1, h2), district, declare_result, unopposed_elected)
            #print('-'*50)
        if href:
            r = s.get(href, headers=headers, verify=True)
            #print(r.status_code)
            assert r.status_code == 200
            soup2 = BeautifulSoup(r.content)
            links2 = soup2.find_all('a', {'href': re.compile('frmDetails.aspx.*')})
            df = pd.read_html(r.content, attrs={'id': 'ContentPlaceHolder1_gv%s' % post_map[row]}, encoding='utf-8')[0]
            assert len(df) == len(links2)
            for i, l2 in enumerate(links2):
                common = df.iloc[i].to_dict()
                href2 = 'https://secresult.uk.gov.in/panch_result/' + l2.attrs['href']
                #print(common, href2)
                #print(np, row, col, i, len(df))
                r = s.get(href2, headers=headers, verify=True)
                #print(r.status_code)
                assert r.status_code == 200
                try:
                    df2 = pd.read_html(r.content, attrs={'id': 'ContentPlaceHolder1_GridView1'}, encoding='utf-8')[0]
                    df2.rename(columns={'चुनाव चिन्‍ह': 'चुनाव चिन्‍ह.2', 'प्राप्‍त मत': 'प्राप्‍त मत.2'}, inplace=True)
                    df2['Year'] = np[2:]
                    df2['निर्वाचित पद'] = h1
                    df2['जनपद'] = district
                    df2['घोषित परिणाम'] = declare_result
                    df2['निर्विरोध निर्वाचित'] = unopposed_elected
                    for k in common:
                        v = common[k]
                        df2[k] = v
                    #print(df2)
                    if out_df is None:
                        out_df = df2
                    else:
                        out_df = pd.concat([out_df, df2])
                except Exception as e:
                    print(e)
                    print(np, row, col, i, len(df))
                #break
            #break
    #break

out_df = out_df[['Year',
 'निर्वाचित पद',
 'जनपद',
 'घोषित परिणाम',
 'निर्विरोध निर्वाचित',
 'विकास खण्\u200dड',
 'ग्राम पंचायत',
 'आरक्षण स्थिति',
 'विजयी प्रत्\u200dयाशी का नाम',
 'चुनाव चिन्\u200dह',
 'प्राप्\u200dत मत',
 'प्रथम रनर अप प्रत्\u200dयाशी का नाम',
 'चुनाव चिन्\u200dह.1',
 'प्राप्\u200dत मत.1',
 'मतों का अन्\u200dतर',
 'क्षेत्र पंचायत वाडॅ',
 'जिला पंचायत वाडॅ',
 'क्रमांक',
 'अभ्\u200dयर्थी का नाम',
 'पिता/पति का नाम',
 'चुनाव चिन्\u200dह.2',
 'प्राप्\u200dत मत.2']]

out_df.drop_duplicates(inplace=True)

out_df.to_csv('data/uttarakhand-panchayat-elections.csv', index=False)

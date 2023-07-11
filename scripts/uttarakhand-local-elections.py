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

def extract_key_value(soup, id, tag='span', delimiter=':'):
    k, v = soup.find(tag, {'id': id}).text.split(delimiter)
    return k.strip(), v.strip()


out_df = None

for np in ['np2008', 'np2013', 'np2018', 'np2019']:
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
    viewstategenerator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']
    viewstateencrypted = soup.find('input', {'id': '__VIEWSTATEENCRYPTED'})['value']
    viewstate = soup.select_one('#form1 input[name*="__VIEWSTATE"]')['value']

    data = {'__EVENTTARGET': 'LinkButton4',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__VIEWSTATEENCRYPTED': viewstateencrypted,
           }
    r = s.post('https://secresult.uk.gov.in/result.aspx', headers=headers, data=data, verify=True)
    #print(r.status_code)
    assert r.status_code == 200
    results = r.content
    ##### Results Declared for Ward Members #####
    # District, NN/NP/NPP Name,
    # Ward Name(Seat Category),
    # Winning Candidate (Name-Party-Symbol),
    # First Runner-up Candidate (Name-Party-Symbol),
    df = pd.read_html(r.content, attrs={'id': 'GridView1'}, encoding='utf-8')[0]
    for i, m in enumerate(re.finditer(b'(GridView1\$ctl\d+\$lnkfindetall)', results)):
        print(np, i, len(df), m.group(1))
        soup = BeautifulSoup(r.content)
        viewstategenerator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']
        viewstateencrypted = soup.find('input', {'id': '__VIEWSTATEENCRYPTED'})['value']
        viewstate = soup.select_one('#form1 input[name*="__VIEWSTATE"]')['value']
        data = {'__EVENTTARGET': m.group(1),
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategenerator,
                '__VIEWSTATEENCRYPTED': viewstateencrypted,
               }
        r = s.post('https://secresult.uk.gov.in/result_final_detail2_All.aspx', headers=headers, data=data, verify=True)
        #print(r.status_code)
        assert r.status_code == 200
        soup = BeautifulSoup(r.content)
        #print(soup)
        # TODO: Parse result to
        # Local Bodies Election
        # -----------------------
        # Year, District, NN/NP/NPP Name,
        # Ward Name(Seat Category),
        # Winning Candidate (Name-Party-Symbol),
        # First Runner-up Candidate (Name-Party-Symbol),
        # Name, Ward,
        # Candidate, Party, Symbol, Votes Secured, Total Votes, Invalid Votes, Tender Votes, Valid Votes
        try:
            df2 = pd.read_html(r.content, attrs={'id': 'ContentPlaceHolder1_GridView1'}, encoding='utf-8')[0]
            common = df.loc[i].to_dict()
            df2['Year'] = np[2:]
            for k in common:
                v = common[k]
                if k != 'Detailed Result':
                    df2[k] = v
            for id in ['Dist', 'NP', 'Ward', 'Total', 'Cancel', 'Tender', 'Valid']:
                k, v = extract_key_value(soup, 'ContentPlaceHolder1_lbl%s' % id)
                if k == 'NN/ NPP/ NP Name':
                    k = 'Name'
                df2[k] = v
            if out_df is None:
                out_df = df2
            else:
                out_df = pd.concat([out_df, df2])
        except Exception as e:
            print(e)
        viewstategenerator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']
        viewstateencrypted = soup.find('input', {'id': '__VIEWSTATEENCRYPTED'})['value']
        viewstate = soup.select_one('#form1 input[name*="__VIEWSTATE"]')['value']            
        data = {'__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategenerator,
                '__VIEWSTATEENCRYPTED': viewstateencrypted,
                'ctl00$ContentPlaceHolder1$btnback': 'Back'
               }
        r = s.post('https://secresult.uk.gov.in/frmDetails2.aspx', headers=headers, data=data, verify=True)
        #print(r.status_code)
        assert r.status_code == 200
        break
    break


out_df = out_df[['Year', 'District', 'NN/NP/NPP Name', 'Ward Name(Seat Category)',
 'Winning Candidate (Name-Party-Symbol)', 'First Runner-up Candidate (Name-Party-Symbol)',
 'Name', 'Ward', 'Candidate', 'Party', 'Symbol', 'Votes Secured', 'Total Votes Polled',
 'Invalid Votes', 'Tender Votes', 'Valid Votes']]

out_df.drop_duplicates(inplace=True)

out_df.to_csv('../data/uttarakhand-local-elections.csv', index=False)

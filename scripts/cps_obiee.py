#!/usr/bin/env python3
"""Minimal OBIEE SOAP client for the public CPS BI portal (guest creds published by CPS)."""
import re, sys, urllib.request, html
BASE = "https://biportal.cps.edu/analytics-ws/saw.dll"
UA = "Mozilla/5.0 (Macintosh) Chrome/120"
NS = "urn://oracle.bi.webservices/v12"

def soap(service, body, ns=NS, timeout=120):
    env = ('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
           'xmlns:v12="%s"><soapenv:Header/><soapenv:Body>%s</soapenv:Body></soapenv:Envelope>' % (ns, body))
    req = urllib.request.Request(BASE + "?SoapImpl=" + service, data=env.encode(),
                                 headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '""', "User-Agent": UA})
    try:
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", "replace")

def logon(user="cpsbiguest", pw="hell0cpsb1"):
    r = soap("nQSessionService", "<v12:logon><v12:name>%s</v12:name><v12:password>%s</v12:password></v12:logon>" % (user, pw))
    m = re.search(r"<sawsoap:sessionID[^>]*>(.*?)</sawsoap:sessionID>", r)
    if not m: raise SystemExit("logon failed: " + r[:500])
    return m.group(1)

if __name__ == "__main__":
    s = logon(); print(s)

def sub_items(sid, path):
    r = soap("webCatalogService", "<v12:getSubItems><v12:path>%s</v12:path><v12:mask>*</v12:mask><v12:resolveLinks>true</v12:resolveLinks><v12:sessionID>%s</v12:sessionID></v12:getSubItems>" % (html.escape(path), sid))
    out = []
    for m in re.finditer(r"<sawsoap:itemInfo .*?</sawsoap:itemInfo>", r, re.S):
        b = m.group(0)
        g = lambda t: (re.search(r"<sawsoap:%s>(.*?)</sawsoap:%s>" % (t, t), b, re.S) or [None, ""])[1]
        out.append((html.unescape(g("path")), g("type"), g("lastModified")))
    return out

def walk(sid, path, depth=0, maxdepth=6, skip=()):
    for p, t, lm in sub_items(sid, path):
        print("  " * depth + "%s\t%s\t%s" % (p, t, lm), flush=True)
        if t == "Folder" and depth < maxdepth and not any(k in p for k in skip):
            walk(sid, p, depth + 1, maxdepth, skip)

def run_report(sid, path, maxrows=100000, refresh=False):
    r = soap("xmlViewService", "<v12:executeXMLQuery><v12:report><v12:reportPath>%s</v12:reportPath></v12:report><v12:outputFormat>SAWRowsetData</v12:outputFormat><v12:executionOptions><v12:async>false</v12:async><v12:maxRowsPerPage>%d</v12:maxRowsPerPage><v12:refresh>%s</v12:refresh><v12:presentationInfo>false</v12:presentationInfo></v12:executionOptions><v12:sessionID>%s</v12:sessionID></v12:executeXMLQuery>" % (html.escape(path), maxrows, "true" if refresh else "false", sid), timeout=600)
    return r

def read_report_xml(sid, path):
    r = soap("webCatalogService", "<v12:readObjects><v12:paths>%s</v12:paths><v12:resolveLinks>true</v12:resolveLinks><v12:errorMode>FullDetails</v12:errorMode><v12:returnOptions>ObjectAsString</v12:returnOptions><v12:sessionID>%s</v12:sessionID></v12:readObjects>" % (html.escape(path), sid))
    m = re.search(r"<sawsoap:catalogObject>(.*?)</sawsoap:catalogObject>", r, re.S)
    return html.unescape(m.group(1)) if m else r

def report_cols(xml):
    sa = re.search(r'subjectArea="([^"]*)"', xml)
    cols = re.findall(r"<sawx:expr [^>]*>(.*?)</sawx:expr>", xml, re.S)
    return (html.unescape(sa.group(1)) if sa else None), [html.unescape(c) for c in cols]

def parse_rowset(r):
    m = re.search(r'<sawsoap:rowset[^>]*>(.*?)</sawsoap:rowset>', r, re.S)
    if not m: return None, r
    rs = html.unescape(m.group(1))
    rows = []
    for row in re.findall(r"<Row>(.*?)</Row>", rs, re.S):
        d = {k: html.unescape(v) for k, v in re.findall(r"<(Column\d+)>(.*?)</Column\d+>", row, re.S)}
        rows.append(d)
    q = re.search(r"<sawsoap:queryID[^>]*>(.*?)</sawsoap:queryID>", r)
    fin = re.search(r"<sawsoap:finished[^>]*>(.*?)</sawsoap:finished>", r)
    return rows, (q.group(1) if q else None), (fin.group(1) if fin else None)

def count_select_cols(sql):
    body = sql.split(" FROM ")[0][len("SELECT "):] if sql.startswith("SELECT ") else sql
    depth = 0; inq = False; n = 1
    for ch in body:
        if ch == '"' : inq = not inq
        elif not inq:
            if ch == "(": depth += 1
            elif ch == ")": depth -= 1
            elif ch == "," and depth == 0: n += 1
    return n

def logical_sql(sid, sql, maxrows=50000):
    """Run logical SQL; returns list of row lists. Pages via fetchNext."""
    r = soap("xmlViewService", "<v12:executeSQLQuery><v12:sql>%s</v12:sql><v12:outputFormat>SAWRowsetData</v12:outputFormat><v12:executionOptions><v12:async>false</v12:async><v12:maxRowsPerPage>%d</v12:maxRowsPerPage><v12:refresh>false</v12:refresh><v12:presentationInfo>false</v12:presentationInfo></v12:executionOptions><v12:sessionID>%s</v12:sessionID></v12:executeSQLQuery>" % (html.escape(sql), maxrows, sid), timeout=900)
    allrows = []
    ncols = count_select_cols(sql)
    while True:
        res = parse_rowset(r)
        if res[0] is None:
            raise RuntimeError(r[:1500])
        rows, qid, fin = res
        allrows += [[row.get("Column%d" % i) for i in range(ncols)] for row in rows]
        if fin == "true" or not qid: break
        r = soap("xmlViewService", "<v12:fetchNext><v12:queryID>%s</v12:queryID><v12:sessionID>%s</v12:sessionID></v12:fetchNext>" % (qid, sid), timeout=900)
    return allrows

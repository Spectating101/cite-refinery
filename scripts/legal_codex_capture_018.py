"""018: read-only public record-location/access research. Never fetch a private case file.

These are policy/legal source documents, NOT the claimant's operational logs.
Fixed HTTPS endpoints, public-address TLS pinning, bounded bytes, no credentials,
no forms or requests submitted. Artifacts are expiring CI copies, not a vault.
"""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
from http.client import HTTPSConnection
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
from urllib.parse import urlsplit, urljoin

SOURCES={
 'dpia_2021':('https://informatiepuntkinderopvangtoeslag.rijksoverheid.nl/publicaties/9ebc0f244fb97cc58dbe3fb626e92a82/183622021-24-11-geb-interactieve-dienstverlening-v101pdfpdf.pdf','pdf',['KCH','bewaar','logging']),
 'privacy':('https://www.belastingdienst.nl/wps/wcm/connect/nl/toeslagen/content/privacyverklaring-toeslagen','html',['inzageverzoek','bewaren','90']),
 'portal':('https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/toeslagen/hoe_werken_toeslagen/mijn-toeslagen/hoe-werkt-mijn-toeslagen','html',['klikt','Uitbetaald','DigiD']),
 'woo':('https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/toeslagen/hoe_werken_toeslagen/ik_wil_informatie_over_toeslagen/ik_wil_vragen_om_informatie_openbaar_te_maken','html',['Iedereen','documenten','openbaar']),
 'ministerial_2025':('https://zoek.officielebekendmakingen.nl/kst-36708-28.html','html',['inzage','bezwaar','2012']),
 'cjeu_logs':('https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62021CJ0579','html',['dates and purposes','identity of the employees','Article 15']),
 'cjeu_copies':('https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62021CJ0487','html',['entire documents','essential','Article 15']),
}
LIMIT=12*1024*1024

def sha(b):return hashlib.sha256(b).hexdigest()
class Text(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in {'script','style'}:self.hidden+=1
 def handle_endtag(self,tag):
  if tag in {'script','style'}:self.hidden=max(0,self.hidden-1)
 def handle_data(self,data):
  if not self.hidden:self.parts.append(data)

def fetch(url):
 original=urlsplit(url);host=original.hostname
 for attempt in range(3):
  parsed=urlsplit(url)
  if parsed.scheme!='https' or parsed.hostname!=host or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError('unexpected redirected origin')
  addrs=[ipaddress.ip_address(a[4][0]) for a in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM,proto=socket.IPPROTO_TCP)]
  if not addrs or any(not x.is_global for x in addrs):raise ValueError('nonpublic DNS')
  address=str(addrs[0])
  class Pinned(HTTPSConnection):
   def connect(self):
    sock=socket.create_connection((address,443),timeout=25)
    try:self.sock=ssl.create_default_context().wrap_socket(sock,server_hostname=host)
    except BaseException:sock.close();raise
  conn=Pinned(host,443,timeout=25)
  try:
   conn.request('GET',parsed.path+('?' + parsed.query if parsed.query else ''),headers={'Host':host,'User-Agent':'LegalCodex/018 public-record research','Accept-Encoding':'identity'})
   response=conn.getresponse();ctype=response.getheader('Content-Type','')
   if response.status in {301,302,303,307,308}:
    url=urljoin(url,response.getheader('Location',''));continue
   if response.status!=200:raise ValueError('HTTP '+str(response.status))
   body=response.read(LIMIT+1)
   if len(body)>LIMIT:raise ValueError('source exceeds byte budget')
   return body,ctype,url
  finally:conn.close()
 raise ValueError('redirect limit')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',required=True);a=p.parse_args()
 root=Path(a.output_dir);root.mkdir(parents=True,exist_ok=False);rows=[]
 for sid,(url,fmt,terms) in SOURCES.items():
  row={'source_id':sid,'requested_url':url,'source_tier':'public_policy_or_access_law','captured_at':datetime.now(timezone.utc).isoformat()}
  try:
   raw,ctype,final=fetch(url);ext='pdf' if fmt=='pdf' else 'html';path=root/(sid+'.'+ext)
   if fmt=='pdf' and not raw.startswith(b'%PDF'):raise ValueError('not PDF')
   if fmt=='html' and 'html' not in ctype.lower():raise ValueError('not HTML')
   path.write_bytes(raw)
   if fmt=='pdf':
    subprocess.run(['pdftotext','-layout',str(path),str(root/(sid+'.txt'))],check=True,timeout=30)
    text=(root/(sid+'.txt')).read_text(encoding='utf-8')
   else:
    parser=Text();parser.feed(raw.decode('utf-8',errors='strict'));text=' '.join(parser.parts)
   normalized=re.sub(r'\s+',' ',text).strip()
   missing=[term for term in terms if term.casefold() not in normalized.casefold()]
   if missing:raise ValueError('source identity/content check failed: '+repr(missing))
   (root/(sid+'.txt')).write_text(text,encoding='utf-8')
   row.update(status='captured',final_url=final,raw_sha256=sha(raw),raw_bytes=len(raw),text_sha256=sha(text.encode()),tls_hostname_verified=True)
  except Exception as e:row.update(status='failed',error=type(e).__name__,detail=str(e)[:300])
  rows.append(row)
 result={'schema':'legal_codex.public_record_leads_capture_018.v1','sources':rows,'captured_count':sum(r['status']=='captured' for r in rows),'claimant_originals_obtained':0,'requests_submitted':0,'private_portal_accessed':False}
 (root/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
 # A failure is recorded and visible; CI cannot certify complete acquisition.
 return 0 if result['captured_count']==len(SOURCES) else 1
if __name__=='__main__':raise SystemExit(main())

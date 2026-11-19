"""019 public cross-case discovery snapshots; not private dossiers or proof of execution.

Fixed official endpoints, public DNS/TLS pinning, no credentials, no off-origin
redirects, no submitted requests. Original snapshots and extraction are review
inputs, not independent certification of source statements.
"""
from __future__ import annotations
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
from urllib.parse import urlsplit, urljoin
from xml.etree import ElementTree as ET

SOURCES = {
 'hospital_2024': ('https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:GHARL:2024:5384','xml','ECLI:NL:GHARL:2024:5384'),
 'hospital_2026': ('https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RBMNE:2026:7063','xml','ECLI:NL:RBMNE:2026:7063'),
 'staff_identity_2025': ('https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RVS:2025:3260','xml','ECLI:NL:RVS:2025:3260'),
 'finnish_tax_2026': ('https://www.finlex.fi/fi/viranomaiset/tietosuojavaltuutettu/2026/37','html','TSV/238/2022'),
 'contact_center_2026': ('https://www.adviescollegeicttoetsing.nl/documenten/2026/05/29/advies-modernisering-contact-center','html','Modernisering Contact Center'),
}
LIMIT=4*1024*1024

def normalize(s):return re.sub(r'\s+',' ',s).strip()
def sha(b):return hashlib.sha256(b).hexdigest()

class Page(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.hidden=0;self.buffer=[];self.blocks=[]
 def flush(self):
  text=normalize(' '.join(self.buffer));self.buffer=[]
  if text:self.blocks.append(text)
 def handle_starttag(self,tag,attrs):
  if tag in {'script','style','noscript'}:self.hidden+=1
  if not self.hidden and tag in {'p','div','li','h1','h2','h3','h4','section','article','main','br'}:self.flush()
 def handle_endtag(self,tag):
  if tag in {'script','style','noscript'}:self.hidden=max(0,self.hidden-1)
  if not self.hidden and tag in {'p','div','li','h1','h2','h3','h4','section','article','main','br'}:self.flush()
 def handle_data(self,data):
  if not self.hidden:self.buffer.append(data)

def extract(raw,kind,identity):
 if not 40<len(raw)<=LIMIT:raise ValueError('source byte budget')
 if kind=='xml':
  decoded=raw.decode('utf-8-sig')
  if '<!DOCTYPE' in decoded.upper() or '<!ENTITY' in decoded.upper():raise ValueError('XML entity declaration refused')
  root=ET.fromstring(raw)
  ns='http://purl.org/dc/terms/'
  if identity not in [e.text for e in root.iter('{'+ns+'}identifier')]:raise ValueError('wrong ECLI metadata')
  bodies=[e for e in root.iter() if e.tag.rsplit('}',1)[-1]=='uitspraak']
  if len(bodies)!=1:raise ValueError('one judicial ruling required')
  texts=[normalize(' '.join(p.itertext())) for p in bodies[0].iter() if p.tag.rsplit('}',1)[-1]=='para']
  metadata={'decision_dates':[e.text for e in root.iter('{'+ns+'}date')],
            'publication_values':[e.text for e in root.iter('{'+ns+'}issued')]}
 else:
  page=Page();page.feed(raw.decode('utf-8',errors='strict'));page.flush();texts=page.blocks;metadata={}
  if identity.casefold() not in ' '.join(texts).casefold():raise ValueError('expected official page identity absent')
 if sum(len(t) for t in texts)<500:raise ValueError('insufficient body content')
 return {'identity':identity,'format':kind,'metadata':metadata,
         'blocks':[{'id':f'p{i:04d}','text':t,'sha256':sha(t.encode())} for i,t in enumerate(texts,1)]}

def fetch(url):
 host=urlsplit(url).hostname
 for _ in range(3):
  parsed=urlsplit(url)
  if parsed.scheme!='https' or parsed.hostname!=host or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError('off-origin or unsafe redirect')
  ips=[ipaddress.ip_address(i[4][0]) for i in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM,proto=socket.IPPROTO_TCP)]
  if not ips or any(not a.is_global for a in ips):raise ValueError('nonpublic source DNS')
  ip=str(ips[0])
  class Connection(HTTPSConnection):
   def connect(self):
    sock=socket.create_connection((ip,443),timeout=25)
    try:self.sock=ssl.create_default_context().wrap_socket(sock,server_hostname=host)
    except BaseException:sock.close();raise
  conn=Connection(host,443,timeout=25)
  try:
   conn.request('GET',parsed.path+('?' + parsed.query if parsed.query else ''),headers={
      'Host':host,'Accept-Encoding':'identity','User-Agent':'LegalCodex/019 public jurisprudence research'})
   r=conn.getresponse()
   if r.status in {301,302,303,307,308}:url=urljoin(url,r.getheader('Location',''));continue
   if r.status!=200:raise ValueError(f'HTTP {r.status}; not captured')
   ctype=r.getheader('Content-Type','');raw=r.read(LIMIT+1)
   if len(raw)>LIMIT:raise ValueError('source too large')
   return raw,ctype,url
  finally:conn.close()
 raise ValueError('redirect limit')

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',required=True);args=p.parse_args(argv)
 dest=Path(args.output_dir);dest.mkdir(parents=True,exist_ok=False);rows=[]
 for sid,(url,kind,identity) in SOURCES.items():
  row={'source_id':sid,'url':url,'identity':identity,'format':kind,'attempted_at':datetime.now(timezone.utc).isoformat()}
  try:
   raw,ctype,final=fetch(url)
   if kind=='xml' and 'xml' not in ctype.lower():raise ValueError('not XML')
   if kind=='html' and 'html' not in ctype.lower():raise ValueError('not HTML')
   parsed=extract(raw,kind,identity)
   target=dest/(sid+'.'+kind);target.write_bytes(raw)
   if extract(target.read_bytes(),kind,identity)!=parsed:raise ValueError('re-extraction mismatch')
   (dest/(sid+'.json')).write_text(json.dumps(parsed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
   row.update(status='captured_and_reextracted',final_url=final,raw_sha256=sha(raw),raw_bytes=len(raw),
       block_count=len(parsed['blocks']),tls_hostname_verified=True)
  except Exception as e:row.update(status='failed',error=type(e).__name__,detail=str(e)[:240])
  rows.append(row)
 result={'schema':'legal_codex.cross_case_sources_019.v1','sources':rows,
     'captured_count':sum(r['status']=='captured_and_reextracted' for r in rows),
     'claimant_dossiers_obtained':0,'compliance_execution_verified':False,'requests_submitted':0}
 (dest/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result));return 0 if result['captured_count']==len(SOURCES) else 1
if __name__=='__main__':raise SystemExit(main())

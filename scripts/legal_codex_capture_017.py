"""017: bounded acquisition of three public judicial XML records, NOT operational logs."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPSConnection
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
from xml.etree import ElementTree as ET

HOST = 'data.rechtspraak.nl'
LIMIT = 1024 * 1024
SOURCES = {
    'district_2025': ('ECLI:NL:RBGEL:2025:1418', '2025-02-24'),
    'appeal_2026': ('ECLI:NL:RVS:2026:1753', '2026-03-25'),
    'comparator_2021': ('ECLI:NL:RVS:2021:1729', '2021-08-04'),
}

def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def parse(raw, ecli):
    if not isinstance(raw, bytes) or not 40 < len(raw) <= LIMIT:
        raise ValueError('XML size invalid')
    decoded = raw.decode('utf-8-sig')
    if '<!DOCTYPE' in decoded.upper() or '<!ENTITY' in decoded.upper():
        raise ValueError('XML DTD/entities forbidden')
    root = ET.fromstring(raw)
    ns = {'d': 'http://purl.org/dc/terms/'}
    if ecli not in [x.text for x in root.findall('.//d:identifier', ns)]:
        raise ValueError('requested ECLI absent from official metadata')
    sections = [x for x in root.iter() if x.tag.rsplit('}',1)[-1] == 'uitspraak']
    if len(sections) != 1:
        raise ValueError('exactly one ruling body required')
    ruling = sections[0]
    text = normalize(' '.join(ruling.itertext()))
    if len(text) < 500:
        raise ValueError('incomplete judicial text')
    paras = [{'id': f'p{i:04d}', 'text': normalize(' '.join(p.itertext()))}
             for i,p in enumerate([x for x in ruling.iter() if x.tag.rsplit('}',1)[-1]=='para'],1)]
    return {'ecli': ecli, 'text': text, 'text_sha256': sha(text.encode()),
            'paragraphs': paras,
            'metadata_dates': [x.text for x in root.findall('.//d:date',ns)],
            'metadata_publication_values': [x.text for x in root.findall('.//d:issued',ns)]}

def fetch(ecli):
    info = socket.getaddrinfo(HOST,443,type=socket.SOCK_STREAM,proto=socket.IPPROTO_TCP)
    addresses = [ipaddress.ip_address(x[4][0]) for x in info]
    if not addresses or any(not x.is_global for x in addresses):
        raise ValueError('non-public court endpoint DNS')
    address = str(addresses[0])
    class PinnedTLS(HTTPSConnection):
        def connect(self):
            raw = socket.create_connection((address,443),timeout=20)
            try:
                self.sock = ssl.create_default_context().wrap_socket(raw,server_hostname=HOST)
            except BaseException:
                raw.close(); raise
    conn = PinnedTLS(HOST,443,timeout=20)
    try:
        conn.request('GET','/uitspraken/content?Id='+ecli,headers={
            'Host':HOST,'Accept':'application/xml,text/xml','Accept-Encoding':'identity',
            'User-Agent':'LegalCodex/017 (+bounded public judicial chronology research)'})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError(f'HTTP {response.status}; redirects not followed')
        ctype=response.getheader('Content-Type','')
        if ctype.split(';')[0].strip().lower() not in {'text/xml','application/xml'}:
            raise ValueError('not court XML')
        raw=response.read(LIMIT+1)
        if len(raw)>LIMIT: raise ValueError('oversize source')
        return raw,ctype
    finally:
        conn.close()

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',required=True)
    args=p.parse_args(argv)
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=False)
    entries=[]
    for sid,(ecli,decided) in SOURCES.items():
        row={'source_id':sid,'ecli':ecli,'source_url':f'https://{HOST}/uitspraken/content?Id={ecli}',
             'attempted_at':datetime.now(timezone.utc).isoformat(),'expected_decision_date':decided}
        try:
            raw,ctype=fetch(ecli);extracted=parse(raw,ecli)
            if decided not in extracted['metadata_dates']:
                raise ValueError('decision date not corroborated by metadata')
            rawpath=out/(sid+'.xml');rawpath.write_bytes(raw)
            (out/(sid+'.json')).write_text(json.dumps(extracted,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            if parse(rawpath.read_bytes(),ecli)!=extracted: raise ValueError('re-extraction mismatch')
            row.update(status='captured_and_reextracted',raw_sha256=sha(raw),raw_bytes=len(raw),
                       text_sha256=extracted['text_sha256'],content_type=ctype,
                       tls_hostname_verified=True,source_kind='published_judgment',
                       is_original_operational_log=False,legal_authenticity_certified=False)
        except Exception as exc:
            row.update(status='failed',error=type(exc).__name__,detail=str(exc)[:240])
        entries.append(row)
    receipt={'schema':'legal_codex.judicial_capture_017.v1','attempts':entries,
             'successful':sum(x['status']=='captured_and_reextracted' for x in entries),
             'original_operational_logs_obtained':0,'publication_authorized':False}
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))
    return 0 if receipt['successful']==len(SOURCES) else 1
if __name__=='__main__':
    raise SystemExit(main())

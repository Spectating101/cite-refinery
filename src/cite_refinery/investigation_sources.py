"""Bounded public-source discovery for LLM-driven investigations.

The LLM chooses searches. Europe PMC supplies academic *abstract leads*;
Bing RSS discovers official institutions, whose own HTML is fetched and read.
A search hit/snippet is NEVER elevated to a verified source passage.
No arbitrary user URL fetching; only pre-approved official domains.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from xml.etree import ElementTree as ET

ALLOWED_OFFICIAL = (
    "who.int", "woah.org", "cdc.gov", "fao.org", "un.org", "worldbank.org",
    "wmo.int", "unicef.org", "oecd.org", "gov.uk", "nih.gov", "ecdc.europa.eu",
)


def _host_allowed(url: str) -> bool:
    p = urlparse(url)
    host = (p.hostname or "").lower()
    return (p.scheme == "https" and p.port in {None,443} and
            not (p.username or p.password) and
            any(host == domain or host.endswith("."+domain) for domain in ALLOWED_OFFICIAL))


class _GuardRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if _host_allowed(req.full_url) and not _host_allowed(newurl):
            raise ValueError("Official-site redirect left the approved domain list")
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def _fetch(url, *, max_bytes=1_200_000, timeout=14):
    req=Request(url, headers={"User-Agent":"CiteRefinery-Investigator/0.1 (research citation auditing)",
                              "Accept":"text/html,application/json,application/rss+xml,application/xml"})
    opener=build_opener(_GuardRedirect())
    with opener.open(req,timeout=timeout) as response:
        final=response.geturl()
        body=response.read(max_bytes+1)
        if len(body)>max_bytes:
            raise ValueError("response exceeds bounded source size")
        return body,final,response.headers.get("Content-Type","")


def _strip_markup(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>"," ",str(text or ""))).split())


class _Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[];self.current=[];self.depth=0;self.hidden=0
    def handle_starttag(self, tag,attrs):
        if tag in {"script","style","nav","footer","header"}:self.hidden+=1
        if tag in {"p","li"}:
            self.depth+=1
            if self.depth==1:self.current=[]
    def handle_endtag(self,tag):
        if tag in {"p","li"} and self.depth:
            self.depth-=1
            if self.depth==0:
                sentence=" ".join("".join(self.current).split())
                if 65<=len(sentence)<=2500:self.parts.append(sentence)
        if tag in {"script","style","nav","footer","header"} and self.hidden:self.hidden-=1
    def handle_data(self,data):
        if self.depth and not self.hidden:self.current.append(data)


def search_europe_pmc(query: str, *, limit=3, fetch=_fetch):
    q=" ".join(query.split())
    if not 4<=len(q)<=190 or not 1<=limit<=5:raise ValueError("invalid academic query or limit")
    url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?"+urlencode({
        "query":q,"format":"json","resultType":"core","pageSize":limit,
    })
    body,final,content_type=fetch(url)
    j=json.loads(body)
    results=[]
    for record in j.get("resultList",{}).get("result",[])[:limit]:
        title=_strip_markup(record.get("title",""))
        abstract=_strip_markup(record.get("abstractText",""))
        doi=record.get("doi")
        pmid=record.get("pmid")
        pmcid=record.get("pmcid")
        if len(abstract)<100 or not title:continue
        key=doi or pmcid or pmid or record.get("id")
        if not key:continue
        source_url=("https://doi.org/"+doi if doi else
                    "https://europepmc.org/article/MED/"+str(pmid) if pmid else
                    "https://europepmc.org/articles/"+str(pmcid))
        results.append({
            "id":"EPMC-"+hashlib.sha256(str(key).encode()).hexdigest()[:12],
            "url":source_url, "text":(title+". "+abstract)[:6500],
            "title":title,"origin_type":"scholarly_abstract_lead",
            "source_scope":"Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof",
            "retrieval_url":final,
            "source_record":str(key),
            "passage_sha256":hashlib.sha256((title+". "+abstract)[:6500].encode()).hexdigest(),
        })
    if len(results)<limit and len(q.split())>5:
        # Scientific full-conjunction queries can be over-specific. Use a
        # transparent broad fallback, never a fabricated abstract or citation.
        # Preserve the *first four* topical words and record fallback URL.
        tokens=[w for w in re.findall(r"[A-Za-z]{3,}",q) if w.lower() not in
                {"method","evaluation","controlled","statistical","study","analyses","comparison"}]
        short=" ".join(tokens[:4])
        if short and short.lower()!=q.lower():
            alt_url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?"+urlencode({
                "query":short,"format":"json","resultType":"core","pageSize":max(limit,3),
            })
            try:
                extra,actual,_=fetch(alt_url)
                j2=json.loads(extra)
                old={x["source_record"] for x in results}
                for article in j2.get("resultList",{}).get("result",[])[:max(limit,3)]:
                    title=_strip_markup(article.get("title",""))
                    abstract=_strip_markup(article.get("abstractText",""))
                    key=article.get("doi") or article.get("pmcid") or article.get("pmid") or article.get("id")
                    if not key or key in old or len(abstract)<100 or not title:continue
                    url=("https://doi.org/"+article["doi"] if article.get("doi") else
                         "https://europepmc.org/article/MED/"+str(article["pmid"]) if article.get("pmid") else
                         "https://europepmc.org/articles/"+str(article.get("pmcid")))
                    passage=(title+". "+abstract)[:6500]
                    results.append({"id":"EPMC-"+hashlib.sha256(str(key).encode()).hexdigest()[:12],
                        "url":url,"text":passage,"title":title,
                        "origin_type":"scholarly_abstract_lead",
                        "source_scope":"Europe PMC abstract from broadened search, not full-text verification",
                        "retrieval_url":actual,"source_record":str(key),
                        "passage_sha256":hashlib.sha256(passage.encode()).hexdigest(),
                        "fallback_query":short})
                    old.add(key)
                    if len(results)>=limit:break
            except (OSError,ValueError):pass
    return results


class _DiscoveryLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag!="a":return
        href=attrs.get("href","")
        parsed=urlparse("https:"+href if href.startswith("//") else href)
        links=parse_qs(parsed.query).get("uddg",[]) if "duckduckgo.com" in (parsed.hostname or "") else [href]
        for link in links:
            if _host_allowed(link) and link not in self.links:
                self.links.append(link)


def search_official(query: str, *, limit=2, fetch=_fetch):
    q=" ".join(query.split())
    if not 4<=len(q)<=190 or not 1<=limit<=4:raise ValueError("invalid official search")
    results=[];visited=set()
    # A public search discovery index supplies URL CANDIDATES, but every cited
    # official page must be retrieved from its real publisher (not an RSS snippet).
    terms=" ".join(x for x in re.findall(r"[A-Za-z]{4,}",q)
                   if x.lower() not in {"guidance","national","programme","programmes","programme","report","who","woah","site"})[:12]
    for domain in ("who.int","woah.org","cdc.gov"):
        # Brave's HTML results are publicly available on the test host;
        # Bing RSS returned unrelated non-domain hits despite site filters.
        search_url="https://search.brave.com/search?"+urlencode({"q":f"site:{domain} {terms[:110]}"})
        try:
            listing,_,_=fetch(search_url,max_bytes=300_000)
            parser=_DiscoveryLinks()
            parser.feed(listing.decode("utf-8","replace"))
        except (OSError,ValueError):
            continue
        for url in parser.links[:12]:
            if url in visited or not _host_allowed(url) or url.lower().split("?",1)[0].endswith((".pdf",".zip",".docx",".jpg",".png")):
                continue
            visited.add(url)
            try:
                body,final,media=fetch(url,max_bytes=1_500_000)
                if not _host_allowed(final) or "html" not in media.lower():continue
                html_parser=_Paragraphs()
                html_parser.feed(body.decode("utf-8","replace"))
                paragraphs=[]
                for paragraph in html_parser.parts:
                    if paragraph not in paragraphs:paragraphs.append(paragraph)
                tokens=[x for x in re.findall(r"[a-z]{4,}",q.lower()) if x not in
                        {"about","with","that","this","there","their","site"}]
                ranked=sorted(paragraphs,key=lambda text:-sum(t in text.lower() for t in tokens))
                # Omit a webpage if we cannot read sufficiently substantive paragraphs.
                if not ranked:continue
                excerpts=ranked[:6]
                text="\n\n".join(excerpts)[:6400]
                if len(text)<140:continue
                results.append({
                    "id":"OFFICIAL-"+hashlib.sha256(final.encode()).hexdigest()[:12],
                    "url":final, "text":text,
                    "title":_strip_markup(html_parser.parts[0])[:180],
                    "origin_type":"official_webpage_excerpt_unverified",
                    "source_scope":"Selected official-site HTML paragraphs. Not a current local outcome survey or program implementation audit.",
                    "retrieval_url":search_url,
                    "source_record":final,
                    "passage_sha256":hashlib.sha256(text.encode()).hexdigest(),
                })
                if len(results)>=limit:return results
            except (OSError,ValueError,ET.ParseError):
                continue
    # Provider fallback: official publisher's own searchable document index.
    # Unlike a curated source list, documents are discovered by the model's
    # search words and only accepted after fetching publisher HTML.
    words=[w for w in re.findall(r"[a-zA-Z]{3,}",q.lower()) if w not in
           {"who","woah","icam","official","report","data","guidance","annual"}]
    phrases=[]
    for phrase in (" ".join(words[:3])," ".join(words[:2])," ".join(words[1:4])):
        if len(phrase)>=6 and phrase not in phrases:phrases.append(phrase)
    for phrase in phrases:
        api="https://www.woah.org/wp-json/wp/v2/search?"+urlencode({"search":phrase,"per_page":8})
        try:
            raw,_,_=fetch(api,max_bytes=160_000)
            index=json.loads(raw)
        except (OSError,ValueError):
            continue
        if not isinstance(index,list):continue
        for item in index[:8]:
            url=item.get("url") if isinstance(item,dict) else None
            if not isinstance(url,str) or url in visited or not _host_allowed(url):continue
            # Publisher's own index can return adjacent but irrelevant topics.
            # Require a subject-bearing query term in the publisher title,
            # excluding generic words common to every policy document.
            title=_strip_markup(item.get("title", "")).lower()
            subjects=[w for w in re.findall(r"[a-z]{3,}",phrase.lower())
                      if w not in {"population","management","programme","program",
                                   "monitoring","report","study","evaluation","control",
                                   "health","public","annual","official"}]
            if subjects and not any(w in title for w in subjects):continue
            visited.add(url)
            try:
                body,final,media=fetch(url,max_bytes=1_500_000)
                if not _host_allowed(final) or "html" not in media.lower():continue
                parser=_Paragraphs();parser.feed(body.decode("utf-8","replace"))
                text="\n\n".join(parser.parts[:6])[:6400]
                if len(text)<140:continue
                results.append({
                    "id":"OFFICIAL-"+hashlib.sha256(final.encode()).hexdigest()[:12],
                    "url":final,"text":text,"title":_strip_markup(item.get("title", ""))[:280],
                    "origin_type":"official_webpage_excerpt_unverified",
                    "source_scope":"Publisher-indexed WOAH program article/guidance, not audited impact evidence.",
                    "retrieval_url":api,"source_record":final,
                    "passage_sha256":hashlib.sha256(text.encode()).hexdigest(),
                })
                if len(results)>=limit:return results
            except (OSError,ValueError):
                continue
    return results


def collect_sources(queries, *, academic_search=search_europe_pmc, official_search=search_official, per_query=2, max_sources=8):
    if not isinstance(queries,list) or not 1<=len(queries)<=6:raise ValueError("Expected 1-6 planned searches")
    records=[];failures=[];visited=set();fingerprints=set()
    for query in queries:
        if not isinstance(query,dict) or query.get("lane") not in {"academic","official"}:
            raise ValueError("Search lanes must be academic or official")
        raw=query.get("query")
        if not isinstance(raw,str) or not 4<=len(raw)<=190:
            raise ValueError("Search query requires 4-190 characters")
        try:
            hits=(academic_search if query["lane"]=="academic" else official_search)(raw,limit=per_query)
        except Exception as e:
            failures.append({"query":raw,"lane":query["lane"],"reason":type(e).__name__})
            continue
        for item in hits:
            digest=item.get("passage_sha256") or hashlib.sha256(item["text"].encode()).hexdigest()
            if item["url"] in visited or digest in fingerprints:continue
            visited.add(item["url"]);fingerprints.add(digest)
            records.append(item)
            if len(records)>=max_sources:break
        if len(records)>=max_sources:break
    return {"sources":records,"failures":failures,"searches_attempted":len(queries),
            "sources_acquired":len(records),"note":"Selected source abstracts/passages are unreviewed leads; page existence is not claim support."}

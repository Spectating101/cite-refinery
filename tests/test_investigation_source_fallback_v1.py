"""A failed external search index can fall back to the publisher's own index."""
import json
import unittest
from cite_refinery.investigation_sources import search_official

class PublisherFallbackTests(unittest.TestCase):
    def test_fallback_is_a_real_publisher_page_not_search_snippet(self):
        listing=[{'title':'Dog population management research',
                  'url':'https://www.woah.org/en/document/dog-population-management/'}]
        doc='''<html><body><p>Dog population management can complement rabies vaccination,
        monitoring and community surveillance. Monitoring demographic turnover is important
        for assessing dog population intervention approaches and evaluating their results.
        </p></body></html>'''
        requests=[]
        def fetch(url,**kwargs):
            requests.append(url)
            if '/wp-json/wp/v2/search' in url:
                return json.dumps(listing).encode(),url,'application/json'
            if '/en/document/' in url:
                return doc.encode(),url,'text/html'
            return b'<html>No matching external search results</html>',url,'text/html'
        records=search_official('dog population management evaluation',fetch=fetch,limit=2)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['url'],listing[0]['url'])
        self.assertEqual(records[0]['origin_type'],'official_webpage_excerpt_unverified')
        self.assertIn('demographic turnover',records[0]['text'])
        self.assertIn('/wp-json/wp/v2/search',records[0]['retrieval_url'])
        self.assertTrue(any('/en/document/' in x for x in requests))

if __name__=='__main__':unittest.main()

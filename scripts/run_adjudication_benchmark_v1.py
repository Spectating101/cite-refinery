"""Score blinded source-scope predictions; optional opt-in live LLM inference."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from cite_refinery.adjudication_benchmark import make_judge_prompt,score_benchmark
from cite_refinery.external_llm_runtime import invoke_semantic_llm

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--cases',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True)
 p.add_argument('--response-json',type=Path,default=None,help='Externally completed predictions; no LLM run')
 p.add_argument('--provider',default='copilot',choices=['copilot','codex','claude','gemini','ollama'])
 p.add_argument('--model',default=None)
 p.add_argument('--timeout',type=int,default=180)
 args=p.parse_args()
 dataset=json.loads(args.cases.read_text(encoding='utf-8'))
 if dataset.get('schema')!='cite_refinery.adjudication_benchmark.v1':raise ValueError('Unknown benchmark schema')
 cases=dataset['cases']
 if args.response_json:
  response=json.loads(args.response_json.read_text(encoding='utf-8'))
  method='external_json_response'
 else:
  response=invoke_semantic_llm(make_judge_prompt(cases),provider=args.provider,model=args.model,
                               timeout_seconds=args.timeout)['raw']
  method='model_'+args.provider+'_'+(args.model or ('auto' if args.provider=='copilot' else 'cli-default'))
 result=score_benchmark(cases,response)
 result['evaluation_method']=method
 result['source_doi']=dataset.get('source_doi')
 args.out.parent.mkdir(parents=True,exist_ok=True)
 args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
 answers=args.out.with_suffix('.raw_response.json')
 answers.write_text(json.dumps(response,indent=2,ensure_ascii=False)+'\n')
 print('EVALUATED',len(cases),'CORRECT',result['correct'],'ACCURACY',result['accuracy'],
       'FALSE_ENTAILMENTS',result['false_positive_entailment_count'],
       'FALSE_CONTRADICTIONS',result['false_contradiction_count'],
       'ABSTENTIONS',result['abstentions'])
 print('REPORT',args.out,'RAW_RESPONSE',answers)
if __name__=='__main__':main()

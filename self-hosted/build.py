#!/usr/bin/env python3
"""Create the independent edition using the existing training assets."""
import argparse,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
source=args.source.resolve();out=args.output.resolve();public=out/'public'
if source==public or source in public.parents or public in source.parents:raise SystemExit('Source and output must be separate directories')
if not (source/'business-cases.js').is_file():raise SystemExit('Training source not found')
if public.exists():shutil.rmtree(public)
shutil.copytree(source,public)
for name in ['lisa-chat.js','lisa-chat.css','lisa-stream.js','lisa-math.js']:(public/name).unlink(missing_ok=True)
p=public/'app.js';p.write_text(re.sub(r"^ if\(segment\.id==='kksb'\)import\('./lisa-chat\.js[^\n]+\n",'',p.read_text(),flags=re.M))
p=public/'completion.js';p.write_text(p.read_text().replace('https://fot-practice-km.c8cpv86h5k.chatgpt.site/api/training/completions','/api/training/completions'))
for p in public.rglob('*.html'):p.write_text(re.sub(r'^.*<link[^>]+href="/lisa-chat\.css[^\n]*\n','',p.read_text(),flags=re.M))
cases=json.loads((source/'business-cases.js').read_text().removeprefix('export const businessCases=').strip().removesuffix(';'))
metadata={key:{'version':case['version'],'questions':[{'id':q['id'],'options':len(q['options']),'required':bool(q.get('requireCorrect')),'correct':[i for i,o in enumerate(q['options']) if o.get('correct')]} for q in case['questions']],'quiz':[[i for i,o in enumerate(q['options']) if o[1]] for q in case.get('bonusQuiz',[])]} for key,case in cases.items()}
(out/'cases.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
for p in list(public.rglob('*.html'))+list(public.glob('*.js')):
 text=p.read_text()
 if any(token in text for token in ['lisa-chat.js','/api/lisa','api.deepseek.com','api.openai.com','fot-practice-km.c8cpv86h5k.chatgpt.site']):raise SystemExit('Unexpected AI/external-server reference: '+str(p))
print('Independent training edition built:',public)

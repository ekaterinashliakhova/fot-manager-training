#!/usr/bin/env python3
"""Build a dependency-free Sites Worker while preserving all platform pages.

Text assets are embedded; large media stay in the public GitHub repository and
are served through a fixed allowlist proxy. No user-controlled upstream URLs.
"""
import argparse,json,mimetypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
text={};binary=[]
for p in (ROOT/'dist').rglob('*'):
 if not p.is_file():continue
 path='/'+str(p.relative_to(ROOT/'dist'))
 if p.suffix in ['.js','.css','.html','.txt','.svg']:
  text[path]={'body':p.read_text(),'type':{'.js':'text/javascript','.css':'text/css','.html':'text/html','.txt':'text/plain','.svg':'image/svg+xml'}[p.suffix]+'; charset=utf-8'}
 else:binary.append(path)
knowledge=json.loads((ROOT/'agent/knowledge.json').read_text())
math=(ROOT/'dist/lisa-math.js').read_text().replace('export function','function')
server=(ROOT/'agent/worker.js').read_text().replace("import {calculateBrief} from '../dist/lisa-math.js';",'')
body='const TEXT_ASSETS='+json.dumps(text,ensure_ascii=False)+';\nconst BINARY_ASSETS='+json.dumps(binary)+';\nconst KNOWLEDGE='+json.dumps(knowledge,ensure_ascii=False)+';\n'+math+'\n'+server
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(body)
print('Built Sites Worker:',len(body.encode()),'bytes;',len(text),'text files;',len(binary),'media files;',len(knowledge),'knowledge pages')

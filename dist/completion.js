import {currentSegment} from './segments.js?v=20261021-2';
import {feedbackConfirmed,trainingCompleted} from './feedback-state.js?v=20261022-3';
export const SEGMENT_FEEDBACK={
 kksb:{url:'https://polly.events/events/c73f306a-a0e9-4ed8-84f2-3ff39bf158a3',qr:'/assets/feedback/polly-qr.svg'},
 rgs:{url:'https://polly.events/events/50fca92b-dbf7-4b4d-a73f-34cf2b769381',qr:'/assets/feedback/polly-rgs.svg'},
 mmb:{url:'https://polly.events/events/9083d492-4f85-4f1d-a80d-6f921fcb314e',qr:'/assets/feedback/polly-mmb.svg'}
};
export const feedbackFor=(segment=currentSegment().id)=>SEGMENT_FEEDBACK[segment]||SEGMENT_FEEDBACK.kksb;
const API='https://fot-practice-km.c8cpv86h5k.chatgpt.site/api/training/completions';
const QUEUE='fot-completion-pending-v1',ACK='fot-completion-sent-v1';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label=segment=>({kksb:'ККСБ',rgs:'РГС',mmb:'ММБ'})[segment]||'';
let sending=null,onlineBound=false;const memory={},displayed={};
const load=key=>{try{const value=JSON.parse(localStorage.getItem(key)||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{}}catch{return {}}};
const store=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value))}catch{}};
export function completionCounterMarkup(segment){return `<section class="completion-counter" data-completion-counter="${esc(segment)}" aria-label="Количество завершений кейса ${label(segment)}"><span class="completion-counter-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6M4 21h16"/></svg></span><div><span>Завершили кейс ${label(segment)}</span><strong data-completion-count="${esc(segment)}" aria-live="polite">…</strong><small data-completion-status>Уникальных прохождений</small></div></section>`}
export function feedbackMarkup({required=false,attempt,segment=currentSegment().id}={}){
 const feedback=feedbackFor(segment);
 if(feedbackConfirmed(attempt))return '<section class="feedback-receipt" role="status"><span aria-hidden="true">✓</span><div><strong>Спасибо за обратную связь!</strong><p>Вы подтвердили отправку оценки. Обучение завершено.</p></div></section>';
 const opened=!!attempt?.trainingFeedback?.openedAt;
 return `<section class="training-feedback ${required?'is-required':''}"><div class="feedback-copy"><span class="feedback-kicker">${required?'Обязательный финальный шаг':'Ваша обратная связь'}</span><h2><span>Поделитесь</span><em>впечатлениями</em></h2><p>${required?'Все вопросы позади. Чтобы завершить обучение, заполните опрос в Polly, вернитесь сюда и подтвердите отправку оценки.':'Оцените обучение и расскажите, что можно улучшить.'}</p><a class="button feedback-action" href="${feedback.url}" target="_blank" rel="noopener noreferrer">1. Заполнить опрос <span aria-hidden="true">↗</span></a><small>Заполните опрос по ссылке или по QR-коду. Если заполняли с телефона, нажмите кнопку ниже и подтвердите отправку.</small>${required?`<button type="button" class="feedback-qr-open" data-feedback-qr-open>Я заполнил(а) опрос по QR-коду</button><form class="feedback-confirm-form"><label class="feedback-confirm-label"><input type="checkbox" name="feedback-confirm" required ${opened?'':'disabled'}><span>2. Я заполнил(а) опрос и отправил(а) обратную связь</span></label><p class="feedback-confirm-status" role="status">${opened?'После отправки опроса отметьте подтверждение.':'Сначала откройте опрос по кнопке или QR-коду.'}</p><button type="submit" class="button feedback-complete" disabled>Завершить обучение →</button><small>Сайт сохраняет ваше подтверждение. Ответы на опрос собираются в Polly.</small></form>`:''}</div><a class="feedback-qr" href="${feedback.url}" target="_blank" rel="noopener noreferrer" aria-label="Открыть форму оценки обучения в Polly"><img src="${feedback.qr}" width="184" height="184" alt="QR-код: оценить обучение в Polly"><span>Наведите камеру<br>и заполните опрос</span></a></section>`;
}
function paintCount(segment,total){displayed[segment]=Math.max(displayed[segment]||0,total);total=displayed[segment];for(const node of document.querySelectorAll('[data-completion-count]'))if(node.dataset.completionCount===segment){node.textContent=new Intl.NumberFormat('ru-RU').format(total);const status=node.closest('[data-completion-counter]')?.querySelector('[data-completion-status]');if(status)status.textContent='Уникальных прохождений'}}
async function refreshCounts(){try{const response=await fetch(API,{signal:AbortSignal.timeout(15000)});if(!response.ok)throw Error();const data=await response.json();for(const [segment,total] of Object.entries(data.counts||{}))if(Number.isInteger(total)&&total>=0)paintCount(segment,total)}catch{document.querySelectorAll('[data-completion-status]').forEach(el=>el.textContent='Счётчик временно недоступен')}}
async function flush(){
 if(sending)return sending;
 sending=(async()=>{
  const queue={...load(QUEUE),...memory};
  for(const [segment,payload] of Object.entries(queue))try{
   if(!trainingCompleted(payload.attempt)){delete memory[segment];const pending=load(QUEUE);delete pending[segment];store(QUEUE,pending);continue;}
   const response=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(15000)});
   if(!response.ok)continue;const data=await response.json();if(data.segment!==segment||!Number.isInteger(data.total))continue;
   paintCount(segment,data.total);if(memory[segment]?.attempt.id===payload.attempt.id)delete memory[segment];const sent=load(ACK);sent[segment]=payload.attempt.id;store(ACK,sent);const pending=load(QUEUE);if(pending[segment]?.attempt.id===payload.attempt.id){delete pending[segment];store(QUEUE,pending)}
  }catch{}
 })().finally(()=>{sending=null});return sending;
}
export function completionProof(segment,attempt){return {segment,attempt:{id:attempt.id,status:attempt.status,index:attempt.index,version:attempt.version,answers:attempt.answers,quiz:attempt.quiz,trainingFeedback:attempt.trainingFeedback}}}
export function initCompletion(root,{segment,attempt,onFeedbackChange,onFeedbackComplete}={}){
 refreshCounts();
 if(trainingCompleted(attempt)&&load(ACK)[segment]!==attempt.id){const queue=load(QUEUE);queue[segment]=completionProof(segment,attempt);memory[segment]=queue[segment];store(QUEUE,queue)}
 flush();if(!onlineBound){onlineBound=true;window.addEventListener('online',()=>{flush();refreshCounts()})}
 const form=root.querySelector('.feedback-confirm-form');
 if(!form||!attempt)return;
 const check=form.querySelector('input'),button=form.querySelector('button[type="submit"]'),status=form.querySelector('[role="status"]');
 const update=()=>{check.disabled=!attempt.trainingFeedback?.openedAt;button.disabled=check.disabled||!check.checked;status.textContent=check.disabled?'Сначала откройте опрос по кнопке или QR-коду.':check.checked?'Отправка подтверждена вами. Нажмите «Завершить обучение».':'После отправки опроса отметьте подтверждение.';};
 const opened=()=>{attempt.trainingFeedback={version:1,method:'participant-confirmation',openedAt:attempt.trainingFeedback?.openedAt||new Date().toISOString()};onFeedbackChange?.();update();};
 root.querySelectorAll('.feedback-action,.feedback-qr,[data-feedback-qr-open]').forEach(el=>el.addEventListener('click',opened));
 check.addEventListener('change',update);
 form.addEventListener('submit',event=>{event.preventDefault();if(check.disabled||!check.checked||!attempt.trainingFeedback?.openedAt||trainingCompleted(attempt))return;attempt.trainingFeedback.confirmedAt=new Date().toISOString();onFeedbackChange?.();onFeedbackComplete?.();});
 update();
}

// Polly does not send a submission receipt to this static site. Completion is
// based on the participant's explicit confirmation, never on opening a link.
export function feedbackConfirmed(attempt){
 const f=attempt?.trainingFeedback;
 return f?.version===1&&f.method==='participant-confirmation'&&Number.isFinite(Date.parse(f.openedAt))&&Number.isFinite(Date.parse(f.confirmedAt))&&Date.parse(f.confirmedAt)>=Date.parse(f.openedAt);
}
export const trainingCompleted=attempt=>attempt?.status==='done'&&feedbackConfirmed(attempt);
export const awaitingFeedback=attempt=>attempt?.status==='feedback'||attempt?.status==='done'&&!feedbackConfirmed(attempt);

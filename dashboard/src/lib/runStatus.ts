import type { RunGroup } from '../types/orchestrator';

// Single source of truth for "is this run actually done", shared by App.tsx
// (which needs it to decide Active vs. History placement) and RunCard (which
// needs it to decide whether to keep showing "Working..."). Deliberately
// narrow: reaching the graph's last node (security_review) is NOT enough on
// its own - that just means the code side is finished, not that the PR was
// actually merged. Moving a run to History at that point was misleading (it
// looks "done" while still awaiting review/merge). A closed (but not merged)
// PR does NOT count either - that usually means rejected/abandoned, not
// shipped - so it also stays in Active until manually marked done.
//
// Three things count as done:
// - `manually_completed`: a human ended it via the "Mark as done" button.
// - `pr_merged`: the dashboard's own live PR-status check previously found
//   this run's PR merged and persisted that fact (control_server.py's
//   /runs/pr-merged) - checked here from history FIRST, synchronously, so a
//   run already known to be merged doesn't need to wait on a fresh live
//   check (and doesn't re-flash into Active) on every subsequent load.
// - `prStatus === 'merged'`: the live check, for a run that isn't yet known
//   from history - see App.tsx, which persists this as `pr_merged` the
//   first time it's observed so future loads take the fast path above.
export function isRunComplete(run: RunGroup, prStatus?: string): boolean {
	return !!run.nodes.manually_completed || !!run.nodes.pr_merged || prStatus === 'merged';
}

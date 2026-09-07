import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { approve, listApprovals, money, reject } from "./api";

const ACTION_LABEL: Record<string, string> = {
  issue_refund: "Refund",
  issue_replacement: "Replacement",
  escalate: "Escalation",
};

export default function ApprovalQueue() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["approvals"], queryFn: listApprovals });
  const invalidate = () => { qc.invalidateQueries({ queryKey: ["approvals"] }); qc.invalidateQueries({ queryKey: ["runs"] }); qc.invalidateQueries({ queryKey: ["audit"] }); };
  const mApprove = useMutation({ mutationFn: approve, onSuccess: invalidate });
  const mReject = useMutation({ mutationFn: reject, onSuccess: invalidate });
  const busy = mApprove.isPending || mReject.isPending;

  if (isLoading) return <p className="muted">Loading queue…</p>;
  if (error) return <p className="err">Can’t reach the API. Is it running on :8000?</p>;
  if (!data?.length) return <p className="muted">Queue is empty — open the assistant (bottom-right) and request a refund to populate it.</p>;

  return (
    <section>
      <h2 className="panelh">Pending high-risk actions <span className="count">{data.length}</span></h2>
      <p className="muted">Each item was queued by the agent and has <b>not</b> executed. A human decides here.</p>
      <div className="cards">
        {data.map((a) => {
          const isEscalate = a.action === "escalate";
          const showRationale = a.agent_rationale && a.agent_rationale !== a.policy_reason;
          return (
            <article className="card" key={a.approval_id}>
              <div className="row">
                <span className="pill amber">{ACTION_LABEL[a.action] ?? a.action}</span>
                <div className="amt-wrap">
                  <span className="amount">{money(a.amount_cents, a.currency)}</span>
                  <span className="amt-note">{isEscalate ? "under review" : "refund amount"}</span>
                </div>
              </div>
              <h3>{a.item}</h3>
              <dl>
                <div><dt>Order</dt><dd>{a.order_id}</dd></div>
                <div><dt>Customer</dt><dd>{a.customer_name}</dd></div>
                <div><dt>Why</dt><dd>{a.policy_reason} <span className="muted">(policy v{a.policy_version})</span></dd></div>
                {showRationale && <div><dt>Agent note</dt><dd>{a.agent_rationale}</dd></div>}
              </dl>
              <div className="actions">
                <button className="approve" disabled={busy} onClick={() => mApprove.mutate(a.approval_id)}>Approve &amp; execute</button>
                <button className="reject" disabled={busy} onClick={() => mReject.mutate(a.approval_id)}>Reject</button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

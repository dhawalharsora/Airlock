import { useQuery } from "@tanstack/react-query";
import Pipeline from "./Pipeline";
import ApprovalQueue from "./ApprovalQueue";
import Dashboard from "./Dashboard";
import AuditPanel from "./AuditPanel";
import { listRuns, type Outcome } from "./api";

export default function Console() {
  const { data: runs } = useQuery({ queryKey: ["runs"], queryFn: listRuns });
  const last = runs?.[0];
  const d = last?.decision;
  const outcome: Outcome | null =
    d && d !== "info"
      ? ({ final: d === "approve" ? "queued" : d, pill: d, approval_id: null,
           reason: "", customer_message: "",
           order: { order_id: null, item: null, amount_cents: null, currency: "AUD", customer_name: null, status: null },
           policy: { recommendation: d, version: null, reason: "", checks: [], window_days: null, cap_cents: null, age_days: null } } as Outcome)
      : null;
  // seed the pipeline as a completed "last request" (agent gathered → gate coloured)
  const tools = outcome ? ["get_order", "lookup_policy"] : [];

  return (
    <div className="console">
      <div className="pipe-wrap">
        <div className="pipe-title">Last request through the airlock</div>
        <Pipeline tools={tools} outcome={outcome} running={false} />
      </div>
      <div className="consolegrid">
        <div className="col"><ApprovalQueue /></div>
        <div className="col"><Dashboard /><AuditPanel /></div>
      </div>
    </div>
  );
}

import type { Outcome } from "./api";

type Props = { tools: string[]; outcome: Outcome | null; running: boolean };
type St = "idle" | "active" | "done" | "held" | "blocked";

const STAGES = ["Request", "Agent", "Policy gate", "Approval", "Executed"];

function states({ tools, outcome, running }: Props): St[] {
  const started = running || tools.length > 0 || !!outcome;
  const gathered = tools.includes("lookup_policy");
  const f = outcome?.final;
  const ask: St = started ? "done" : "idle";
  const agent: St = gathered ? "done" : started ? "active" : "idle";
  let gate: St = "idle";
  if (f === "refused") gate = "blocked";
  else if (f === "queued") gate = "done";
  else if (f === "escalated") gate = "held";
  else if (gathered || running) gate = "active";
  const queue: St = f === "queued" || f === "escalated" ? "held" : "idle";
  return [ask, agent, gate, queue, "idle"];
}

export default function Pipeline(props: Props) {
  const st = states(props);
  const o = props.outcome;
  const tag =
    o?.final === "queued" ? `queued #${o.approval_id}`
    : o?.final === "escalated" ? `escalated #${o.approval_id}`
    : o?.final === "refused" ? "refused" : props.running ? "working…" : "idle";
  return (
    <div className="pipe" aria-label="airlock pipeline">
      <span className="pipe-cap">LIVE</span>
      {STAGES.map((s, i) => (
        <span className="pseg" key={i}>
          <span className={"pdotc " + st[i] + (props.running && st[i] === "active" ? " pulse" : "")} />
          <span className={"plabelc " + (st[i] !== "idle" ? "on" : "")}>{s}</span>
          {i < STAGES.length - 1 && <span className={"pconn " + (st[i] === "done" ? "on" : "")} />}
        </span>
      ))}
      <span className={"pipe-status " + (o ? o.pill : "")}>{tag}</span>
    </div>
  );
}

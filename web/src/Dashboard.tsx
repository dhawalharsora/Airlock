import { useQuery } from "@tanstack/react-query";
import { listRuns } from "./api";

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ["runs"], queryFn: listRuns });
  if (isLoading) return <p className="muted">Loading runs…</p>;
  if (error) return <p className="err">Can’t reach the API. Is it running on :8000?</p>;
  if (!data?.length) return <p className="muted">No runs yet — send a request from the assistant (bottom-right) to see traces here.</p>;

  const tot = data.reduce((a, r) => ({
    tin: a.tin + r.tokens_in, tout: a.tout + r.tokens_out, cost: a.cost + Number(r.cost_usd),
  }), { tin: 0, tout: 0, cost: 0 });

  return (
    <section>
      <h2 className="panelh">Observability</h2>
      <div className="stats">
        <div className="stat"><span>{data.length}</span><label>runs</label></div>
        <div className="stat"><span>{tot.tin.toLocaleString()}</span><label>tokens in</label></div>
        <div className="stat"><span>{tot.tout.toLocaleString()}</span><label>tokens out</label></div>
        <div className="stat"><span>${tot.cost.toFixed(4)}</span><label>projected cost</label></div>
      </div>
      <p className="costnote">
        Real spend is <b>$0</b> — this demo runs on a local model. “Projected cost” estimates
        what these same tokens would cost in production at Amazon Bedrock (Claude Haiku) rates.
      </p>
      <table>
        <thead><tr><th>Run</th><th>Decision</th><th>Steps (tool sequence)</th><th className="num">tok in/out</th><th className="num">ms</th><th className="num">proj. cost</th></tr></thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.run_id}>
              <td>#{r.run_id}</td>
              <td><span className={"pill " + (r.decision === "approve" ? "green" : r.decision === "refuse" ? "red" : "amber")}>{r.decision}</span></td>
              <td className="steps">{r.steps.filter((s) => s.tool !== "model").map((s) => s.tool).join(" → ") || "—"}</td>
              <td className="num">{r.tokens_in}/{r.tokens_out}</td>
              <td className="num">{r.latency_ms}</td>
              <td className="num">${Number(r.cost_usd).toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

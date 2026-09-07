import { useQuery } from "@tanstack/react-query";
import { listPolicies, money } from "./api";

export default function AdminGovernance() {
  const { data: policies } = useQuery({ queryKey: ["policies"], queryFn: listPolicies });

  return (
    <div className="admin">
      <section>
        <h2 className="panelh">Refund policy <span className="panelhint">versioned · one active</span></h2>
        <p className="muted subtitle">Decisions are made in code against the <b>active</b> version — deterministic and auditable. Changing the active version changes outcomes; every decision records the version it used.</p>
        <div className="polgrid">
          {policies?.map((p) => (
            <article className={"polcard" + (p.active ? " active" : "")} key={p.version}>
              <div className="row">
                <span className="polv">v{p.version}</span>
                {p.active ? <span className="pill green">active</span> : <span className="pill">inactive</span>}
              </div>
              <h3>{p.name}</h3>
              <dl>
                <div><dt>Refund window</dt><dd>{p.refund_window_days} days</dd></div>
                <div><dt>Auto-refund cap</dt><dd>{money(p.max_auto_refund_cents)}</dd></div>
                <div><dt>Above cap</dt><dd>escalates to a human</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className="panelh">Release gate <span className="panelhint">safety is measured, not assumed</span></h2>
        <div className="gategrid">
          <div className="gatecard">
            <div className="gatekpi">15</div><div className="gatelabel">eval cases</div>
            <p>13 of 15 are refuse / escalate — many adversarial (jailbreaks, fake "SYSTEM" prompts, authority injection). Run against the live agent.</p>
          </div>
          <div className="gatecard">
            <div className="gatekpi">PR</div><div className="gatelabel">merge gate</div>
            <p>Deterministic policy + PII-redaction tests block every PR. A change that regresses a safety invariant fails CI — reliably, not on a flaky LLM score.</p>
          </div>
          <div className="gatecard">
            <div className="gatekpi">↻</div><div className="gatelabel">nightly evals</div>
            <p>The full refusal suite runs nightly against the live agent; <code>refusal_accuracy</code> is the headline jailbreak-resistance number.</p>
          </div>
        </div>
        <p className="muted" style={{ marginTop: "12px", fontSize: "12.5px" }}>
          Thresholds: refusal-accuracy ≥ 0.9, task-success ≥ 0.7. Full suite: <code>uv run pytest evals/</code>.
        </p>
      </section>
    </div>
  );
}

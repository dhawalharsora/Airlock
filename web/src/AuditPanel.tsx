import { useQuery } from "@tanstack/react-query";
import { listAudit } from "./api";

function tone(outcome: string | null): string {
  const o = (outcome || "").toLowerCase();
  if (o.includes("executed") || o.includes("pending") || o === "approve") return "green";
  if (o.includes("block") || o.includes("reject") || o === "refuse") return "red";
  if (o.includes("escalat")) return "amber";
  return "";
}

export default function AuditPanel() {
  const { data } = useQuery({ queryKey: ["audit"], queryFn: listAudit });
  return (
    <section className="panel">
      <h2 className="panelh">Audit trail <span className="panelhint">append-only · DB-enforced</span></h2>
      {!data?.length ? (
        <p className="muted">No entries yet — send a request from the bot.</p>
      ) : (
        <ul className="audit">
          {data.map((a) => (
            <li key={a.audit_id}>
              <span className={"apill " + tone(a.outcome)}>{a.outcome}</span>
              <span className="aactor">{a.actor}</span>
              <span className="aaction">{a.action}{a.entity_id ? ` · ${a.entity_id}` : ""}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

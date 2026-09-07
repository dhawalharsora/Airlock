import { useEffect, useState } from "react";
import CustomerPortal from "./CustomerPortal";
import Console from "./Console";
import AdminGovernance from "./AdminGovernance";
import { setApiRole } from "./api";

function personaOf(hash: string) {
  if (hash.includes("operator")) return "operator";
  if (hash.includes("admin")) return "admin";
  return "customer";
}

export default function App() {
  const [route, setRoute] = useState(() => location.hash || "#/customer");
  useEffect(() => {
    const h = () => setRoute(location.hash || "#/customer");
    window.addEventListener("hashchange", h);
    return () => window.removeEventListener("hashchange", h);
  }, []);
  const p = personaOf(route);
  useEffect(() => { setApiRole(p === "customer" ? "customer" : "approver"); }, [p]);
  const go = (to: string) => { location.hash = to; };

  return (
    <div className="app">
      <header>
        <div className="brand">
          <span className="lock">🔒</span>
          <span><span className="name">Airlock</span><span className="sub">control plane for high-risk agents</span></span>
        </div>
        <nav className="personas">
          <button className={p === "customer" ? "on" : ""} onClick={() => go("#/customer")}>Customer portal</button>
          <button className={p === "operator" ? "on" : ""} onClick={() => go("#/operator")}>Operator console</button>
          <button className={p === "admin" ? "on" : ""} onClick={() => go("#/admin")}>Admin</button>
        </nav>
      </header>

      <div className="legend">
        <span className="lstep"><b>1</b> Customer asks</span><span className="larrow">→</span>
        <span className="lstep"><b>2</b> Policy gate</span><span className="larrow">→</span>
        <span className="lstep"><b>3</b> Queued</span><span className="larrow">→</span>
        <span className="lstep"><b>4</b> Human approves</span><span className="larrow">→</span>
        <span className="lstep"><b>5</b> Executes + audited</span>
        <span className="lnote">· the agent never moves money itself</span>
      </div>

      <p className="viewnote">
        {p === "customer" && <>The <b>customer portal</b> — what a passenger sees. Ask the assistant or request a refund; it can only <b>queue</b> an action for a human.</>}
        {p === "operator" && <>The <b>operator console</b> — the ops team approves queued actions and watches every run. The agent can't reach this.</>}
        {p === "admin" && <>The <b>admin</b> surface — the versioned policy that governs decisions and the release gate that keeps the agent safe to ship.</>}
      </p>

      <main>
        {p === "customer" && <CustomerPortal />}
        {p === "operator" && <Console />}
        {p === "admin" && <AdminGovernance />}
      </main>
    </div>
  );
}

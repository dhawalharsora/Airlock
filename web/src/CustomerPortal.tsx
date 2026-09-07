import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listCustomerOrders, listCustomers, money, resetSession, streamAgent,
  type CustomerOrder, type Outcome,
} from "./api";

type BotMsg = { role: "bot"; streaming: boolean; text: string; tools: string[]; error?: boolean };
type Msg = { role: "user"; text: string } | BotMsg;

const newSession = () => (crypto as any).randomUUID?.() ?? "s-" + Math.random().toString(36).slice(2);
const ageDays = (iso: string) => Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86400000));
const pillOf = (o: Outcome) => (o.final === "queued" ? "green" : o.final === "escalated" ? "amber" : "red");
const bannerOf = (o: Outcome) =>
  o.final === "queued" ? `Queued for approval — #${o.approval_id} · not executed`
  : o.final === "escalated" ? `Escalated for human review — #${o.approval_id}`
  : "Refused — no refund issued";

export default function CustomerPortal() {
  const qc = useQueryClient();
  const { data: customers } = useQuery({ queryKey: ["customers"], queryFn: listCustomers });
  const [cid, setCid] = useState("");
  useEffect(() => { if (!cid && customers?.length) setCid(customers[0].customer_id); }, [customers, cid]);
  const { data: orders } = useQuery({ queryKey: ["orders", cid], queryFn: () => listCustomerOrders(cid), enabled: !!cid });

  const [session, setSession] = useState(newSession);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [outcomes, setOutcomes] = useState<Record<string, Outcome>>({});
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [open, setOpen] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);
  const me = customers?.find((c) => c.customer_id === cid);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  function switchCustomer(id: string) { resetSession(session); setCid(id); setSession(newSession()); setMessages([]); setOutcomes({}); }

  const patchBot = (fn: (b: BotMsg) => void) =>
    setMessages((prev) => { const c = [...prev]; const l = c[c.length - 1]; if (l && l.role === "bot") fn(l); return c; });

  async function send(text: string) {
    if (running || !text.trim()) return;
    setInput(""); setOpen(true);
    setMessages((p) => [...p, { role: "user", text }, { role: "bot", streaming: true, text: "", tools: [] }]);
    setRunning(true);
    try {
      await streamAgent(text, cid, session, (e) => {
        if (e.type === "token") patchBot((b) => { b.text += e.text; });
        else if (e.type === "tool") patchBot((b) => { if (!b.tools.includes(e.name)) b.tools.push(e.name); });
        else if (e.type === "done") {
          patchBot((b) => { b.streaming = false; if (!e.is_action) b.text = e.reply || b.text; else b.text = e.outcome.customer_message; });
          if (e.is_action && e.outcome.order.order_id) setOutcomes((o) => ({ ...o, [e.outcome.order.order_id as string]: e.outcome }));
          qc.invalidateQueries({ queryKey: ["approvals"] });
          qc.invalidateQueries({ queryKey: ["runs"] });
          qc.invalidateQueries({ queryKey: ["audit"] });
        }
      });
    } catch { patchBot((b) => { b.streaming = false; b.error = true; }); }
    setRunning(false);
  }

  return (
    <div className={"portal" + (open ? " chat-open" : "")}>
      <div className="portal-main">
        <div className="portal-head">
          <div>
            <h2 className="panelh">Your orders</h2>
            <p className="muted signed">Signed in as <b>{me?.name}</b> · <span className="mono">{cid}</span>
              <select className="who-sel" value={cid} onChange={(e) => switchCustomer(e.target.value)}>
                {customers?.map((c) => <option key={c.customer_id} value={c.customer_id}>{c.name}</option>)}
              </select>
            </p>
          </div>
        </div>

        <div className="pordergrid">
          {orders?.map((o: CustomerOrder) => {
            const oc = outcomes[o.order_id];
            return (
              <article className="pordercard" key={o.order_id}>
                <div className="row">
                  <span className="oc-item">{o.item}</span>
                  <span className="oc-amt">{money(o.amount_cents, o.currency)}</span>
                </div>
                <div className="oc-meta">{o.order_id} · <span className={"status " + o.status}>{o.status}</span> · {ageDays(o.ordered_at)} days ago</div>

                {oc ? (
                  <div className="cardoutcome">
                    <ul className="checks">
                      {oc.policy.checks?.map((c, i) => (
                        <li key={i} className={c.ok ? "ok" : "no"}>
                          <span className="ck">{c.ok ? "✓" : "✗"}</span><span className="cl">{c.label}</span><span className="cd">{c.detail}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="policyline"><span className={"pill " + pillOf(oc)}>{oc.final}</span>{oc.policy.version != null && <span className="muted">policy v{oc.policy.version}</span>}</div>
                    <div className={"banner b-" + pillOf(oc)}>{bannerOf(oc)}</div>
                  </div>
                ) : (
                  <button className="req" disabled={running} onClick={() => send(`I'd like a refund for ${o.order_id}.`)}>Request refund</button>
                )}
              </article>
            );
          })}
        </div>
      </div>

      {open ? (
        <div className="widget">
          <div className="wg-head">
            <div className="wg-title"><span className="wg-ava">🔒</span><span>Southern Cross Assistant<span className="wg-tag">customer-facing bot</span></span></div>
            <button className="wg-x" onClick={() => setOpen(false)}>—</button>
          </div>
          <div className="wg-body">
            {messages.length === 0 && (
              <div className="wg-empty">
                <p>Hi{me ? `, ${me.name.split(" ")[0]}` : ""} 👋 Ask about the refund policy, or request a refund on an order.</p>
                <button className="wg-sugg" disabled={running} onClick={() => send("What is your refund policy?")}>What is your refund policy?</button>
              </div>
            )}
            {messages.map((m, i) =>
              m.role === "user"
                ? <div className="wg-msg me" key={i}>{m.text}</div>
                : <div className="wg-msg bot" key={i}>
                    {m.tools.length > 0 && <div className="toolrun">{m.tools.map((t, j) => <span key={j} className="toolstep">{t}</span>)}{m.streaming && <span className="cursor">▋</span>}</div>}
                    {m.error ? <span className="err">Can’t reach the agent (:8100).</span> : <p className="botext">{m.text || (m.streaming ? "…" : "")}</p>}
                  </div>)}
            <div ref={endRef} />
          </div>
          <div className="wg-composer">
            <input value={input} placeholder="Message the assistant…" disabled={running}
                   onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") send(input); }} />
            <button disabled={running || !input.trim()} onClick={() => send(input)}>➤</button>
          </div>
        </div>
      ) : (
        <button className="launcher" onClick={() => setOpen(true)}>💬</button>
      )}
    </div>
  );
}

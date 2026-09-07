const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type Role = "customer" | "approver";
let currentRole: Role = "customer";
export const setApiRole = (r: Role) => { currentRole = r; };

export type Approval = {
  approval_id: number; order_id: string; action: string; amount_cents: number;
  policy_version: number; policy_reason: string; agent_rationale: string;
  item: string; currency: string; customer_name: string; created_at: string;
};

export type Step = {
  step_no: number; tool: string; tokens_in: number; tokens_out: number;
  latency_ms: number; cost_usd: number;
};
export type Run = {
  run_id: number; prompt: string; decision: string; created_at: string;
  tokens_in: number; tokens_out: number; latency_ms: number; cost_usd: number; steps: Step[];
};

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Airlock-Role": currentRole, ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const listApprovals = () => j<Approval[]>("/api/approvals?state=pending");
export const approve = (id: number) =>
  j("/api/approvals/" + id + "/approve", { method: "POST", body: "{}" });
export const reject = (id: number) =>
  j("/api/approvals/" + id + "/reject", { method: "POST", body: "{}" });
export const listRuns = () => j<Run[]>("/api/runs");

export type AuditRow = {
  audit_id: number; actor: string; action: string; entity_id: string | null;
  outcome: string | null; policy_version: number | null; created_at: string;
};
export const listAudit = () => j<AuditRow[]>("/api/audit");

export type Policy = {
  version: number; name: string; refund_window_days: number;
  max_auto_refund_cents: number; active: boolean;
};
export const listPolicies = () => j<Policy[]>("/api/policies");

export type Customer = { customer_id: string; name: string };
export type CustomerOrder = {
  order_id: string; item: string; amount_cents: number; currency: string;
  status: string; ordered_at: string;
};
export const listCustomers = () => j<Customer[]>("/api/customers");
export const listCustomerOrders = (id: string) =>
  j<CustomerOrder[]>("/api/customers/" + id + "/orders");

export const money = (cents: number, ccy = "AUD") =>
  new Intl.NumberFormat("en-AU", { style: "currency", currency: ccy }).format(cents / 100);

const AGENT_BASE = import.meta.env.VITE_AGENT_URL ?? "http://localhost:8100";


export type Outcome = {
  final: "queued" | "refused" | "escalated";
  pill: "approve" | "refuse" | "escalate";
  approval_id: number | null;
  reason: string;
  customer_message: string;
  order: { order_id: string | null; item: string | null; amount_cents: number | null;
           currency: string; customer_name: string | null; status: string | null };
  policy: {
    recommendation: string | null; version: number | null; reason: string;
    checks: { label: string; detail: string; ok: boolean }[];
    window_days: number | null; cap_cents: number | null; age_days: number | null;
  };
};

export type StreamEvent =
  | { type: "start" }
  | { type: "token"; text: string }
  | { type: "tool"; name: string }
  | { type: "done"; is_action: boolean; outcome: Outcome; reply: string;
      tool_calls: string[]; run_id: number | null;
      tokens_in: number; tokens_out: number; latency_ms: number };

export async function streamAgent(
  message: string, customerId: string, sessionId: string,
  onEvent: (e: StreamEvent) => void,
): Promise<void> {
  const res = await fetch(AGENT_BASE + "/agent/stream", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, customer_id: customerId, session_id: sessionId }),
  });
  if (!res.ok || !res.body) throw new Error(await res.text());
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let nl: number;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (line) onEvent(JSON.parse(line) as StreamEvent);
    }
  }
}

export const resetSession = (sessionId: string) =>
  fetch(AGENT_BASE + "/agent/reset", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: "", session_id: sessionId }),
  });

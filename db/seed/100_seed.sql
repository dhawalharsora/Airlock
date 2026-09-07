-- Synthetic data. Fake customers/orders, real system above this layer.
-- Scenarios are chosen so the high-risk gate is obviously warranted (real airfares,
-- not just trivial ancillaries) and every decision branch is covered.

INSERT INTO customers (customer_id, name, email) VALUES
  ('CUST-01', 'Ava Nguyen', 'ava@example.com'),
  ('CUST-02', 'Liam Patel', 'liam@example.com'),
  ('CUST-03', 'Mia Okafor', 'mia@example.com');

-- amount_cents drives the branch against the active policy (v3: 60-day window, $200 auto-cap).
INSERT INTO orders (order_id, customer_id, item, amount_cents, currency, status, ordered_at) VALUES
  -- Ava — carries the full arc
  ('ORD-1001', 'CUST-01', 'Airfare — Sydney to Melbourne', 42000, 'AUD', 'completed', now() - interval '4 days'),   -- over cap -> escalate
  ('ORD-1002', 'CUST-01', 'Checked baggage fee',            6500,  'AUD', 'completed', now() - interval '3 days'),   -- small, in window -> approve
  ('ORD-1003', 'CUST-01', 'In-flight Wi-Fi',                1500,  'AUD', 'completed', now() - interval '75 days'),  -- outside window -> refuse
  -- Liam
  ('ORD-1004', 'CUST-02', 'Business fare upgrade',          89000, 'AUD', 'completed', now() - interval '6 days'),   -- large -> escalate
  ('ORD-1005', 'CUST-02', 'Seat selection',                 2500,  'AUD', 'refunded',  now() - interval '12 days'),  -- already refunded -> refuse
  -- Mia
  ('ORD-1006', 'CUST-03', 'Lounge day pass',                5500,  'AUD', 'completed', now() - interval '9 days'),   -- small, in window -> approve
  ('ORD-1007', 'CUST-03', 'Priority boarding',              3000,  'AUD', 'cancelled', now() - interval '8 days');   -- cancelled -> refuse

-- Three policy versions. The active one (v3) governs decisions.
INSERT INTO policy_versions (version, name, refund_window_days, max_auto_refund_cents, rules, active) VALUES
  (1, 'Launch policy',   30, 5000,  '{"note":"strict: 30-day window, auto up to $50"}', false),
  (2, 'Relaxed window',  60, 5000,  '{"note":"60-day window, auto cap unchanged at $50"}', false),
  (3, 'Higher auto cap', 60, 20000, '{"note":"60-day window, auto up to $200 before escalation"}', true);

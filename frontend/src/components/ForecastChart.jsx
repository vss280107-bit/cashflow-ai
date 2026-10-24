import { Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { inr, shortDate } from "../api";

/** Balance forecast with an 80% uncertainty band. `compare` optionally overlays a what-if scenario. */
export default function ForecastChart({ daily, threshold, compare }) {
  const data = daily.map((d, i) => ({
    date: d.date,
    base: d.balance_low,
    band: Math.max(0, d.balance_high - d.balance_low),
    expected: d.balance,
    scenario: compare ? compare[i].balance : undefined,
  }));
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e6e8f0" />
        <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={28} tick={{ fontSize: 12 }} />
        <YAxis tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} tick={{ fontSize: 12 }} width={56} />
        <Tooltip
          labelFormatter={shortDate}
          formatter={(v, name) => (name === "band" ? null : [inr(v), name === "base" ? "Worst case (low)" : name === "expected" ? "Expected" : "With planned spend"])}
          itemSorter={() => 0}
        />
        <Legend formatter={(v) => ({ expected: "Expected balance", scenario: "With planned spend", band: "80% range" }[v] || null)} payload={undefined} />
        <Area dataKey="base" stackId="r" stroke="none" fill="transparent" legendType="none" />
        <Area dataKey="band" stackId="r" stroke="none" fill="#6366f1" fillOpacity={0.15} name="band" />
        <ReferenceLine y={threshold} stroke="#ef4444" strokeDasharray="5 4" label={{ value: "Buffer", fill: "#ef4444", fontSize: 12, position: "insideTopLeft" }} />
        <Line dataKey="expected" stroke="#4f46e5" strokeWidth={2.5} dot={false} name="expected" />
        {compare && <Line dataKey="scenario" stroke="#f59e0b" strokeWidth={2.5} dot={false} strokeDasharray="6 3" name="scenario" />}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

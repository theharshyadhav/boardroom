"use client";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { fmtDate } from "@/lib/utils";

export function TimelineChart({ dates, values }: { dates: string[]; values: number[] }) {
  const tail = 45;
  const d = dates.slice(-tail);
  const v = values.slice(-tail);

  // simple linear regression over the last 14 points, extended 10 days as a dashed forecast
  const window = v.slice(-14);
  const xs = window.map((_, i) => i);
  const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;
  const mx = mean(xs), my = mean(window);
  let num = 0, den = 0;
  xs.forEach((x, i) => { num += (x - mx) * (window[i] - my); den += (x - mx) * (x - mx); });
  const slope = den ? num / den : 0;

  const data = d.map((date, i) => ({ date, actual: v[i], forecast: null as number | null }));
  const lastVal = v[v.length - 1];
  data[data.length - 1].forecast = lastVal;
  for (let f = 1; f <= 10; f++) {
    const fdate = new Date(dates[dates.length - 1]);
    fdate.setDate(fdate.getDate() + f);
    data.push({ date: fdate.toISOString().slice(0, 10), actual: null as unknown as number, forecast: lastVal + slope * f });
  }

  return (
    <div style={{ height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="date" tickFormatter={fmtDate} tick={{ fontSize: 10, fill: "rgba(255,255,255,0.32)", fontFamily: "var(--font-mono)" }}
            axisLine={false} tickLine={false} minTickGap={40}
          />
          <YAxis tick={{ fontSize: 10, fill: "rgba(255,255,255,0.32)", fontFamily: "var(--font-mono)" }} axisLine={false} tickLine={false} width={40} />
          <Tooltip
            contentStyle={{ background: "#131318", border: "1px solid rgba(255,255,255,0.14)", borderRadius: 10, fontSize: 12 }}
            labelFormatter={(l) => fmtDate(l as string)}
            labelStyle={{ color: "rgba(255,255,255,0.6)" }}
          />
          <Line type="monotone" dataKey="actual" stroke="#8B5CF6" strokeWidth={2.2} dot={false} connectNulls={false} />
          <Line type="monotone" dataKey="forecast" stroke="#8B5CF6" strokeWidth={1.6} strokeDasharray="4 4" dot={false} opacity={0.6} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/Sidebar";
import { RecommendationCard } from "@/components/RecommendationCard";
import { AskBoardMind } from "@/components/AskBoardMind";
import type { Recommendation } from "@/lib/types";

export default function InsightsPage() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.recommendations().then(setRecs).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="Insights" sub="Recommendations, ranked by confidence and impact" />
      <div className="flex flex-col gap-3.5 mb-4">
        {loading
          ? [0, 1, 2].map((i) => <div key={i} className="skeleton h-[180px] rounded-2xl" />)
          : recs.map((r, i) => <RecommendationCard key={r.id} rec={r} index={i} />)}
      </div>
      <AskBoardMind />
    </div>
  );
}

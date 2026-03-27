"use client";

import { useEffect, useState } from "react";
import { jobApi } from "@/lib/api";
import type { JobStatus } from "@/types";

export function useAnalysisJob(jobId: string | null) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let stopped = false;

    const poll = async () => {
      try {
        const data = await jobApi.status(jobId);
        if (!stopped) {
          setJob(data);
          if (data.status === "completed" || data.status === "failed") {
            return; // 停止轮询
          }
          setTimeout(poll, 5000);
        }
      } catch (err) {
        if (!stopped) setError(err instanceof Error ? err.message : "轮询失败");
      }
    };

    poll();
    return () => {
      stopped = true;
    };
  }, [jobId]);

  return { job, error };
}

import { useCallback, useEffect, useRef, useState } from "react";
import type { Api } from "./api";
import { ACTIVE, type Job, type JobState } from "./types";

/** Polls the project's jobs while any is running and reports each job that finishes while we are watching. */
export function useJobs(api: Api, projectId: string, onFinished: (job: Job) => void, pollMs = 600) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const seen = useRef<Map<string, JobState>>(new Map());
  const first = useRef(true);
  const finished = useRef(onFinished);
  finished.current = onFinished;

  const refresh = useCallback(async () => {
    try {
      const list = await api.listJobs(projectId);
      for (const j of list) {
        const prev = seen.current.get(j.id);
        if (!first.current && prev && ACTIVE.includes(prev) && !ACTIVE.includes(j.state)) finished.current(j);
        if (!first.current && !prev && !ACTIVE.includes(j.state)) finished.current(j); // finished before we saw it start
        seen.current.set(j.id, j.state);
      }
      first.current = false;
      setJobs(list);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the activity list.");
    }
  }, [api, projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const active = jobs.some((j) => ACTIVE.includes(j.state));
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => void refresh(), pollMs);
    return () => clearInterval(t);
  }, [active, refresh, pollMs]);

  const cancel = useCallback(
    async (jobId: string) => {
      try {
        await api.cancelJob(projectId, jobId);
      } finally {
        await refresh();
      }
    },
    [api, projectId, refresh],
  );

  return { jobs, active, error, refresh, cancel };
}

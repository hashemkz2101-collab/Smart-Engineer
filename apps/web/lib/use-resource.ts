"use client";

import { useEffect, useState } from "react";

import { api, toApiError, type ApiError } from "./api";

type State<T> = { key: string; data: T | null; error: ApiError | null };

// Loads a GET resource. Change `version` to reload after a mutation. State is only
// set from the promise callbacks (never synchronously inside the effect). While a
// different path is loading, the previous path's data is not shown.
export function useResource<T>(path: string, version = 0) {
  const [state, setState] = useState<State<T> | null>(null);

  useEffect(() => {
    let active = true;
    api.get<T>(path).then(
      (data) => {
        if (active) setState({ key: path, data, error: null });
      },
      (error: unknown) => {
        if (active) setState({ key: path, data: null, error: toApiError(error) });
      },
    );
    return () => {
      active = false;
    };
  }, [path, version]);

  const current = state && state.key === path ? state : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    loading: current === null,
  };
}

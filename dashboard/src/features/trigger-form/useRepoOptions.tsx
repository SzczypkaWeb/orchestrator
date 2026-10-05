import { useQuery } from "@tanstack/react-query";
import { fetchRepos } from "./api";

export interface RepoOption {
  label: string;
  value: string;
}

// Radix Select reserves the empty string (it means "clear the selection"), so the
// "no explicit repo" choice uses a sentinel that the form maps back to undefined.
export const AUTO_REPO = "auto";

const AUTO_OPTION: RepoOption = { label: "Auto (let Claude decide)", value: AUTO_REPO };


export default function useRepoOptions() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["repos"],
    queryFn: fetchRepos,
  });

  const options: RepoOption[] = [
    AUTO_OPTION,
    ...(data?.repos ?? []).map((r) => ({ label: r, value: r })),
  ];

  return { options, isLoading, isError };
}

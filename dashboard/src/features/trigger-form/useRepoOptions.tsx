import { useQuery } from "@tanstack/react-query";
import { fetchRepos } from "./api";

export interface RepoOption {
  label: string;
  value: string;
}

const AUTO_OPTION: RepoOption = { label: "Auto (let Claude decide)", value: "" };


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

import { redirect } from "next/navigation";

export default function ObservabilityIndex() {
  redirect("/observability/status");
}
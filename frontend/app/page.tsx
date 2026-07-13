import { OperationsDashboard } from "@/components/dashboard/operations-dashboard";
import { dashboardFixture } from "@/lib/dashboard-fixture";

export default function HomePage() {
  return <OperationsDashboard data={dashboardFixture} />;
}

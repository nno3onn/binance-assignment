import { APP_NAME } from "@/lib/project";

export default function HomePage() {
  return (
    <main className="min-h-screen px-6 py-8">
      <h1 className="text-2xl font-semibold">{APP_NAME}</h1>
      <p className="mt-3 max-w-2xl text-sm text-slate-600">
        Frontend scaffold is ready. Operations dashboard implementation starts
        in T15.
      </p>
    </main>
  );
}

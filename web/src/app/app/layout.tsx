import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ReEntry: demo",
  description: "Live Re-entry Capsule for the seeded demo project.",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

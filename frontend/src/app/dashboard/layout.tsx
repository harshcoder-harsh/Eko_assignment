export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen bg-[#030303] text-white overflow-hidden">
      <main className="flex-1 flex flex-col h-full relative z-10">
        {children}
      </main>
    </div>
  );
}

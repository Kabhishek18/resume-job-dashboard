import Link from "next/link"

export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <div className="bg-background flex min-h-svh flex-col items-center justify-center gap-6 p-6">
      <Link href="/" className="text-muted-foreground hover:text-foreground text-sm transition-colors">
        ← Resume Job Dashboard
      </Link>
      {children}
    </div>
  )
}

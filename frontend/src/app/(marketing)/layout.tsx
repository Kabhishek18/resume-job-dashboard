import Link from "next/link"

export default function MarketingLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <div className="bg-background flex min-h-svh flex-col">
      <header className="flex h-14 shrink-0 items-center justify-end gap-2 border-b border-border px-4">
        <Link
          href="/login"
          className="text-muted-foreground hover:text-foreground text-sm font-medium transition-colors"
        >
          Sign in
        </Link>
        <Link
          href="/signup"
          className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex h-9 items-center rounded-md px-4 text-sm font-medium transition-colors"
        >
          Sign up
        </Link>
      </header>
      <main className="flex flex-1 flex-col">{children}</main>
    </div>
  )
}

import { useState } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'

interface ResponsiveLayoutProps {
  children: React.ReactNode
}

export function ResponsiveLayout({ children }: ResponsiveLayoutProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  return (
    <div className="flex h-screen bg-background">
      {/* Desktop Sidebar - hidden on mobile */}
      <aside className="hidden lg:block w-64 border-r bg-card">
        <Sidebar />
      </aside>

      {/* Mobile Sidebar Sheet */}
      <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation</SheetTitle>
          </SheetHeader>
          <Sidebar onNavigate={() => setIsMobileMenuOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header onMenuClick={() => setIsMobileMenuOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  )
}

import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  Database,
  Home,
  Search,
  Settings,
  Users,
  GitBranch,
  History,
  BookMarked,
} from 'lucide-react'

interface SidebarProps {
  onNavigate?: () => void
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Query', href: '/query', icon: Search },
  { name: 'Tables', href: '/tables', icon: Database },
  { name: 'Pipelines', href: '/pipelines', icon: GitBranch },
  { name: 'History', href: '/history', icon: History },
  { name: 'Saved Queries', href: '/saved', icon: BookMarked },
  { name: 'Team', href: '/team', icon: Users },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar({ onNavigate }: SidebarProps) {
  const location = useLocation()

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex h-14 items-center border-b px-4 lg:h-[60px] lg:px-6">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <Database className="h-6 w-6" />
          <span className="">NeuroLake</span>
        </Link>
      </div>
      <div className="flex-1">
        <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={onNavigate}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 transition-all hover:text-primary',
                  isActive
                    ? 'bg-muted text-primary'
                    : 'text-muted-foreground'
                )}
              >
                <Icon className="h-4 w-4" />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>
    </div>
  )
}

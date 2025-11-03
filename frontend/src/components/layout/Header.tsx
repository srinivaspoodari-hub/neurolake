import { useState } from 'react'
import { Bell, Menu, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/store/authStore'
import { useNavigate } from 'react-router-dom'
import { ThemeToggle } from '@/components/theme/ThemeToggle'

interface HeaderProps {
  onMenuClick?: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [notifications] = useState(3) // Mock notification count

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-4 lg:h-[60px] lg:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onMenuClick}
      >
        <Menu className="h-5 w-5" />
        <span className="sr-only">Toggle navigation menu</span>
      </Button>

      <div className="w-full flex-1">
        <h1 className="text-lg font-semibold md:text-2xl">
          Welcome back, {user?.name || 'User'}
        </h1>
      </div>

      <ThemeToggle />

      <Button variant="ghost" size="icon" className="relative">
        <Bell className="h-5 w-5" />
        {notifications > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-xs text-destructive-foreground">
            {notifications}
          </span>
        )}
        <span className="sr-only">Notifications</span>
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="rounded-full">
            <User className="h-5 w-5" />
            <span className="sr-only">User menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>My Account</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate('/settings')}>
            Settings
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate('/settings/api-keys')}>
            API Keys
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleLogout}>Logout</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}

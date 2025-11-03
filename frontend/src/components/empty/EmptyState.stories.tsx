import type { Meta, StoryObj } from '@storybook/react'
import { EmptyState } from './EmptyState'
import { Database, Search, Users, Bell, GitBranch } from 'lucide-react'

const meta = {
  title: 'Components/EmptyState',
  component: EmptyState,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof EmptyState>

export default meta
type Story = StoryObj<typeof meta>

export const NoTables: Story = {
  args: {
    icon: Database,
    title: 'No tables found',
    description: 'Get started by creating your first table or importing data from an external source.',
    action: {
      label: 'Create Table',
      onClick: () => alert('Create table clicked'),
    },
  },
}

export const NoQueries: Story = {
  args: {
    icon: Search,
    title: 'No saved queries',
    description: 'Save your frequently used queries for quick access later.',
    action: {
      label: 'Go to Query Editor',
      onClick: () => alert('Navigate to query editor'),
    },
  },
}

export const NoTeamMembers: Story = {
  args: {
    icon: Users,
    title: 'No team members yet',
    description: 'Collaborate with your team by inviting members.',
    action: {
      label: 'Invite Team Member',
      onClick: () => alert('Invite clicked'),
    },
  },
}

export const NoNotifications: Story = {
  args: {
    icon: Bell,
    title: 'No notifications',
    description: "You're all caught up! Notifications will appear here.",
  },
}

export const NoPipelines: Story = {
  args: {
    icon: GitBranch,
    title: 'No pipelines configured',
    description: 'Create data pipelines to automate your workflows.',
    action: {
      label: 'Create Pipeline',
      onClick: () => alert('Create pipeline clicked'),
    },
  },
}

export const WithoutAction: Story = {
  args: {
    icon: Database,
    title: 'No data available',
    description: 'There is no data to display at the moment.',
  },
}

export const Multiple: Story = {
  render: () => (
    <div className="grid gap-4 md:grid-cols-2">
      <EmptyState
        icon={Database}
        title="No tables"
        description="Create your first table."
        action={{
          label: 'Create',
          onClick: () => {},
        }}
      />
      <EmptyState
        icon={Search}
        title="No queries"
        description="Start by running a query."
      />
    </div>
  ),
}

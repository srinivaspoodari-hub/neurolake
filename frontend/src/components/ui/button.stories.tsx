import type { Meta, StoryObj } from '@storybook/react'
import { Button } from './button'
import { Download, Mail, Plus, Trash } from 'lucide-react'

const meta = {
  title: 'UI/Button',
  component: Button,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'],
    },
    size: {
      control: 'select',
      options: ['default', 'sm', 'lg', 'icon'],
    },
  },
} satisfies Meta<typeof Button>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    children: 'Button',
    variant: 'default',
  },
}

export const Destructive: Story = {
  args: {
    children: 'Delete',
    variant: 'destructive',
  },
}

export const Outline: Story = {
  args: {
    children: 'Outline',
    variant: 'outline',
  },
}

export const Secondary: Story = {
  args: {
    children: 'Secondary',
    variant: 'secondary',
  },
}

export const Ghost: Story = {
  args: {
    children: 'Ghost',
    variant: 'ghost',
  },
}

export const Link: Story = {
  args: {
    children: 'Link',
    variant: 'link',
  },
}

export const Small: Story = {
  args: {
    children: 'Small',
    size: 'sm',
  },
}

export const Large: Story = {
  args: {
    children: 'Large',
    size: 'lg',
  },
}

export const WithIcon: Story = {
  args: {
    children: (
      <>
        <Mail className="mr-2 h-4 w-4" />
        Login with Email
      </>
    ),
  },
}

export const IconOnly: Story = {
  args: {
    children: <Download className="h-4 w-4" />,
    size: 'icon',
    variant: 'outline',
  },
}

export const Disabled: Story = {
  args: {
    children: 'Disabled',
    disabled: true,
  },
}

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        <Button variant="default">Default</Button>
        <Button variant="destructive">Destructive</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="link">Link</Button>
      </div>
      <div className="flex gap-2">
        <Button size="sm">Small</Button>
        <Button size="default">Default</Button>
        <Button size="lg">Large</Button>
        <Button size="icon">
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex gap-2">
        <Button>
          <Download className="mr-2 h-4 w-4" />
          With Icon
        </Button>
        <Button variant="destructive">
          <Trash className="mr-2 h-4 w-4" />
          Delete
        </Button>
      </div>
    </div>
  ),
}

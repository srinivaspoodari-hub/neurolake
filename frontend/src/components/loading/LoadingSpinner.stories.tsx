import type { Meta, StoryObj } from '@storybook/react'
import { LoadingSpinner, FullPageSpinner } from './LoadingSpinner'

const meta = {
  title: 'Components/LoadingSpinner',
  component: LoadingSpinner,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
    },
  },
} satisfies Meta<typeof LoadingSpinner>

export default meta
type Story = StoryObj<typeof meta>

export const Small: Story = {
  args: {
    size: 'sm',
  },
}

export const Medium: Story = {
  args: {
    size: 'md',
  },
}

export const Large: Story = {
  args: {
    size: 'lg',
  },
}

export const WithText: Story = {
  args: {
    size: 'md',
    text: 'Loading...',
  },
}

export const FullPage: Story = {
  render: () => <FullPageSpinner />,
  parameters: {
    layout: 'fullscreen',
  },
}

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-center gap-8">
      <LoadingSpinner size="sm" text="Small" />
      <LoadingSpinner size="md" text="Medium" />
      <LoadingSpinner size="lg" text="Large" />
    </div>
  ),
}

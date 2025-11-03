// Animation utilities for consistent transitions across the app

export const transitions = {
  fast: 'transition-all duration-150 ease-in-out',
  normal: 'transition-all duration-300 ease-in-out',
  slow: 'transition-all duration-500 ease-in-out',
}

export const animations = {
  fadeIn: 'animate-in fade-in duration-300',
  fadeOut: 'animate-out fade-out duration-300',
  slideInFromTop: 'animate-in slide-in-from-top duration-300',
  slideInFromBottom: 'animate-in slide-in-from-bottom duration-300',
  slideInFromLeft: 'animate-in slide-in-from-left duration-300',
  slideInFromRight: 'animate-in slide-in-from-right duration-300',
  scaleIn: 'animate-in zoom-in duration-300',
  scaleOut: 'animate-out zoom-out duration-300',
}

export const hover = {
  scale: 'hover:scale-105 active:scale-95',
  lift: 'hover:-translate-y-1 hover:shadow-lg',
  glow: 'hover:shadow-glow',
  brightness: 'hover:brightness-110',
}

export const focus = {
  ring: 'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  visible: 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
}

export const interactive = {
  button: `${transitions.fast} ${hover.scale} ${focus.ring}`,
  card: `${transitions.normal} ${hover.lift}`,
  link: `${transitions.fast} hover:text-primary ${focus.visible}`,
}

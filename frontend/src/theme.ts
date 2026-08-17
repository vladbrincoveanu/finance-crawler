import { extendTheme } from '@chakra-ui/react';

const theme = extendTheme({
  fonts: {
    heading: '"IBM Plex Sans", "Avenir Next", sans-serif',
    body: '"IBM Plex Sans", "Avenir Next", sans-serif',
  },
  colors: {
    ink: {
      950: '#070b14',
      900: '#0b1220',
      800: '#111b2d',
    },
    amber: {
      200: '#fbd38d',
      300: '#f6ad55',
    },
  },
  styles: {
    global: {
      'html, body, #root': { minHeight: '100%' },
      body: {
        background: '#070b14',
        color: '#edf2f7',
        fontFeatureSettings: '"ss01" 1, "cv11" 1',
      },
      '*:focus-visible': {
        outline: '2px solid #f6ad55',
        outlineOffset: '3px',
      },
      '::selection': { background: '#8b5cf6', color: '#fff' },
    },
  },
});

export default theme;

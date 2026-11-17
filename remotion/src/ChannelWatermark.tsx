import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';

export const ChannelWatermark: React.FC<{text?: string}> = ({text}) => {
  const {width, height} = useVideoConfig();
  const name = text?.trim();
  if (!name) return null;
  const fontSize = Math.min(Math.min(width, height) * 0.055, width * 0.82 / Math.max(1, Array.from(name).length));
  return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', pointerEvents: 'none', zIndex: 1000}}>
    <div data-channel-watermark style={{opacity: 0.18, color: '#fff', fontFamily: 'Arial, sans-serif',
      fontWeight: 700, fontSize, lineHeight: 1.3, whiteSpace: 'nowrap', maxWidth: '88%', overflow: 'hidden',
      textAlign: 'center', textShadow: '0 1px 4px #000, 0 0 2px #000', WebkitTextStroke: '0.5px #333'}}>{name}</div>
  </AbsoluteFill>;
};

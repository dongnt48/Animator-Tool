import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CozyStorytellingProps} from './CozyStorytellingVideo';
import {poseAt, storyAt} from './storyMotion';

const INK = '#34364C';
const CORAL = '#E07A5F';
const SAGE = '#81B29A';

type ActorProps = {x: number; y?: number; frame: number; walk?: boolean; gesture?: string; progress?: number;
  crouch?: number; mood?: string; speaking?: boolean; color?: string; flip?: boolean; scale?: number; character?: string};

function Actor({x, y = 300, frame, walk = false, gesture = 'idle', progress = 1,
  crouch = 0, mood = 'reflecting', speaking = false, color = CORAL, flip = false, scale = 1,
  character = 'stickman'}: ActorProps) {
  const pose = poseAt(frame, walk, gesture, progress, crouch);
  const headTilt = gesture === 'think' ? -8 * progress : gesture === 'nod' ? Math.sin(frame * .24) * 9 * progress
    : gesture === 'shake_head' ? Math.sin(frame * .25) * 12 * progress : mood === 'sad' ? 8 : 0;
  const headY = crouch * 36 - (walk ? Math.abs(Math.cos(frame * .27)) * 7 : 0);
  const arm = (hand: [number, number], side: number) => `M ${side * 20} ${8 + headY} Q ${side * 46} ${(40 + hand[1]) / 2 + headY} ${hand[0]} ${hand[1] + headY}`;
  const leg = (foot: [number, number], side: number) => `M 0 ${pose.hipY} Q ${side * 24 + foot[0] * .4} ${150 + crouch * 20} ${foot[0]} ${foot[1]}`;
  return <g transform={`translate(${x} ${y}) scale(${flip ? -scale : scale} ${scale})`}>
    <ellipse cx="0" cy="207" rx="65" ry="9" fill={INK} opacity=".09" />
    <g fill="none" stroke={INK} strokeWidth="8" strokeLinecap="round" strokeLinejoin="round">
      <path d={leg(pose.leftFoot, -1)} /><path d={leg(pose.rightFoot, 1)} />
      <path d={arm(pose.leftHand, -1)} /><path d={arm(pose.rightHand, 1)} />
      <path d={`M -20 ${5 + headY} Q 0 ${-2 + headY} 20 ${5 + headY} L 25 ${pose.hipY} L -25 ${pose.hipY} Z`} fill={color} />
      <path d={`M ${pose.leftFoot[0] + 3} ${pose.leftFoot[1]} l -24 0 M ${pose.rightFoot[0] - 3} ${pose.rightFoot[1]} l 25 0`} />
    </g>
    <g transform={`translate(0 ${headY}) rotate(${headTilt} 0 -65)`}>
      {character === 'cat' && <path d="M-41-88 -40-130 -12-108 M12-108 40-130 41-88" fill="#FAE4CE" stroke={INK} strokeWidth="6" />}
      {character === 'bear' && <g fill="#D6B18A" stroke={INK} strokeWidth="6"><circle cx="-37" cy="-104" r="18" /><circle cx="37" cy="-104" r="18" /></g>}
      {character === 'hoodie' && <ellipse cx="0" cy="-63" rx="54" ry="58" fill={color} stroke={INK} strokeWidth="6" />}
      {character === 'bot' ? <rect x="-45" y="-110" width="90" height="90" rx="18" fill="#FDFBF5" stroke={INK} strokeWidth="7" />
        : <circle cy="-65" r="45" fill={character === 'bear' ? '#E9C8A4' : '#FDFBF5'} stroke={INK} strokeWidth="7" />}
      {character === 'bot' && <path d="M0-110v-20m-8 0h16" stroke={INK} strokeWidth="6" />}
      <path d="M-22-111q22-22 43 1" fill="none" stroke={INK} strokeWidth="7" strokeLinecap="round" />
      {frame % 100 > 95 ? <path d="M-23-67h13m20 0h13" stroke={INK} strokeWidth="6" />
        : <g fill={INK}><circle cx="-16" cy="-67" r="5" /><circle cx="16" cy="-67" r="5" /></g>}
      {mood === 'sad' || mood === 'regret' ? <><path d="M-25-81l15-7m20 0 15 7M-12-40q12-12 24 0" fill="none" stroke={INK} strokeWidth="4" /><path d="M29-53q-12 17 0 19q12-2 0-19" fill="#A5C8D6" /></>
        : speaking ? <ellipse cy="-42" rx="8" ry={4 + Math.abs(Math.sin(frame * .7)) * 7} fill={INK} />
        : <path d={mood === 'peace' || mood === 'proud' || mood === 'loyal' ? 'M-14-45q14 17 28 0' : 'M-10-40h20'} stroke={INK} strokeWidth="4" fill="none" strokeLinecap="round" />}
      {character === 'ghost' && <path d="M-40-30q-15 20-15 39l20-8 17 9 18-10 18 10 17-9 20 8q0-19-15-39" fill="#FDFBF5" stroke={INK} strokeWidth="5" />}
    </g>
  </g>;
}

const heartPath = 'M0 18C-70-24-68-78-30-78C-12-78 0-62 0-62C0-62 12-78 30-78C68-78 70-24 0 18Z';

export const DialogueStoryVideo: React.FC<CozyStorytellingProps> = props => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const scenes = props.scenes || [];
  if (!scenes.length) return <AbsoluteFill style={{background: '#FAF6EE'}} />;
  const state = storyAt(scenes, frame);
  const {scene, visual, action, phase, elapsed, speaking, visibleText} = state;
  const tall = height > width * 1.2;
  const dark = props.style === 'midnight';
  const accent = dark ? '#F4A261' : CORAL;
  const exit = visual === 'parting' ? phase : 0;
  const lifted = visual === 'support' ? phase : 0;
  const released = visual === 'burden' && action === 'release' ? phase : 0;
  const growing = visual === 'growth' ? phase : 0;
  const journeyX = visual === 'journey' ? phase * 180 : 0;
  const gesture = visual === 'burden' && released < .4 ? 'burden'
    : visual === 'support' ? 'reach' : visual === 'growth' ? 'water'
    : visual === 'crossroads' ? 'point' : action === 'rise' ? 'celebrate' : action;
  const actorMood = scene.characterState;
  const bg = dark ? '#202336' : '#FAF6EE';
  const text = dark ? '#FAF6EE' : INK;
  const figureProps = {frame: elapsed, mood: actorMood, speaking, color: accent, character: props.character};
  return <AbsoluteFill style={{background: bg, color: text, fontFamily: 'Arial, sans-serif', overflow: 'hidden'}}>
    {props.audioSrc && <Audio src={staticFile(props.audioSrc)} />}
    <div style={{position: 'absolute', inset: 0, opacity: .25, backgroundImage: `radial-gradient(${dark ? '#515569' : '#D9CFB8'} 1.5px, transparent 1.5px)`, backgroundSize: '32px 32px'}} />
    <div style={{position: 'absolute', top: tall ? '7%' : '5%', width: '100%', textAlign: 'center', padding: '0 7%', boxSizing: 'border-box'}}>
      <span style={{fontSize: tall ? width * .032 : height * .032, fontWeight: 800, letterSpacing: 2, color: dark ? '#EBCDB0' : '#82715D'}}>{props.channelTag || 'MỖI CÂU NÓI · MỘT CÂU CHUYỆN'}</span>
      <h1 style={{fontSize: Math.min(width * .052, height * .064), margin: '22px 0', lineHeight: 1.2, fontWeight: 900}}>{scene.badge}</h1>
    </div>
    <svg viewBox="0 0 1000 650" style={{position: 'absolute', top: tall ? '19%' : '16%', left: tall ? '0' : '12%', width: tall ? '100%' : '76%', height: tall ? '52%' : '65%', overflow: 'visible'}}>
      {dark && <rect x="40" y="70" width="920" height="540" rx="45" fill="#F6F2E7" />}
      <ellipse cx="500" cy="513" rx="440" ry="37" fill={dark ? '#F9EEE0' : '#D6C8AD'} opacity={dark ? .88 : .35} />
      <path d="M80 513h840" stroke="#C7B99E" strokeWidth="3" />
      {visual === 'parting' && <>
        <path d={`M450 294Q500 ${260 + exit * 45} ${550 + exit * 175} 294`} stroke={accent} strokeWidth="7" strokeDasharray={exit > .25 ? '9 14' : undefined} fill="none" opacity={1 - exit * .8} />
        <g transform={`translate(500 170) scale(${.7 - exit * .15})`} opacity={1 - exit * .7}>
          <path d={heartPath} fill={accent} /><path d="M0-73 -10-45 9-25 -5 0" stroke={bg} strokeWidth="8" fill="none" />
        </g>
        <Actor {...figureProps} x={355 - exit * 35} gesture={action === 'embrace' ? 'embrace' : 'reach'} progress={1 - exit * .7} scale={1.1} />
        <Actor {...figureProps} speaking={false} x={610 + exit * 175} flip={exit < .25} walk={phase > .05 && phase < .98} gesture="idle" color={SAGE} scale={1.1} />
        <path d="m790 475 55 0m-18-13 18 13-18 13" stroke={SAGE} strokeWidth="5" fill="none" opacity={exit} />
      </>}
      {visual === 'support' && <>
        <path d="M120 500q120-80 220-20m340 0q100-60 180 15" fill="none" stroke={SAGE} strokeWidth="8" opacity=".4" />
        <Actor {...figureProps} x={350 + lifted * 35} gesture="reach" progress={phase} scale={1.1} />
        <Actor {...figureProps} speaking={false} x={650 - lifted * 95} y={300} flip crouch={1 - lifted} gesture="reach" progress={phase} mood={lifted < .6 ? 'sad' : 'proud'} color={SAGE} scale={1.1} />
        <path d={`M${405 + lifted * 35} ${390 - lifted * 45} Q470 ${340 - lifted * 30} ${580 - lifted * 70} ${430 - lifted * 85}`} stroke={accent} strokeWidth="6" fill="none" opacity={phase} />
        <g transform="translate(510 160) scale(.5)" opacity={phase}><path d={heartPath} fill={accent} /></g>
      </>}
      {visual === 'burden' && <>
        <Actor {...figureProps} x={490} gesture={released > .5 ? 'celebrate' : 'burden'} progress={released > .5 ? (released - .5) * 2 : 1} crouch={(1 - released) * .5} scale={1.1} mood={released > .8 ? 'peace' : 'sad'} />
        <g transform={`translate(${490 + released * 230} ${140 + released * 335}) rotate(${released * 75})`} opacity={1 - released * .25}>
          <path d="M-98-46 -64-95 25-105 95-52 90 18 30 46-70 33Z" fill="#9B9AA3" stroke={INK} strokeWidth="7" />
          <path d="m-48-62 25 20-17 32m65-58-5 27 30 15" fill="none" stroke={INK} strokeWidth="4" opacity=".35" />
        </g>
        {released > .4 && <path d="m650 476 30-32m25 53 32-7m-57 15 5-27" stroke={accent} strokeWidth="6" opacity={Math.sin(released * Math.PI)} />}
      </>}
      {visual === 'crossroads' && <>
        <path d="M480 540Q490 400 285 220M520 540Q510 400 745 220" fill="none" stroke="#DFCEB0" strokeWidth="70" />
        <path d="M500 535Q490 400 285 220M500 535Q510 400 745 220" fill="none" stroke="#FFFDF9" strokeWidth="4" strokeDasharray="14 18" />
        <path d="M500 130v130m-85-100h170l30 25-30 25H415l-30-25Z" fill={SAGE} stroke={INK} strokeWidth="5" />
        <Actor {...figureProps} x={450 + phase * 120} y={310 - phase * 60} walk={phase > .1 && phase < .95} gesture="point" progress={phase} scale={1.05 - phase * .15} />
      </>}
      {visual === 'growth' && <>
        <Actor {...figureProps} x={325} gesture="water" progress={phase} scale={1.1} />
        <g transform="translate(650 500)">
          <path d="M-75-40H75L50 65H-50Z" fill="#DAAD86" stroke={INK} strokeWidth="6" />
          <path d={`M0-38Q${10 + growing * 15} ${-60 - growing * 100} 0 ${-85 - growing * 140}`} stroke={SAGE} strokeWidth="12" fill="none" />
          <g transform={`translate(0 ${-80 - growing * 120}) scale(${.2 + growing * .8})`} fill={SAGE} stroke={INK} strokeWidth="3"><path d="M0 0Q-90-80-95-20Q-70 15 0 0M0-15Q95-110 98-45Q85-10 0-15" /></g>
        </g>
        <g transform={`translate(450 350) rotate(${phase * 20})`}><path d="M0 0h75v55H0Z M75 8l45-20-10 22-35 25" fill="#ABCAD1" stroke={INK} strokeWidth="5" /><path d="M0 8q-35-20-28 15q7 20 28 12" fill="none" stroke={INK} strokeWidth="5" /></g>
        {[0, 1, 2, 3].map(i => <circle key={i} cx={580 + i * 17} cy={365 + ((frame * 4 + i * 23) % 105)} r="4" fill="#88B5C8" opacity={phase} />)}
      </>}
      {visual === 'journey' && <>
        <path d="M100 550Q390 425 950 485" fill="none" stroke="#DBC8A6" strokeWidth="80" />
        <path d="M100 550Q390 425 950 485" fill="none" stroke="#FFFDF9" strokeWidth="5" strokeDasharray="25 30" />
        <path d="M120 440V265m-60 0h130l20 25-20 25H60Z" fill={SAGE} stroke={INK} strokeWidth="5" />
        <Actor {...figureProps} x={370 + journeyX} y={285} walk={phase > 0} gesture="idle" scale={1.15} />
        <circle cx="800" cy="150" r="45" fill="#F1D28C" /><path d="m800 77 0-20m73 93h20m-145 0h-20" stroke="#F1D28C" strokeWidth="6" />
      </>}
      {visual === 'conversation' && <>
        <Actor {...figureProps} x={325} gesture={action === 'heart' ? 'heart' : 'reach'} progress={.5 + Math.sin(frame * .09) * .15} scale={1.1} />
        <Actor {...figureProps} speaking={false} x={680} flip color={SAGE} gesture="think" progress={.5} scale={1.1} />
        <path d="M390 110h230q20 0 20 20v65q0 20-20 20H480l-40 30 6-30h-56q-20 0-20-20v-65q0-20 20-20" fill="#FFFFFF" stroke={INK} strokeWidth="5" />
        {[460, 500, 540].map((x, i) => <circle key={x} cx={x} cy={164 - Math.sin(frame * .14 + i) * (speaking ? 7 : 0)} r="9" fill={accent} />)}
      </>}
      {visual === 'reflection' && <>
        <rect x="600" y="140" width="190" height="330" rx="90" fill="#DDE9E8" stroke="#BCA78A" strokeWidth="14" />
        <g opacity=".38"><Actor {...figureProps} speaking={false} x={695} y={280} scale={.55} gesture="think" progress={phase} color={SAGE} /></g>
        <Actor {...figureProps} x={350} gesture="think" progress={Math.max(.4, phase)} scale={1.15} />
        <path d="M370 125q50-85 110-25q60 45-15 75l-40-3-30 25 4-35q-45-5-29-37" fill="#FFFFFF" stroke={INK} strokeWidth="4" />
        <text x="424" y="145" fontSize="58" fill={accent} textAnchor="middle">?</text>
      </>}
      {visual === 'celebration' && <>
        <path d="M310 515v-65h140v-65h150v130Z" fill="#D8C8A5" stroke={INK} strokeWidth="5" />
        <Actor {...figureProps} x={500} y={250 - phase * 65} crouch={(1 - phase) * .6} gesture="celebrate" progress={phase} mood="proud" scale={1.1} />
        {Array.from({length: 18}, (_, i) => <rect key={i} x={150 + i * 40} y={100 + ((elapsed * 3 + i * 33) % 240)} width="8" height="18" rx="2" transform={`rotate(${i * 23} ${150 + i * 40} ${100 + ((elapsed * 3 + i * 33) % 240)})`} fill={[accent, SAGE, '#EBC96B'][i % 3]} opacity={phase} />)}
      </>}
      {visual === 'peace' && <>
        <path d="M80 490Q300 310 500 490Q730 290 920 490" fill="#E3E9D5" />
        <circle cx="745" cy="180" r="72" fill="#F3D58B" />
        <path d="M200 480V300m0 80q-100-90-60-110q50-30 60 110m0-15q120-100 80-130q-50-30-80 130" fill={SAGE} stroke={SAGE} strokeWidth="7" />
        <Actor {...figureProps} x={500} y={300 + Math.sin(frame * .05) * 3} gesture="heart" progress={1} mood="peace" scale={1.1} />
        <circle cx="500" cy="325" r={160 + Math.sin(frame * .045) * 15} fill="none" stroke={SAGE} opacity=".3" strokeWidth="4" />
      </>}
      {action === 'heart' && visual !== 'parting' && <g transform={`translate(500 150) scale(${phase * .6})`}><path d={heartPath} fill={accent} /></g>}
    </svg>
    <div style={{position: 'absolute', left: '7%', right: '7%', bottom: tall ? '12%' : '4%', textAlign: 'center'}}>
      <div style={{minHeight: tall ? 150 : 65, fontSize: Math.min(width * .049, height * .052), fontWeight: 800, lineHeight: 1.55, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignContent: 'center', gap: '0 .24em'}}>
        {visibleText && scene.leadWords.map((word, i) => <span key={i} style={{color: frame >= word.start && frame < word.end ? accent : frame < word.start ? dark ? '#777D90' : '#B0ABA1' : text}}>{word.text}</span>)}
      </div>
      {visibleText && frame >= scene.keyPhrase.start && <div style={{display: 'inline-block', maxWidth: '100%', boxSizing: 'border-box', padding: '16px 28px', borderRadius: 16, color: dark ? '#202336' : '#FFFFFF', background: accent, fontSize: Math.min(width * .04, height * .042, width * .84 / Math.max(1, scene.keyPhrase.text.length * .62)), fontWeight: 900, overflowWrap: 'anywhere'}}>{scene.keyPhrase.text}</div>}
    </div>
  </AbsoluteFill>;
};

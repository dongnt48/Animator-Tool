import type {SceneData} from './CozyStorytellingVideo';

export const clamp = (value: number) => Math.max(0, Math.min(1, value));
export const ease = (value: number) => { const p = clamp(value); return p * p * (3 - 2 * p); };

export function storyAt(scenes: SceneData[], frame: number) {
  let index = 0;
  scenes.forEach((scene, i) => { if (scene.startFrame <= frame) index = i; });
  const scene = scenes[index];
  let from = index;
  while (from > 0 && scenes[from - 1].visual === scene.visual) from--;
  let to = index;
  while (to + 1 < scenes.length && scenes[to + 1].visual === scene.visual) to++;
  const primary: Record<string, string[]> = {
    parting: ['turn_away', 'walk', 'release'], support: ['reach', 'rise', 'embrace'],
    burden: ['release'], crossroads: ['choose', 'point', 'walk'], growth: ['water'],
    journey: ['walk'], conversation: ['heart', 'embrace', 'reach'], reflection: ['think'],
    celebration: ['celebrate', 'rise'], peace: ['breathe'],
  };
  const shot = scenes.slice(from, to + 1);
  // A nod in the next subtitle must not put the released rock back on the actor.
  // Wait for the shot's meaningful cue, then retain its state for the whole shot.
  const candidate = shot.find(s => primary[scene.visual || 'reflection']?.includes(s.action || 'idle'))
    || shot.find(s => s.action && s.action !== 'idle');
  const event = candidate && (candidate.actionStart ?? candidate.startFrame) <= frame ? candidate : undefined;
  const cue = event?.actionStart ?? event?.startFrame ?? scene.startFrame;
  const duration = Math.max(8, Math.min(30, scenes[to].endFrame - cue));
  return {scene, visual: scene.visual || 'reflection', action: event?.action || 'idle',
    phase: event ? ease((frame - cue) / duration) : 0,
    elapsed: event ? Math.max(0, frame - cue) : 0,
    shotFrame: Math.max(0, frame - scenes[from].startFrame),
    speaking: frame >= scene.startFrame && frame < scene.endFrame && scene.leadWords.some(w => frame >= w.start && frame < w.end),
    visibleText: frame >= scene.startFrame && frame < scene.endFrame};
}

export function poseAt(frame: number, walk: boolean, gesture: string, progress: number, crouch = 0) {
  const stride = walk ? Math.sin(frame * .27) : 0;
  const lift = walk ? Math.abs(Math.cos(frame * .27)) * 7 : 0;
  const arms: Record<string, [number, number, number, number]> = {
    reach: [36, 48, 88, 34], point: [30, 18, 98, 0],
    heart: [-8, 42, 8, 42], celebrate: [-68, -30, 68, -30],
    think: [-35, 78, 30, -25], embrace: [20, 35, 80, 35],
    water: [-34, 64, 82, 42], burden: [-62, -125, 62, -125],
  };
  const target = arms[gesture] || [-40, 85, 40, 85];
  const p = clamp(progress);
  return {
    hipY: 100 + crouch * 38 - lift,
    leftHand: [-40 + (target[0] + 40) * p - stride * 23, 85 + (target[1] - 85) * p] as [number, number],
    rightHand: [40 + (target[2] - 40) * p + stride * 23, 85 + (target[3] - 85) * p] as [number, number],
    leftFoot: [-27 - stride * 35, 200 - Math.max(0, stride) * 18] as [number, number],
    rightFoot: [27 + stride * 35, 200 + Math.min(0, stride) * 18] as [number, number],
  };
}

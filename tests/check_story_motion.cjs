const assert = require('node:assert/strict');
const {poseAt, storyAt} = require('../remotion/src/storyMotion.ts');
const walkingA = poseAt(1, true, 'idle', 1);
const walkingB = poseAt(8, true, 'idle', 1);
assert.notDeepEqual(walkingA.leftFoot, walkingB.leftFoot, 'Walking must articulate legs');
assert.notDeepEqual(walkingA.rightHand, walkingB.rightHand, 'Walking must swing arms');
assert.notDeepEqual(poseAt(0, false, 'reach', 0).rightHand, poseAt(0, false, 'reach', 1).rightHand);
const scenes = [
  {startFrame: 0, endFrame: 90, visual: 'burden', action: 'release', actionStart: 30, leadWords: [{start: 25, end: 40}]},
  {startFrame: 90, endFrame: 180, visual: 'burden', action: 'idle', actionStart: 90, leadWords: []},
  {startFrame: 180, endFrame: 270, visual: 'journey', action: 'walk', actionStart: 200, leadWords: []},
];
assert.equal(storyAt(scenes, 20).phase, 0, 'No event before spoken cue');
assert.equal(storyAt(scenes, 60).phase, 1);
assert.equal(storyAt(scenes, 100).action, 'release', 'Continue event across subtitle boundaries');
assert.equal(storyAt(scenes, 190).action, 'idle', 'New shot must not inherit previous event');
const repeated = [...scenes];
repeated[1] = {...repeated[1], action: 'nod'};
assert.equal(storyAt(repeated, 100).action, 'release', 'A cosmetic cue must not reset released props');
const delayed = [...scenes];
delayed[0] = {...delayed[0], action: 'nod'};
delayed[1] = {...delayed[1], action: 'release', actionStart: 120};
assert.equal(storyAt(delayed, 70).phase, 0, 'Wait for the meaningful spoken cue rather than an earlier cosmetic gesture');
assert.equal(storyAt(delayed, 150).phase, 1);
assert.equal(storyAt(scenes, 30).speaking, true);
assert.equal(storyAt(scenes, 50).speaking, false);
console.log('Story motion checks passed');

import React from 'react';
import {Composition} from 'remotion';
import {CozyStorytellingVideo, CozyStorytellingProps} from './CozyStorytellingVideo';
import {DialogueStoryVideo} from './DialogueStoryVideo';

const StudioVideo: React.FC<CozyStorytellingProps> = props => props.timedDialogue
  ? <DialogueStoryVideo {...props} /> : <CozyStorytellingVideo {...props} />;

export const Root: React.FC = () => (
  <Composition id="CozyStorytellingVideo" component={StudioVideo}
    durationInFrames={300} fps={30} width={1080} height={1920}
    defaultProps={{totalDurationInFrames: 300, audioSrc: ''}}
    calculateMetadata={async ({props}: {props: CozyStorytellingProps}) => ({
      durationInFrames: props.totalDurationInFrames || 300,
      width: props.width || 1080, height: props.height || 1920, props,
    })} />
);

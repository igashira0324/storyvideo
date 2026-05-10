import { Composition } from 'remotion';
import { MainTimeline } from './Timeline';
import shotsData from './shots.json';

export const RemotionRoot: React.FC = () => {
  // Calculate total duration from shots
  const totalFrames = shotsData.reduce((acc, shot) => acc + (shot.duration_frames || 0), 0);
  
  return (
    <>
      <Composition
        id="FinalVideo"
        component={MainTimeline}
        durationInFrames={totalFrames || 100}
        fps={24}
        width={1920}
        height={1080}
        defaultProps={{
          shots: shotsData,
          bgm_path: "/assets/bgm.mp3",
          bgm_volume: 0.2
        }}
      />
    </>
  );
};

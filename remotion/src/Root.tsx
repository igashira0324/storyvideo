import { Composition } from 'remotion';
import { MainTimeline } from './Timeline';
import shotsData from './shots.json';
import config from './config.json';

export const RemotionRoot: React.FC = () => {
  // Calculate total duration from shots
  const totalFrames = shotsData.reduce((acc, shot) => acc + (shot.duration_frames || 0), 0);
  
  return (
    <>
      <Composition
        id={config.compositionName || "FinalVideo"}
        component={MainTimeline}
        durationInFrames={totalFrames || 100}
        fps={config.fps || 24}
        width={config.width || 1280}
        height={config.height || 720}
        defaultProps={{
          shots: shotsData,
          bgm_path: config.bgmPath,
          bgm_volume: 0.2,
          project_title: config.projectTitle,
          project_subtitle: config.projectSubtitle
        }}
      />
    </>
  );
};

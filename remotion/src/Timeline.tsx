import { Series, Video, AbsoluteFill, staticFile, Audio, useCurrentFrame, interpolate } from 'remotion';
import React from 'react';

interface Shot {
  id: string;
  path: string;
  duration_frames: number;
  subtitle?: string;
  narration_path?: string;
  transition?: string;
}

interface TimelineProps {
  shots: Shot[];
  bgm_path?: string;
  bgm_volume?: number;
}

const ShotView: React.FC<{shot: Shot}> = ({shot}) => {
  const frame = useCurrentFrame();
  
  const opacity = shot.transition === 'fade' 
    ? interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' })
    : 1;

  return (
    <AbsoluteFill style={{ opacity }}>
      <Video src={staticFile(shot.path)} />
      
      {/* Narration Track */}
      {shot.narration_path && (
        <Audio src={staticFile(shot.narration_path)} />
      )}

      {shot.subtitle && (
        <AbsoluteFill style={{
          justifyContent: 'flex-end',
          alignItems: 'center',
          paddingBottom: 50,
        }}>
          <div style={{
            color: 'white',
            fontSize: 48,
            textAlign: 'center',
            backgroundColor: 'rgba(0,0,0,0.5)',
            padding: '10px 20px',
            borderRadius: 10,
            maxWidth: '80%',
            fontFamily: 'sans-serif',
            textShadow: '2px 2px 4px rgba(0,0,0,0.8)'
          }}>
            {shot.subtitle}
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

export const MainTimeline: React.FC<TimelineProps> = ({ 
  shots, 
  bgm_path = "/assets/bgm.mp3", 
  bgm_volume = 0.3 
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      {/* BGM Track */}
      {bgm_path && (
        <Audio 
          src={staticFile(bgm_path)} 
          volume={bgm_volume} 
          loop 
        />
      )}

      <Series>
        {shots.map((shot) => (
          <Series.Sequence key={shot.id} durationInFrames={shot.duration_frames}>
            <ShotView shot={shot} />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};

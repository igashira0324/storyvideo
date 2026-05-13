import { Series, Video, AbsoluteFill, staticFile, Audio } from 'remotion';
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
  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      <Video
        src={staticFile(shot.path)}
        startFrom={0}
        endAt={shot.duration_frames}
        muted
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover'
        }}
      />

      {/* Narration Track */}
      {shot.narration_path && (
        <Audio src={staticFile(shot.narration_path)} />
      )}

      {shot.subtitle && (
        <AbsoluteFill
          style={{
            justifyContent: 'flex-end',
            alignItems: 'center',
            paddingBottom: 72,
            paddingLeft: 36,
            paddingRight: 36,
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              color: '#fffdf7',
              fontSize: 42,
              lineHeight: 1.35,
              fontWeight: 700,
              textAlign: 'center',
              maxWidth: '88%',
              padding: '14px 28px 16px',
              borderRadius: 28,
              fontFamily: '"Noto Sans JP", "Hiragino Sans", "Yu Gothic", sans-serif',
              letterSpacing: '0.04em',
              background: 'linear-gradient(135deg, rgba(10,18,35,0.58), rgba(40,95,120,0.38))',
              border: '1.5px solid rgba(255,255,255,0.45)',
              boxShadow: '0 0 22px rgba(120,220,255,0.32), 0 10px 28px rgba(0,0,0,0.45)',
              backdropFilter: 'blur(8px)',
              textShadow: '0 2px 6px rgba(0,0,0,0.9), 0 0 12px rgba(120,220,255,0.65)',
            }}
          >
            <span style={{ color: '#bff7ff', marginRight: 10 }}>✦</span>
            {shot.subtitle}
            <span style={{ color: '#ffe9a8', marginLeft: 10 }}>✦</span>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

export const MainTimeline: React.FC<TimelineProps> = ({
  shots,
  bgm_path,
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

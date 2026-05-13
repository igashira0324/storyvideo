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

const SubtitleText: React.FC<{ text: string }> = ({ text }) => {
  return (
    <div
      style={{
        position: 'relative',
        display: 'inline-block',
        maxWidth: '92%',
        textAlign: 'center',
        fontFamily: '"Noto Sans JP", "Hiragino Sans", "Yu Gothic", sans-serif',
        fontSize: 46,
        lineHeight: 1.35,
        fontWeight: 900,
        letterSpacing: '0.045em',
      }}
    >
      {/* Outer dark outline */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          color: 'transparent',
          WebkitTextStroke: '11px rgba(3, 12, 28, 0.92)',
          filter: 'drop-shadow(0 5px 10px rgba(0,0,0,0.9))',
          zIndex: 0,
        }}
      >
        {text}
      </div>

      {/* Cyan glowing outline */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          color: 'transparent',
          WebkitTextStroke: '5px rgba(95, 225, 255, 0.85)',
          filter: 'drop-shadow(0 0 8px rgba(100,230,255,0.9)) drop-shadow(0 0 18px rgba(80,190,255,0.65))',
          zIndex: 1,
        }}
      >
        {text}
      </div>

      {/* Main text */}
      <div
        style={{
          position: 'relative',
          color: '#fffdf7',
          WebkitTextStroke: '1.4px rgba(255, 225, 150, 0.85)',
          textShadow: '0 0 5px rgba(255,255,255,0.95), 0 0 12px rgba(130,230,255,0.8), 0 2px 4px rgba(0,0,0,0.8)',
          zIndex: 2,
        }}
      >
        {text}
      </div>
    </div>
  );
};

const ShotView: React.FC<{ shot: Shot }> = ({ shot }) => {
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
            paddingBottom: 82,
            paddingLeft: 32,
            paddingRight: 32,
            pointerEvents: 'none',
          }}
        >
          <SubtitleText text={shot.subtitle} />
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

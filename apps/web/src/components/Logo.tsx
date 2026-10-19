type LogoProps = {
  className?: string;
  /** 渐变描边 ID 需唯一，避免同页多个 logo 冲突 */
  id?: string;
};

/** 品牌标识：一条圆润的"大肥鱼"。 */
export function Logo({ className = "h-9 w-9", id = "logo" }: LogoProps) {
  const gradientId = `${id}-gradient`;
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="55%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      {/* 尾鳍 */}
      <path d="M9.5 16 2.5 10.5v11L9.5 16Z" fill={`url(#${gradientId})`} opacity="0.85" />
      {/* 身体 */}
      <ellipse cx="18.5" cy="16" rx="10.5" ry="7.2" fill={`url(#${gradientId})`} />
      {/* 背鳍 */}
      <path d="M15 9.6c.6-2.6 2.4-4 4.2-4.2-.9 1.6-1 3-.4 4.1Z" fill={`url(#${gradientId})`} opacity="0.9" />
      {/* 眼睛 */}
      <circle cx="23.4" cy="13.6" r="1.5" fill="#fff" />
      <circle cx="23.8" cy="13.6" r="0.7" fill="#1e1b4b" />
      {/* 气泡 */}
      <circle cx="27.5" cy="8" r="1" fill="#a5b4fc" opacity="0.8" />
      <circle cx="29.5" cy="4.5" r="0.6" fill="#a5b4fc" opacity="0.6" />
    </svg>
  );
}
